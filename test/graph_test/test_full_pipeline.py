"""

完整链路测试：入库主图 → 检索主图（端到端）

第一阶段 KBImportWorkflow（导入）：
    A 入口路由 → B(PDF转MD) → C(图片处理) → D(切分) → E(商品名识别)
    → F(向量化) → G(Milvus 入库)

第二阶段 KBQueryWorkflow（检索）：
    node_item_name_confirm（主体确认）→ node_multi_search（分叉）
    → 三路并发检索（向量 / HyDE / 联网）→ node_join → node_rrf
    → node_rerank → node_answer_output

两阶段均以 stream 模式输出每个节点执行后的关键状态。

注意：本测试会真实调用 MinerU(PDF 解析)、多模态大模型、文本大模型、
BGE-M3、阿里云百炼 MCP，并写入 MinIO / Milvus / MongoDB；
耗时较长（数分钟），需保证 .env 中各服务配置正确、可访问。

    运行：PYTHONPATH=. python test/graph_test/test_full_pipeline.py

"""

import uuid

from main_graph import KBImportWorkflow
from processor.import_processor.base import setup_logging
from processor.import_processor.state import create_default_state
from processor.query_processor.main_graph import KBQueryWorkflow
from tool.logger import logger

setup_logging()

# ==================== 测试数据 ====================
pdf_path = r"C:\Users\小黑\Desktop\掌柜智库\掌柜智库课件0525\2.资料\04-设备手册汇总\doc\hl3040网络说明书.pdf"
# B 节点（PDF转MD）需要 file_dir 作为结果输出目录
file_dir = r"D:\output"

# 检索阶段：入口节点 node_item_name_confirm 强制要求 session_id，用随机后缀避免读到历史
session_id = f"test_full_{uuid.uuid4().hex[:8]}"
# 检索问题针对刚入库的 HL3040 设备手册
original_query = "HL3040 的网络怎么配置？"


# ==================== 摘要工具 ====================

def summarize_import(state: dict) -> str:
    """导入图 updates/单状态 chunk 的关键字段摘要"""
    md_content = state.get("md_content") or ""
    chunks = state.get("chunks") or []
    return (
        f"file_title={state.get('file_title')!r} "
        f"md_path={state.get('md_path')!r} "
        f"md_content_len={len(md_content)} "
        f"chunks={len(chunks)} "
        f"item_name={state.get('item_name')!r}"
    )


def summarize_query(chunk: dict) -> str:
    """检索图 updates 模式 chunk（{节点名: 状态更新}）的单行摘要"""
    lines = []
    for node_name, update in chunk.items():
        if not isinstance(update, dict):
            lines.append(f"{node_name}: <无状态更新>")
            continue
        parts = []
        if update.get("item_names"):
            parts.append(f"item_names={update['item_names']}")
        if update.get("rewritten_query"):
            parts.append(f"rewritten_query={update['rewritten_query']!r}")
        if update.get("answer"):
            parts.append(f"answer={str(update['answer'])[:120]!r}")
        for key in ("embedding_chunks", "hyde_embedding_chunks", "web_search_docs",
                    "rrf_chunks", "reranked_docs"):
            value = update.get(key)
            if value:
                parts.append(f"{key}={len(value)}条")
        lines.append(f"{node_name}: " + ("; ".join(parts) if parts else "（无关键字段）"))
    return " | ".join(lines)


# ==================== 阶段一：入库主图 ====================

def run_import_stage() -> dict:
    logger.info("#" * 60)
    logger.info("# 阶段一：入库主图 KBImportWorkflow")
    logger.info("#" * 60)

    workflow = KBImportWorkflow()
    init_state = create_default_state(import_file_path=pdf_path, file_dir=file_dir)

    steps = 0
    final_state = init_state
    try:
        for event in workflow.run(init_state, stream=True):
            steps += 1
            final_state = event
            logger.info(f"[import step {steps}] {summarize_import(event)}")
    except Exception as e:
        logger.error(f"入库主图执行失败（第 {steps} 步之后）：{type(e).__name__}: {e}")
        raise

    chunks = final_state.get("chunks") or []
    logger.info("-" * 60)
    logger.info("入库主图执行完成")
    logger.info(f"  file_title  : {final_state.get('file_title')!r}")
    logger.info(f"  md_path     : {final_state.get('md_path')!r}")
    logger.info(f"  chunks 数量 : {len(chunks)}")
    logger.info(f"  item_name   : {final_state.get('item_name')!r}")
    if chunks:
        miss_vec = [i for i, c in enumerate(chunks) if not c.get("dense_vector")]
        miss_id = [i for i, c in enumerate(chunks) if c.get("chunk_id") is None]
        logger.info(f"  缺向量切片数: {len(miss_vec)}")
        logger.info(f"  缺chunk_id数: {len(miss_id)}")
    logger.info("-" * 60)
    return final_state


# ==================== 阶段二：检索主图 ====================

def run_query_stage() -> dict:
    logger.info("#" * 60)
    logger.info("# 阶段二：检索主图 KBQueryWorkflow")
    logger.info("#" * 60)
    logger.info(f"session_id={session_id}")
    logger.info(f"查询：{original_query}")

    workflow = KBQueryWorkflow()
    # 检索图 stream 默认是 updates 模式：每个 chunk 为 {节点名: 该节点的状态更新}
    init_state = {"session_id": session_id, "original_query": original_query}

    merged_state = dict(init_state)
    steps = 0
    try:
        for chunk in workflow.run(init_state, stream=True):
            steps += 1
            for update in chunk.values():
                if isinstance(update, dict):
                    merged_state.update(update)
            logger.info(f"[query step {steps}] {summarize_query(chunk)}")
    except Exception as e:
        logger.error(f"检索主图执行失败（第 {steps} 步之后）：{type(e).__name__}: {e}")
        raise

    logger.info("-" * 60)
    logger.info("检索主图执行完成")
    logger.info(f"  item_names           : {merged_state.get('item_names')!r}")
    logger.info(f"  rewritten_query      : {merged_state.get('rewritten_query')!r}")
    logger.info(f"  embedding_chunks     : {len(merged_state.get('embedding_chunks') or [])}")
    logger.info(f"  hyde_embedding_chunks: {len(merged_state.get('hyde_embedding_chunks') or [])}")
    logger.info(f"  web_search_docs      : {len(merged_state.get('web_search_docs') or [])}")
    logger.info(f"  rrf_chunks           : {len(merged_state.get('rrf_chunks') or [])}")
    logger.info(f"  reranked_docs        : {len(merged_state.get('reranked_docs') or [])}")
    logger.info(f"  answer               : {merged_state.get('answer')!r}")
    logger.info("-" * 60)
    return merged_state


def main():
    logger.info("=" * 60)
    logger.info("完整链路测试：入库 → 检索")
    logger.info("=" * 60)

    import_state = run_import_stage()
    query_state = run_query_stage()

    logger.info("=" * 60)
    logger.info("完整链路测试结束")
    logger.info(f"  入库 item_name : {import_state.get('item_name')!r}")
    logger.info(f"  检索 answer    : {query_state.get('answer')!r}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
