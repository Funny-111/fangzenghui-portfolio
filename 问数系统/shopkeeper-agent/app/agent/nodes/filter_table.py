import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState, TableInfoState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "过滤表信息"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        table_infos: list[TableInfoState] = state["table_infos"]

        # 上下文裁剪：过滤阶段只需语义信息（名称/描述/别名/类型），不需要取值样例
        # （样例由召回阶段的字段取值检索独立负责）。减小 prompt 体积可降低 LLM 延迟与
        # token 成本——与「换模型」互为对比实验的两种降本手段。
        slim_tables = [
            {**t, "columns": [{k: v for k, v in c.items() if k != "examples"} for c in t["columns"]]}
            for t in table_infos
        ]

        prompt = PromptTemplate(template=load_prompt("filter_table_info"), input_variables=["query", "table_infos"])
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke(
            {"query": query, "table_infos": yaml.dump(slim_tables, allow_unicode=True, sort_keys=False)}
        )

        filtered = []
        for ti in table_infos:
            if ti["name"] in result:
                ti["columns"] = [c for c in ti["columns"] if c["name"] in result[ti["name"]]]
                filtered.append(ti)

        logger.info(f"过滤后的表信息：{[t['name'] for t in filtered]}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"table_infos": filtered}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
