"""
generate_sql 输出解析（PRD 四.4）

LLM 输出四种形态：
1. 正常 SQL 文本 → 返回
2. `CLARIFY: <追问>` 行（问题模糊/口径歧义）→ 抛 ClarificationNeededError，
   话术即追问内容，由 QueryService 包装成 need_clarification=true 的 SSE error
3. `REJECT` 行（字段/指标不存在或非统计问题）→ 抛 RecallEmptyError，
   使用 PRD 五a.4 固定拒答话术，禁止模型自拟
4. 空输出 → 抛 SqlGenerationError

独立成模块是为了让解析逻辑不依赖 LLM 客户端初始化，可被单测直接覆盖。
"""
from app.core.errors import ClarificationNeededError, RecallEmptyError, SqlGenerationError

CLARIFY_PREFIX = "CLARIFY:"
REJECT_PREFIX = "REJECT"


def parse_generation_output(raw: str | None) -> str:
    """解析 generate_sql 的 LLM 输出，返回可执行的 SQL 文本"""
    stripped = (raw or "").strip()
    if not stripped:
        raise SqlGenerationError()
    if stripped.startswith(CLARIFY_PREFIX):
        clarification = stripped[len(CLARIFY_PREFIX):].strip()
        raise ClarificationNeededError(clarification or None)
    # 拒答：只认独立的 REJECT 行，话术固定用 PRD 原文（不采信模型自拟文本）
    if stripped.upper().startswith(REJECT_PREFIX):
        raise RecallEmptyError()
    return stripped
