import jieba.analyse
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def extract_keywords(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "抽取关键词"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        allow_pos = (
            "n", "nr", "ns", "nt", "nz",
            "v", "vn", "a", "an", "eng", "i", "l",
        )
        keywords = jieba.analyse.extract_tags(query, allowPOS=allow_pos)
        keywords = list(set(keywords + [query]))
        writer({"type": "progress", "step": step, "status": "success"})
        logger.info(f"抽取关键词: {keywords}")
        return {"keywords": keywords}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
