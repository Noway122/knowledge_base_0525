"""

f_node_bge_embedding 节点测试

按图节点的调用方式传入 state（chunks），跑完整的 BGE-M3 向量化流程：
    1. 分批拼接「商品名 + 正文」文本
    2. 调用 BGE-M3 生成稠密/稀疏双向量
    3. 回填 dense_vector / sparse_vector 到每个切片

F 节点依赖带 item_name 的 chunks，故这里先跑 D 节点（切分）与 E 节点（商品名识别）
产出贴近真实流水线的输入。

注意：本测试会真实调用大模型（E 节点）与写入 Milvus（E 节点），
并加载 BGE-M3 模型；需保证 .env 中 OPENAI_* / MILVUS_* / BGE_M3_PATH 配置正确。

"""

from pathlib import Path

from processor.import_processor.base import setup_logging
from processor.import_processor.nodes.d_node_document_split import NodeDocumentSplit
from processor.import_processor.nodes.e_node_item_name_recognition import NodeItemNameRecognition
from processor.import_processor.nodes.f_node_bge_embedding import NodeBGEEmbedding
from processor.import_processor.state import create_default_state

setup_logging()

# ==================== 测试数据 ====================
md_path = r"D:\output\hak180使用说明书\hak180使用说明书.md"

with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()

file_title = Path(md_path).stem


def main():
    # 1. 前置：D 节点切分 → E 节点识别商品名，得到带 item_name 的 chunks
    split_state = create_default_state(md_content=md_content, file_title=file_title)
    split_state = NodeDocumentSplit()(split_state)
    chunks = split_state["chunks"]

    recog_state = create_default_state(file_title=file_title, chunks=chunks)
    recog_state = NodeItemNameRecognition()(recog_state)
    chunks = recog_state["chunks"]
    item_name = recog_state["item_name"]
    print(f"\n前置完成：{len(chunks)} 个 Chunk，item_name={item_name!r}")

    # 2. 构造 F 节点输入状态并执行
    state = create_default_state(file_title=file_title, chunks=chunks)
    node = NodeBGEEmbedding()
    result = node(state)

    # 3. 打印向量化结果
    out_chunks = result["chunks"]
    print("\n" + "=" * 60)
    print(f"向量化切片数量：{len(out_chunks)}")
    first = out_chunks[0]
    dense = first.get("dense_vector")
    sparse = first.get("sparse_vector")
    print(f"首个切片 item_name：{first.get('item_name')!r}")
    print(f"首个切片 content 长度：{len(first.get('content', ''))}")
    print(f"dense_vector 维度：{len(dense)}")
    print(f"sparse_vector 非零项数：{len(sparse)}")
    # 抽查所有切片是否都已带上双向量
    missing = [i for i, c in enumerate(out_chunks)
               if not c.get("dense_vector") or not c.get("sparse_vector")]
    print(f"缺少向量的切片数：{len(missing)}{' -> ' + str(missing[:5]) if missing else ''}")
    print("=" * 60)


if __name__ == "__main__":
    main()
