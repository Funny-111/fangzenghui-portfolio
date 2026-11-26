from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.conf.app_config import app_config
from app.core.badcase import record_badcase
from app.core.errors import SqlBlockedError, SqlCorrectionFailedError
from app.core.log import logger
from app.core.sql_safety import check_sql


async def validate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """SQL 校验节点：安全闸口 + EXPLAIN 校验 + 校正次数控制"""
    step = "校验SQL"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})

    sql = state["sql"]
    correction_count = state.get("correction_count", 0)
    max_correction = app_config.safety.max_correction

    # 安全闸口：非 SELECT / 多语句 / 黑名单 / 敏感字段 → 直接拦截
    guard = check_sql(sql)
    if not guard.ok:
        logger.warning(f"SQL 安全拦截：{guard.message}（SQL: {sql}）")
        record_badcase(
            query=state["query"], code=guard.code or "sql_blocked",
            message=guard.message, source="validate_sql", sql=sql,
        )
        writer({"type": "progress", "step": step, "status": "error"})
        if guard.code == "sensitive_field":
            from app.core.errors import SensitiveFieldError
            raise SensitiveFieldError(guard.message)
        raise SqlBlockedError(guard.message)

    dw_mysql_repository = runtime.context["dw_mysql_repository"]

    try:
        await dw_mysql_repository.validate(sql)
        writer({"type": "progress", "step": step, "status": "success"})
        logger.info("SQL语法正确")
        return {"error": None, "validation_status": "pass"}
    except Exception as e:
        # 校正次数已达上限，本次失败为最终失败 → 终止执行（PRD 四.4 不可纠正分支）
        if correction_count >= max_correction:
            writer({"type": "progress", "step": step, "status": "error"})
            logger.error(f"SQL 校正次数已达上限（{max_correction}），最终失败：{e}")
            raise SqlCorrectionFailedError(
                f"【查询生成失败】数据库错误：{str(e)}"
            )

        # 未达上限，写入错误，交给条件边进入 correct_sql
        writer({"type": "progress", "step": step, "status": "success"})
        logger.info(f"SQL语法错误（第{correction_count + 1}次校验）：{str(e)}")
        return {"error": str(e), "validation_status": "fail"}
