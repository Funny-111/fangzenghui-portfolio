"""badcase 落盘 —— PRD 六.5：拦截命中时「记录日志并记入 badcase」

所有安全拦截（入口注入预检 / SQL 校验闸口 / 执行前防御）统一追加到
logs/badcase.jsonl，一行一事件，供 badcase→评测集回流（PRD 十.1）。
"""
import json
from datetime import datetime
from pathlib import Path

from app.conf.app_config import app_config
from app.core.context import request_id_ctx_var
from app.core.log import logger

BADCASE_PATH = Path(app_config.logging.file.path) / "badcase.jsonl"


def record_badcase(
    *,
    query: str,
    code: str,
    message: str,
    source: str,
    sql: str | None = None,
    path: Path | None = None,
) -> None:
    """追加一条 badcase 记录。source 标明拦截发生在哪一处闸口。"""
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "request_id": str(request_id_ctx_var.get()),  # 上下文里是 UUID，落盘必须转 str
        "source": source,  # entry_guard / validate_sql / run_sql
        "code": code,      # sql_blocked / sensitive_field 等
        "message": message,
        "query": query,
        "sql": sql,
    }
    target = path or BADCASE_PATH
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        # 坏账本不能拖垮主链路：记日志失败只告警不抛错
        logger.error(f"badcase 落盘失败：{e}")
        return
    logger.warning(f"badcase 记录：source={source} code={code}")
