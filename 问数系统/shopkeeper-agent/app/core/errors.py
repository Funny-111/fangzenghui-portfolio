"""
受控异常与话术

对应 PRD 四.4 异常流程、五a.4 拒答/转人工/失败话术、六.5 高风险阻断规则。
所有业务异常走 QueryFlowError 子类，携带 code + message + need_clarification，
由 QueryService 统一包装成结构化 SSE error 消息。
"""


class QueryFlowError(Exception):
    """业务流程异常基类，携带 PRD 约定的 code 和话术"""

    code: str = "internal_error"
    message: str = "【系统内部错误】"
    need_clarification: bool = False

    def __init__(self, message: str | None = None, need_clarification: bool | None = None):
        self.message = message or self.message
        if need_clarification is not None:
            self.need_clarification = need_clarification
        super().__init__(self.message)


class RecallEmptyError(QueryFlowError):
    """三路召回全部为空 → PRD 四.4：【未找到相关数据表或字段，请尝试换一种表述】"""

    code = "recall_empty"
    message = "【未找到相关数据表或字段，请尝试换一种表述】"
    need_clarification = False


class SqlGenerationError(QueryFlowError):
    """LLM 生成失败或空输出 → PRD 四.4：【无法理解该问题，请尝试更具体的问法】"""

    code = "sql_generation_failed"
    message = "【无法理解该问题，请尝试更具体的问法】"
    need_clarification = True


class ClarificationNeededError(QueryFlowError):
    """问题过于笼统或口径歧义 → PRD 四.4：前端展示提示，引导用户补全信息

    话术由 generate_sql 根据 LLM 的 CLARIFY 输出动态传入，
    need_clarification 随 SSE error 事件下发，前端据此渲染追问面板。
    """

    code = "need_clarification"
    message = "【请补充必要信息后再查询】"
    need_clarification = True


class SqlBlockedError(QueryFlowError):
    """非 SELECT / 多语句 / 黑名单 / 注入 → PRD 六.5：拦截不执行"""

    code = "sql_blocked"
    message = "【该问题超出系统支持范围】"
    need_clarification = False


class SensitiveFieldError(QueryFlowError):
    """敏感字段拦截 → PRD 六.5：【该字段涉及隐私数据，无权查询】（生产预留）"""

    code = "sensitive_field"
    message = "【该字段涉及隐私数据，无权查询】"
    need_clarification = False


class SqlCorrectionFailedError(QueryFlowError):
    """校正 1 次后仍失败 → PRD 四.4：【查询生成失败】+ 原始报错"""

    code = "sql_correction_failed"
    message = "【查询生成失败】"
    need_clarification = False


class SqlExecutionError(QueryFlowError):
    """SQL 执行失败 → PRD 四.4：【查询执行失败】+ 原始报错"""

    code = "sql_execution_error"
    message = "【查询执行失败】"
    need_clarification = False


class QueryTimeoutError(QueryFlowError):
    """查询超时 → PRD 四.4：【查询量过大，请调整查询信息范围或问题】"""

    code = "query_timeout"
    message = "【查询量过大，请调整查询信息范围或问题】"
    need_clarification = False


class LlmBudgetExceededError(QueryFlowError):
    """LLM 调用超上限 → PRD 六a.4"""

    code = "llm_budget_exceeded"
    message = "【查询生成失败】"
    need_clarification = False
