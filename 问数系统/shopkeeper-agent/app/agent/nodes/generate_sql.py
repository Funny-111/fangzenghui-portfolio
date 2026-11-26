import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.agent.generation_parser import parse_generation_output
from app.core.errors import QueryFlowError, SqlGenerationError
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def generate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "生成SQL"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        table_infos = state["table_infos"]
        metric_infos = state["metric_infos"]
        date_info = state["date_info"]
        db_info = state["db_info"]
        query = state["query"]

        prompt = PromptTemplate(
            template=load_prompt("generate_sql"),
            input_variables=["table_infos", "metric_infos", "date_info", "db_info", "query"],
        )
        chain = prompt | llm | StrOutputParser()
        result = await chain.ainvoke({
            "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False),
            "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False),
            "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
            "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
            "query": query,
        })

        logger.info(f"生成的SQL：{result}")

        # 输出解析（PRD 四.4）：空输出 → 生成失败；CLARIFY 行 → 澄清追问；否则为 SQL
        try:
            sql = parse_generation_output(result)
        except QueryFlowError:
            writer({"type": "progress", "step": step, "status": "error"})
            raise

        writer({"type": "progress", "step": step, "status": "success"})
        return {"sql": sql}
    except QueryFlowError:
        # CLARIFY / REJECT / 生成失败按原 code 下发，不得包装成其他错误
        raise
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        # LLM 调用异常也走 SqlGenerationError 话术（PRD 四.4：SQL生成失败）
        raise SqlGenerationError()
