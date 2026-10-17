
"""

主图 KBImportWorkflow 端到端测试（完整 PDF 链路）

流程：A 入口路由 → B(PDF转MD) → C(图片处理) → D(切分) → E(商品名识别)
      → F(向量化) → G(Milvus入库)

用真实 PDF 跑完整导入流程，以 stream 模式输出每个节点执行后的关键状态。

注意：本测试会真实调用 MinerU(PDF 解析)、多模态大模型(C)、文本大模型(E)、
BGE-M3(F)，并写入 MinIO / Milvus；耗时较长（数分钟），
需保证 .env 中各服务配置正确、可访问。

    运行：PYTHONPATH=. python test/graph_test/test_main_graph.py

"""

from pathlib import Path

from main_graph import KBImportWorkflow
from processor.import_processor.base import setup_logging
from processor.import_processor.state import create_default_state

setup_logging()

# ==================== 测试数据 ====================
pdf_path = r"C:\Users\小黑\Desktop\掌柜智库\掌柜智库课件0525\2.资料\04-设备手册汇总\doc\Aolynk CC系列室内型Cable网络集中器 用户手册-6W202-整本手册.pdf"
# B 节点（PDF转MD）需要 file_dir 作为结果输出目录，主图 __main__ 未提供，这里补上
file_dir = r"D:\output"


def summarize(state) -> str:
    """抽取关键字段做单行摘要，避免打印超长的 md_content"""
    md_content = state.get("md_content") or ""
    chunks = state.get("chunks") or []
    return (
        f"file_title={state.get('file_title')!r} "
        f"md_path={state.get('md_path')!r} "
        f"md_content_len={len(md_content)} "
        f"chunks={len(chunks)} "
        f"item_name={state.get('item_name')!r}"
    )


def main():
    assert Path(pdf_path).exists(), f"测试 PDF 不存在：{pdf_path}"

    workflow = KBImportWorkflow()

    # 构造初始状态：入口需要的 import_file_path + B 节点需要的 file_dir
    init_state = create_default_state(import_file_path=pdf_path, file_dir=file_dir)
    print(f"\n开始执行主图（stream 模式），输入 PDF：{Path(pdf_path).name}\n")

    steps = 0
    final_state = init_state
    try:
        for event in workflow.run(init_state, stream=True):
            steps += 1
            final_state = event
            print(f"[step {steps}] {summarize(event)}")
    except Exception as e:
        print(f"\n主图执行失败（第 {steps} 步之后）：{type(e).__name__}: {e}")
        raise

    # 最终结果汇总
    chunks = final_state.get("chunks") or []
    print("\n" + "=" * 60)
    print("主图执行完成")
    print(f"  file_title  : {final_state.get('file_title')!r}")
    print(f"  md_path     : {final_state.get('md_path')!r}")
    print(f"  chunks 数量 : {len(chunks)}")
    print(f"  item_name   : {final_state.get('item_name')!r}")
    if chunks:
        miss_vec = [i for i, c in enumerate(chunks) if not c.get("dense_vector")]
        miss_id = [i for i, c in enumerate(chunks) if c.get("chunk_id") is None]
        print(f"  缺向量切片数: {len(miss_vec)}")
        print(f"  缺chunk_id数: {len(miss_id)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
