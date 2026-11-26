import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.conf.app_config import app_config
from app.core.badcase import record_badcase
from app.core.errors import QueryTimeoutError, SqlBlockedError, SqlExecutionError
from app.core.log import logger
from app.core.sql_safety import check_sql


async def run_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "执行SQL"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})

    sql = state["sql"]
    correction_count = state.get("correction_count", 0)
    keywords = state.get("keywords", [])
    table_infos = state.get("table_infos", [])
    metric_infos = state.get("metric_infos", [])
    retrieved_value_infos = state.get("retrieved_value_infos", [])

    # 防御性安全闸口（validate_sql 已过，此处兜底）
    guard = check_sql(sql)
    if not guard.ok:
        record_badcase(
            query=state["query"], code=guard.code or "sql_blocked",
            message=guard.message, source="run_sql", sql=sql,
        )
        writer({"type": "progress", "step": step, "status": "error"})
        raise SqlBlockedError(guard.message)

    dw_mysql_repository = runtime.context["dw_mysql_repository"]
    timeout = app_config.safety.sql_timeout_seconds
    max_rows = app_config.safety.max_result_rows

    try:
        result = await asyncio.wait_for(dw_mysql_repository.run(sql), timeout=timeout)
    except asyncio.TimeoutError:
        writer({"type": "progress", "step": step, "status": "error"})
        logger.error(f"SQL 执行超时（{timeout}s）：{sql}")
        raise QueryTimeoutError()
    except Exception as e:
        writer({"type": "progress", "step": step, "status": "error"})
        logger.error(f"SQL 执行失败：{e}")
        raise SqlExecutionError(f"【查询执行失败】数据库错误：{str(e)}")

    # 结果行数截断
    if len(result) > max_rows:
        result = result[:max_rows]
        logger.info(f"结果超过 {max_rows} 行，已截断")

    # 组装 matched_* 字段（PRD 五a.3 schema）
    matched_tables = [t["name"] for t in table_infos]
    matched_columns = [
        f"{t['name']}.{c['name']}" for t in table_infos for c in t.get("columns", [])
    ]
    matched_metrics = [
        {"name": m["name"], "source": ", ".join(m.get("alias", []))}
        for m in metric_infos
    ]
    matched_values = [
        {"value": v.value, "column": v.column_id}
        for v in retrieved_value_infos
    ]

    confidence = "high" if correction_count == 0 else "low"

    logger.info(f"SQL执行结果：{result}")
    writer({"type": "progress", "step": step, "status": "success"})
    writer({
        "type": "result",
        "schema_version": "1.0",
        "data": result,
        "generated_sql": sql,
        "validation_status": state.get("validation_status", "pass"),
        "execution_status": "success",
        "correction_count": correction_count,
        "keywords": keywords,
        "matched_tables": matched_tables,
        "matched_columns": matched_columns,
        "matched_metrics": matched_metrics,
        "matched_values": matched_values,
        "confidence": confidence,
        "unclear": [],
        "need_clarification": False,
    })
