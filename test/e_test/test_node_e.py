"""

e_node_item_name_recognition 节点测试

按图节点的调用方式传入 state（file_title + chunks），
跑完整的商品名称识别流程：
    1. 调用大模型识别商品名称
    2. 回填 item_name 到 state 与每个切片
    3. 为商品名称生成 BGE-M3 稠密/稀疏向量
    4. 写入 Milvus 向量库（item_name 集合）

注意：本节点会真实调用大模型（OPENAI_*）并写入 Milvus，
需保证 .env 中 OPENAI_* / MILVUS_* 配置正确、服务可访问；
BGE-M3 模型需已下载且 .env 中 BGE_M3_PATH 指向的目录存在。

"""

from pathlib import Path

from processor.import_processor.base import setup_logging
from processor.import_processor.nodes.d_node_document_split import NodeDocumentSplit
from processor.import_processor.nodes.e_node_item_name_recognition import NodeItemNameRecognition
from processor.import_processor.state import create_default_state

setup_logging()

# ==================== 测试数据 ====================
md_path = r"D:\output\hak180使用说明书\hak180使用说明书.md"

with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()

file_title = Path(md_path).stem


def main():
    # 1. 构造含 chunks 的 state：E 节点依赖 file_title + chunks
    #    这里用 D 节点（文档切分）产出真实 chunks，贴近实际流水线
    split_state = create_default_state(md_content=md_content, file_title=file_title)
    split_state = NodeDocumentSplit()(split_state)
    chunks = split_state["chunks"]
    print(f"\n前置切分完成，共 {len(chunks)} 个 Chunk")

    # 2. 构造 E 节点输入状态
    state = create_default_state(file_title=file_title, chunks=chunks)

    node = NodeItemNameRecognition()

    # 3. 按图节点调用方式执行，返回更新后的 state（含 item_name，chunks 已回填 item_name）
    result = node(state)

    # 4. 打印识别结果
    item_name = result["item_name"]
    print("\n" + "=" * 60)
    print(f"识别出的商品名称：{item_name!r}")
    print(f"回填后首个切片 item_name：{result['chunks'][0].get('item_name')!r}")
    print("=" * 60)


if __name__ == "__main__":
    main()
