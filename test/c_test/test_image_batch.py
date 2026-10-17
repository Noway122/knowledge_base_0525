"""

_upload_images_batch 单独测试

只测图片批量上传至 MinIO 这一步，打印上传结果 URL。

注意：本测试会真实上传图片到 MinIO，需保证 .env 中
MINIO_* 配置正确、MinIO 服务可访问。

"""

from pathlib import Path

from config.minio_config import minio_config
from processor.import_processor.base import setup_logging
from processor.import_processor.nodes.c_node_md_img import NodeMDImg
from utils.minio_utils import get_minio_client

setup_logging()

# ==================== 测试数据 ====================
md_path = r"D:\output\hak180使用说明书\hak180使用说明书.md"
image_dir = Path(r"D:\output\hak180使用说明书\images")

with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()


def main():
    node = NodeMDImg()
    minio_client = get_minio_client()

    target_images = node._step_2_scan_images(md_content, image_dir)

    doc_stem = Path(md_path).stem
    upload_dir = f"{minio_config.img_dir}/{doc_stem}".replace(" ", "")
    node._clean_minio_directory(minio_client, upload_dir)

    urls = node._upload_images_batch(minio_client, upload_dir, target_images)

    for url in urls.values():
        print(url)


if __name__ == "__main__":
    main()
