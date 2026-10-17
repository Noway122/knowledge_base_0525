"""

d_node_document_split 节点测试

按图节点调用方式传入 state（md_content + file_title），
跑完整的文档切分流程，打印最终生成的 Chunk 数量与每个 Chunk 的标题/长度。

"""

from pathlib import Path

from processor.import_processor.base import setup_logging
from processor.import_processor.nodes.d_node_document_split import NodeDocumentSplit
from processor.import_processor.state import create_default_state

setup_logging()

# ==================== 测试数据 ====================
md_path = r"D:\output\hak180使用说明书\hak180使用说明书.md"

with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()

file_title = Path(md_path).stem


def main():
    # 构造切分所需的 state：md_content + file_title
    state = create_default_state(md_content=md_content, file_title=file_title)

    node = NodeDocumentSplit()

    # 按图节点调用方式执行，返回更新后的 state（含 chunks）
    result = node(state)

    chunks = result["chunks"]
    print(f"\n共生成 {len(chunks)} 个 Chunk：")
    for i, chunk in enumerate(chunks, start=1):
        print(f"  [{i}] title={chunk.get('title')!r}  长度={len(chunk.get('content', ''))}")


if __name__ == "__main__":
    main()
