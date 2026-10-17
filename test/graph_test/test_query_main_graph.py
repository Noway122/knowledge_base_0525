"""

查询主图 KBQueryWorkflow 端到端测试

流程：node_item_name_confirm（主体确认）
      → node_multi_search（分叉）→ 三路并发检索
        ├─ node_search_embedding（向量检索）
        ├─ node_search_embedding_hyde（HyDE 向量检索）
        └─ node_web_search_mcp（联网搜索）
      → node_join（合并）→ node_rrf（融合排序）→ node_rerank（重排）
      → node_answer_output（生成答案）

用 stream 模式跑完整查询流程，逐个输出节点执行后的关键状态。

注意：本测试会真实调用 MongoDB(读写历史)、Milvus(检索)、
文本大模型、BGE-M3、阿里云百炼 MCP，耗时较长，
需保证 .env 中各服务配置正确、可访问。

    运行：PYTHONPATH=. python test/graph_test/test_query_main_graph.py

"""

import uuid

from processor.query_processor.base import NodeBase
from processor.query_processor.main_graph import KBQueryWorkflow
from tool.logger import logger

# ==================== 测试数据 ====================
# 查询图入口节点 node_item_name_confirm 强制要求 session_id（缺省会抛 ValueError），
# 主图 __main__ 未提供，这里补上；用随机后缀避免读到历史会话数据。
session_id = f"test_query_{uuid.uuid4().hex[:8]}"
original_query = "如何使用万用表测量电压？"


def summarize(chunk: dict) -> str:
    """把 updates 模式的一个 chunk（{节点名: 状态更新}）压成单行摘要"""
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


def main():
    logger.info(f"开始执行查询主图（stream 模式），session_id={session_id}")
    logger.info(f"查询：{original_query}")

    workflow = KBQueryWorkflow()

    # 查询图 stream 默认是 updates 模式：每个 chunk 为 {节点名: 该节点的状态更新}
    init_state = {"session_id": session_id, "original_query": original_query}

    # 累积完整 state，便于最后汇总（updates 模式每次只给增量）
    merged_state = dict(init_state)
    steps = 0
    try:
        for chunk in workflow.run(init_state, stream=True):
            steps += 1
            for node_name, update in chunk.items():
                if isinstance(update, dict):
                    merged_state.update(update)
            logger.info(f"[step {steps}] {summarize(chunk)}")
    except Exception as e:
        logger.error(f"查询主图执行失败（第 {steps} 步之后）：{type(e).__name__}: {e}")
        raise

    # ==================== 最终结果汇总 ====================
    logger.info("=" * 60)
    logger.info("查询主图执行完成")
    logger.info(f"  session_id      : {merged_state.get('session_id')!r}")
    logger.info(f"  item_names      : {merged_state.get('item_names')!r}")
    logger.info(f"  rewritten_query : {merged_state.get('rewritten_query')!r}")
    logger.info(f"  embedding_chunks    : {len(merged_state.get('embedding_chunks') or [])}")
    logger.info(f"  hyde_embedding_chunks: {len(merged_state.get('hyde_embedding_chunks') or [])}")
    logger.info(f"  web_search_docs     : {len(merged_state.get('web_search_docs') or [])}")
    logger.info(f"  rrf_chunks          : {len(merged_state.get('rrf_chunks') or [])}")
    logger.info(f"  reranked_docs       : {len(merged_state.get('reranked_docs') or [])}")
    logger.info(f"  answer          : {merged_state.get('answer')!r}")
    logger.info("=" * 60)

    if not merged_state.get("answer"):
        logger.warning(
            "answer 为空：node_answer_output 目前是 TODO 空实现，属预期（检索链路本身正常）"
        )


if __name__ == "__main__":
    main()
