import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, BackgroundTasks, UploadFile, File
from starlette.responses import FileResponse

from config.minio_config import minio_config
from processor.import_processor.main_graph import KBImportWorkflow
from tool.logger import logger
from utils.minio_utils import get_minio_client
from utils.task_utils import (
    add_running_task,
    add_done_task,
    update_task_status,
    get_task_status,
    get_done_task_list,
    get_running_task_list,
)

router = APIRouter(tags=["import"])


def run_graph_task(task_id: str, file_dir: str, import_file_path: str):
    """
    LangGraph 全流程执行后台任务。

    进度由各节点的 BaseNode.__call__ 统一通过 task_utils 推送（以节点 name 属性为键，
    与 _NODE_NAME_TO_CN 中文映射一致），此处只负责任务全局状态的更新，
    不再重复 add_done_task。
    """
    try:
        update_task_status(task_id, "processing")

        init_state = {
            "task_id": task_id,
            "file_dir": file_dir,
            "import_file_path": import_file_path,
        }

        workflow = KBImportWorkflow()
        for _ in workflow.run(init_state, stream=True):
            pass

        update_task_status(task_id, "completed")
        logger.info(f"[{task_id}] LangGraph 全流程执行完成")

    except Exception as e:
        update_task_status(task_id, "failed")
        logger.error(f"[{task_id}] LangGraph 全流程执行失败，异常信息：{str(e)}", exc_info=True)


@router.get("/import.html")
async def get_import_page():
    html_path = Path(__file__).absolute().parent.parent.parent / "page" / "index.html"
    if not html_path.exists():
        html_path = Path(__file__).absolute().parent.parent.parent / "page" / "import.html"
    return FileResponse(html_path)


@router.post("/upload", summary="文件上传接口", description="支持多文件批量上传，自动触发知识库导入全流程")
async def upload_files(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    """
    1. 接收前端上传的多文件（PDF/MD 为主）
    2. 按「日期/任务ID」分层保存到本地输出目录
    3. 将文件上传至 MinIO 对象存储做持久化
    4. 为每个文件生成唯一 TaskID，启动独立的 LangGraph 后台处理任务
    5. 前端通过 /status/{task_id} 轮询进度
    """
    data_based_root_dir = os.getenv("DATA_BASED_ROOT_DIR")
    data_dir = os.path.join(data_based_root_dir, datetime.now().strftime("%Y%m%d"))
    task_ids = []

    for file in files:
        task_id = str(uuid.uuid4())
        task_ids.append(task_id)
        logger.info(f"[{task_id}] 开始处理上传文件，文件名：{file.filename}，类型：{file.content_type}")

        add_running_task(task_id, "upload_file")

        file_dir = os.path.join(data_dir, task_id)
        os.makedirs(file_dir, exist_ok=True)
        import_file_path = os.path.join(file_dir, file.filename)

        with open(import_file_path, "wb") as file_buffer:
            shutil.copyfileobj(file.file, file_buffer)
        logger.info(f"[{task_id}] 文件已保存至本地：{import_file_path}")

        minio_object_name = f"pdf_files/{datetime.now().strftime('%Y%m%d')}/{file.filename}"
        try:
            minio_client = get_minio_client()
            minio_client.fput_object(
                bucket_name=minio_config.bucket_name,
                object_name=minio_object_name,
                file_path=import_file_path,
                content_type=file.content_type,
            )
            logger.info(f"[{task_id}] 文件已上传至 MinIO：{minio_object_name}")
        except Exception as e:
            logger.warning(f"[{task_id}] 上传 MinIO 失败，继续本地处理：{str(e)}", exc_info=True)

        add_done_task(task_id, "upload_file")

        background_tasks.add_task(run_graph_task, task_id, file_dir, import_file_path)
        logger.info(f"[{task_id}] 已加入后台 LangGraph 任务")

    logger.info(f"多文件上传处理完毕，共 {len(files)} 个文件，TaskID 列表：{task_ids}")
    return {
        "code": 200,
        "message": f"文件上传成功, total: {len(files)}",
        "task_ids": task_ids,
    }


@router.get("/status/{task_id}", summary="任务状态查询", description="根据 TaskID 查询单个文件的处理进度和全局状态")
async def get_task_progress(task_id: str):
    return {
        "code": 200,
        "task_id": task_id,
        "status": get_task_status(task_id),
        "done_list": get_done_task_list(task_id),
        "running_list": get_running_task_list(task_id),
    }
