"""
SQL 安全闸口

对应 PRD 六.5 高风险场景强制阻断规则（非 SELECT / 黑名单 / 敏感字段 / 注入）和六a.2 工具白名单。
所有检查为纯函数，可单独单测。
"""

import re
from dataclasses import dataclass

from app.conf.app_config import app_config


@dataclass
class GuardResult:
    """闸口检查结果"""

    ok: bool
    code: str | None = None
    message: str | None = None


# 黑名单关键字（词边界匹配，不区分大小写）
_BLACKLIST = (
    r"insert|update|delete|drop|alter|create|truncate|"
    r"grant|revoke|call|load_file|outfile|dumpfile|sleep|benchmark|"
    r"union\s+select"
)
_blacklist_re = re.compile(rf"\b({_BLACKLIST})\b", re.IGNORECASE)

# 首关键字允许的 SQL 语句类型（只读 SELECT）
_select_re = re.compile(r"^select\b", re.IGNORECASE)

# 注入特征（用户问题层）
_injection_patterns = (
    r";",
    r"--",
    r"/\*",
    r"#",
    r"union\s+select",
    r"information_schema",
    r"or\s+1\s*=\s*1",
    r"'\s*or\s*'",
    r"xp_cmdshell",
    r"drop\s+table",
)
_injection_re = re.compile("|".join(_injection_patterns), re.IGNORECASE)


def check_sql(sql: str) -> GuardResult:
    """
    检查生成/校正后的 SQL 是否安全。
    返回 GuardResult(ok=True) 通过；ok=False 时携带 code 和 message。
    """
    if not sql or not sql.strip():
        return GuardResult(ok=False, code="sql_blocked", message="【SQL 为空，无法执行】")

    stripped = sql.strip()

    # 多语句检测：去掉尾分号后，仍有分号 → 拦截
    body = stripped.rstrip(";")
    if ";" in body:
        return GuardResult(
            ok=False, code="sql_blocked", message="【该问题超出系统支持范围】"
        )

    # 首关键字必须是 SELECT
    if not _select_re.match(stripped):
        return GuardResult(
            ok=False, code="sql_blocked", message="【该问题超出系统支持范围】"
        )

    # 黑名单词检测
    if _blacklist_re.search(stripped):
        return GuardResult(
            ok=False, code="sql_blocked", message="【该问题超出系统支持范围】"
        )

    # 敏感字段检测（读配置，生产预留）
    sensitive_columns = getattr(app_config.safety, "sensitive_columns", []) or []
    for col in sensitive_columns:
        if re.search(rf"\b{re.escape(col)}\b", stripped, re.IGNORECASE):
            return GuardResult(
                ok=False,
                code="sensitive_field",
                message="【该字段涉及隐私数据，无权查询】",
            )

    return GuardResult(ok=True)


def check_query_input(query: str) -> GuardResult:
    """
    检查用户输入的自然语言问题是否包含 SQL 注入特征。
    用于 QueryService 入口预检，拦截后不进入图执行。
    """
    if not query or not query.strip():
        return GuardResult(ok=True)  # 空输入由 Pydantic 校验处理

    if _injection_re.search(query):
        return GuardResult(
            ok=False, code="sql_blocked", message="【该问题超出系统支持范围】"
        )

    return GuardResult(ok=True)
