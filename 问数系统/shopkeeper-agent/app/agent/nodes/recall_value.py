from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.value_info import ValueInfo
from app.prompt.prompt_loader import load_prompt


async def recall_value(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "召回字段取值"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        keywords = state["keywords"]
        value_es_repository = runtime.context["value_es_repository"]

        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_value_recall"), input_variables=["query"])
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke({"query": query})
        keywords = set(keywords + result)

        value_infos_map: dict[str, ValueInfo] = {}
        for keyword in keywords:
            values = await value_es_repository.search(keyword)
            for v in values:
                if v.id not in value_infos_map:
                    value_infos_map[v.id] = v

        writer({"type": "progress", "step": step, "status": "success"})
        logger.info(f"检索到字段取值：{list(value_infos_map.keys())}")
        return {"retrieved_value_infos": list(value_infos_map.values())}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
