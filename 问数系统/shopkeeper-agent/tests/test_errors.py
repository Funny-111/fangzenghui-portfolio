"""
PRD 话术与异常映射测试
"""
import pytest

from app.core.errors import (
    ClarificationNeededError,
    LlmBudgetExceededError,
    QueryFlowError,
    QueryTimeoutError,
    RecallEmptyError,
    SensitiveFieldError,
    SqlBlockedError,
    SqlCorrectionFailedError,
    SqlExecutionError,
    SqlGenerationError,
)


class TestQueryFlowError:
    """QueryFlowError 基类与话术映射"""

    def test_recall_empty_message(self):
        e = RecallEmptyError()
        assert e.code == "recall_empty"
        assert "未找到相关数据表或字段" in e.message
        assert e.need_clarification is False

    def test_sql_generation_failed_message(self):
        e = SqlGenerationError()
        assert e.code == "sql_generation_failed"
        assert "无法理解该问题" in e.message
        assert e.need_clarification is True

    def test_clarification_needed_default_and_custom_message(self):
        # 默认话术
        e = ClarificationNeededError()
        assert e.code == "need_clarification"
        assert e.need_clarification is True
        assert "补充必要信息" in e.message
        # LLM CLARIFY 输出的动态追问作为话术
        e2 = ClarificationNeededError("请补充时间范围和对比维度")
        assert e2.message == "请补充时间范围和对比维度"
        assert e2.need_clarification is True
        # 必须是 QueryFlowError 子类，才能被 QueryService 统一包装成 SSE error
        assert isinstance(e2, QueryFlowError)

    def test_sql_blocked_message(self):
        e = SqlBlockedError()
        assert e.code == "sql_blocked"
        assert "超出系统支持范围" in e.message

    def test_sensitive_field_message(self):
        e = SensitiveFieldError()
        assert e.code == "sensitive_field"
        assert "隐私数据" in e.message

    def test_sql_correction_failed_message(self):
        e = SqlCorrectionFailedError("【查询生成失败】数据库错误：Unknown column")
        assert e.code == "sql_correction_failed"
        assert "查询生成失败" in e.message
        assert "Unknown column" in e.message

    def test_sql_execution_error_message(self):
        e = SqlExecutionError("【查询执行失败】超时")
        assert e.code == "sql_execution_error"
        assert "查询执行失败" in e.message

    def test_query_timeout_message(self):
        e = QueryTimeoutError()
        assert e.code == "query_timeout"
        assert "查询量过大" in e.message

    def test_llm_budget_exceeded_message(self):
        e = LlmBudgetExceededError()
        assert e.code == "llm_budget_exceeded"

    def test_base_class_defaults(self):
        e = QueryFlowError()
        assert e.code == "internal_error"
        assert e.need_clarification is False

    def test_need_clarification_override(self):
        e = QueryFlowError(need_clarification=True)
        assert e.need_clarification is True

    def test_custom_message(self):
        e = QueryFlowError("自定义消息")
        assert e.message == "自定义消息"

    def test_all_subclasses_inherit_base(self):
        subclasses = [
            RecallEmptyError, SqlGenerationError, SqlBlockedError,
            SensitiveFieldError, SqlCorrectionFailedError,
            SqlExecutionError, QueryTimeoutError, LlmBudgetExceededError,
        ]
        for cls in subclasses:
            e = cls()
            assert isinstance(e, QueryFlowError)
            assert isinstance(e.code, str)
            assert isinstance(e.message, str)
