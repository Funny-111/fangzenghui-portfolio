"""
Graph 路由逻辑测试（validate_sql 条件分支 + 校正计数边界）
"""
import pytest


def _route_after_validate(state):
    """从 graph.py 复制的路由函数（避免触发 graph import 带来的依赖初始化）"""
    if state.get("error") is None:
        return "run_sql"
    correction_count = state.get("correction_count", 0)
    if correction_count > 1:
        from app.core.errors import LlmBudgetExceededError
        raise LlmBudgetExceededError()
    return "correct_sql"


class TestRouteAfterValidate:
    """路由逻辑测试"""

    def test_error_none_routes_to_run_sql(self):
        state = {"error": None, "correction_count": 0}
        assert _route_after_validate(state) == "run_sql"

    def test_error_present_zero_corrections_routes_to_correct_sql(self):
        state = {"error": "Unknown column 'x'", "correction_count": 0}
        assert _route_after_validate(state) == "correct_sql"

    def test_error_present_one_correction_routes_to_correct_sql(self):
        # 第一次校正后 correction_count=1，error 仍在（validate_sql 内部会 raise，不会到这里）
        # 但如果到这里（防御性测试），路由仍到 correct_sql
        state = {"error": "syntax error", "correction_count": 1}
        # correction_count=1 不 > 1，所以走 correct_sql
        assert _route_after_validate(state) == "correct_sql"

    def test_error_present_corrections_exceeded_raises(self):
        from app.core.errors import LlmBudgetExceededError
        state = {"error": "syntax error", "correction_count": 2}
        with pytest.raises(LlmBudgetExceededError):
            _route_after_validate(state)
