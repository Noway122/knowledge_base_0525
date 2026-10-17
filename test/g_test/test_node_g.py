"""

g_node_import_milvus 节点测试

按图节点的调用方式传入 state（chunks），跑完整的向量入库流程：
    1. 校验切片与向量字段完整性，提取向量维度
    2. 连接 Milvus，集合不存在则自动创建 Schema + 索引
    3. 按 file_title 幂等清理旧数据
    4. 批量插入切片，回填 Milvus 自增主键 chunk_id
    5. 将回填后的 chunks 写回 state

G 节点依赖带 item_name（E 节点）与 dense_vector/sparse_vector（F 节点）的 chunks，
故这里先跑 D → E → F 产出贴近真实流水线的输入，最后校验 Milvus 中的实际入库条数。

注意：本测试会真实调用大模型（E 节点）、加载 BGE-M3（F 节点）并写入 Milvus（G 节点），
需保证 .env 中 OPENAI_* / MILVUS_* / BGE_M3_PATH 配置正确、Milvus 服务可访问。

"""

import time
from pathlib import Path

from pymilvus import MilvusClient

from config.milvus_config import milvus_config
from processor.import_processor.base import setup_logging
from processor.import_processor.nodes.d_node_document_split import NodeDocumentSplit
from processor.import_processor.nodes.e_node_item_name_recognition import NodeItemNameRecognition
from processor.import_processor.nodes.f_node_bge_embedding import NodeBGEEmbedding
from processor.import_processor.nodes.g_node_import_milvus import NodeImportMilvus
from processor.import_processor.state import create_default_state
from utils.milvus_utils import escape_milvus_string

setup_logging()

# ==================== 测试数据 ====================
md_path = r"D:\output\hak180使用说明书\hak180使用说明书.md"

with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()

file_title = Path(md_path).stem


def main():
    # 1. 前置：D 切分 → E 识别商品名 → F 生成向量，得到可入库的 chunks
    split_state = create_default_state(md_content=md_content, file_title=file_title)
    chunks = NodeDocumentSplit()(split_state)["chunks"]

    recog_state = create_default_state(file_title=file_title, chunks=chunks)
    recog_state = NodeItemNameRecognition()(recog_state)
    chunks = recog_state["chunks"]
    item_name = recog_state["item_name"]

    emb_state = create_default_state(file_title=file_title, chunks=chunks)
    chunks = NodeBGEEmbedding()(emb_state)["chunks"]
    print(f"\n前置完成：{len(chunks)} 个 Chunk，item_name={item_name!r}，均已带双向量")

    # 2. 构造 G 节点输入状态并执行
    state = create_default_state(file_title=file_title, chunks=chunks)
    node = NodeImportMilvus()
    result = node(state)

    # 3. 打印入库结果
    out_chunks = result["chunks"]
    print("\n" + "=" * 60)
    print(f"入库切片数量：{len(out_chunks)}")
    first = out_chunks[0]
    print(f"首个切片 chunk_id：{first.get('chunk_id')!r}")
    print(f"首个切片 title：{first.get('title')!r}  part={first.get('part')!r}")
    missing_id = [i for i, c in enumerate(out_chunks) if c.get("chunk_id") is None]
    print(f"缺少 chunk_id 的切片数：{len(missing_id)}")

    # 4. 回查 Milvus，确认落库条数一致
    #    刚插入的数据需先 flush 再 load 才立即可查；此处加短暂轮询兜底
    client = MilvusClient(uri=milvus_config.milvus_url)
    coll = milvus_config.chunks_collection
    client.flush(coll)
    client.load_collection(coll)
    safe_title = escape_milvus_string(file_title)
    count = 0
    for _ in range(10):
        rows = client.query(
            collection_name=coll,
            filter=f'file_title=="{safe_title}"',
            output_fields=["count(*)"],
        )
        count = rows[0]["count(*)"]
        if count >= len(out_chunks):
            break
        time.sleep(1)
    print(f"Milvus 集合 {coll!r} 中 file_title={file_title!r} 的条数：{count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
