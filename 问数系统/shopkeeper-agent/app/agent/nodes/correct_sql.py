import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def correct_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "校正SQL"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})
    # PRD 五a.4：可纠正分支发送提示
    writer({"type": "notice", "message": "【系统自动修正中，请稍候】"})

    try:
        table_infos = state["table_infos"]
        metric_infos = state["metric_infos"]
        date_info = state["date_info"]
        db_info = state["db_info"]
        query = state["query"]
        sql = state["sql"]
        error = state["error"]
        correction_count = state.get("correction_count", 0)

        prompt = PromptTemplate(
            template=load_prompt("correct_sql"),
            input_variables=["table_infos", "metric_infos", "date_info", "db_info", "query", "sql", "error"],
        )
        chain = prompt | llm | StrOutputParser()
        result = await chain.ainvoke({
            "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False),
            "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False),
            "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
            "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
            "query": query,
            "sql": sql,
            "error": error,
        })

        logger.info(f"校正后的SQL（第{correction_count + 1}次校正）：{result}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"sql": result, "correction_count": correction_count + 1}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
