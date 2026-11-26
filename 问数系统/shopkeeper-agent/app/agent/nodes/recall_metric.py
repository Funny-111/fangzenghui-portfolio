from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.metric_info import MetricInfo
from app.prompt.prompt_loader import load_prompt


async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "召回指标信息"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        keywords = state["keywords"]
        embedding_client = runtime.context["embedding_client"]
        metric_qdrant_repository = runtime.context["metric_qdrant_repository"]

        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_metric_recall"), input_variables=["query"])
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke({"query": query})
        keywords = set(keywords + result)

        metric_info_map: dict[str, MetricInfo] = {}
        for keyword in keywords:
            embedding = await embedding_client.feature_extraction(keyword)
            metrics = await metric_qdrant_repository.search(embedding[0])
            for m in metrics:
                if m.id not in metric_info_map:
                    metric_info_map[m.id] = m

        writer({"type": "progress", "step": step, "status": "success"})
        logger.info(f"检索到指标信息：{list(metric_info_map.keys())}")
        return {"retrieved_metric_infos": list(metric_info_map.values())}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
