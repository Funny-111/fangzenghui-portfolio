"""降级模式测试（PRD 八.3）"""
from app.conf.app_config import app_config
from app.services.query_service import provider_unavailable


def test_config_has_degraded_switch():
    # 开关存在且默认关闭（DEGRADED_MODE 未设时）
    assert hasattr(app_config, "degraded_mode")
    assert str(app_config.degraded_mode).lower() in ("false", "0", "")


def test_provider_unavailable_matches_503_busy():
    detail = "Error code: 503 - Service is too busy. Please switch providers."
    assert provider_unavailable(detail) is True


def test_provider_unavailable_matches_connection_error():
    assert provider_unavailable("APIConnectionError: Connection refused") is True
    assert provider_unavailable("ReadTimeoutError: timed out") is True


def test_provider_unavailable_ignores_business_errors():
    # 业务类错误不应触发降级
    assert provider_unavailable("SQL语法错误：语法不对") is False
    assert provider_unavailable("【该问题超出系统支持范围】") is False
