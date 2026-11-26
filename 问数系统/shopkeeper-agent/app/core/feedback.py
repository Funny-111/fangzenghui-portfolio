"""用户反馈落盘 —— PRD 七.2 用户反馈（点赞/点踩 + 采纳率埋点）

结果卡 👍/👎 → POST /api/feedback → logs/feedback.jsonl 一行一事件。
rating=down 必须带 reason（召回错 / 生成错 / 理解错，PRD 七.2 口径）。
采纳率 = up / (up + down)，按 query_id 去重后可直接统计。
"""
import json
from datetime import datetime
from pathlib import Path

from app.conf.app_config import app_config
from app.core.log import logger

FEEDBACK_PATH = Path(app_config.logging.file.path) / "feedback.jsonl"


def record_feedback(
    *,
    query_id: str,
    query: str,
    rating: str,
    reason: str | None = None,
    path: Path | None = None,
) -> None:
    """追加一条用户反馈记录。落盘失败只告警，不影响接口返回。"""
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "query_id": query_id,
        "query": query,
        "rating": rating,  # up / down
        "reason": reason,  # 点踩原因：召回错 / 生成错 / 理解错
    }
    target = path or FEEDBACK_PATH
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.error(f"反馈落盘失败：{e}")
        return
    logger.info(f"用户反馈：rating={rating} reason={reason} query_id={query_id}")
