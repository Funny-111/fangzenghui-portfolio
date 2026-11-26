from contextvars import ContextVar

from langchain_core.callbacks import BaseCallbackHandler
from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config

# 每请求一份的 LLM 用量状态（ContextVar 存可变 dict：graph 子任务复制上下文时共享同一 dict 引用，
# 任务内的累加对请求级读取可见——若存不可变 int，子任务 set 无法传播回父任务）
# 内容：calls=调用次数（PRD 六a.4 预算）、input_tokens/output_tokens=成本统计（面试对比实验数据源）
_llm_state_ctx: ContextVar[dict] = ContextVar(
    "llm_state",
    default={"calls": 0, "input_tokens": 0, "output_tokens": 0},
)


class _LlmUsageCallback(BaseCallbackHandler):
    """每次 LLM 调用：开始时累加次数，结束时累加 token 用量"""

    def on_llm_start(self, serialized, prompts, **kwargs):
        _llm_state_ctx.get()["calls"] += 1

    def on_llm_end(self, response, **kwargs):
        # 用量字段路径因 provider 而异：优先 llm_output.usage，其次首条消息的 usage_metadata
        llm_output = getattr(response, "llm_output", None) or {}
        usage = llm_output.get("usage") or llm_output.get("token_usage") or {}
        if not usage:
            generations = getattr(response, "generations", None) or []
            if generations and generations[0]:
                message = getattr(generations[0][0], "message", None)
                usage = getattr(message, "usage_metadata", None) or {}
        state = _llm_state_ctx.get()
        state["input_tokens"] += int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
        state["output_tokens"] += int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)


def get_llm_call_count() -> int:
    """获取当前请求的 LLM 调用次数"""
    return _llm_state_ctx.get()["calls"]


def get_llm_usage() -> dict:
    """获取当前请求的 LLM token 用量 {"input_tokens", "output_tokens"}"""
    state = _llm_state_ctx.get()
    return {"input_tokens": state["input_tokens"], "output_tokens": state["output_tokens"]}


def reset_llm_call_count():
    """在请求开始时重置计数与用量（由 QueryService 调用，须在创建图任务之前）"""
    _llm_state_ctx.set({"calls": 0, "input_tokens": 0, "output_tokens": 0})


# 统一从配置读取模型三件套，节点只复用 llm，不重复初始化模型连接
# provider 默认 anthropic（MiMo 使用 Anthropic Messages 协议）；可经 LLM_PROVIDER 环境变量切换
_base_llm = init_chat_model(
    model=app_config.llm.model_name,
    model_provider=app_config.llm.provider,
    base_url=app_config.llm.base_url,
    api_key=app_config.llm.api_key,
    temperature=0,
)

# 推理型模型（如 deepseek-flash）默认会先输出 thinking：对关键词抽取、表过滤这类
# 结构化任务没有收益，却会占满 max_tokens 导致正文为空、JSON 解析失败，并成倍抬高
# 输出 token 成本。配置 thinking=disabled 可关闭（LLM_THINKING 环境变量控制）。
_thinking_overrides = (
    {"thinking": {"type": "disabled"}} if app_config.llm.thinking == "disabled" else {}
)

# 挂载计数与用量回调，每次 invoke/ainvoke 自动累加
llm = _base_llm.bind(**_thinking_overrides).with_config(callbacks=[_LlmUsageCallback()])

if __name__ == "__main__":
    print(llm.invoke("你好").content)
    print(f"LLM 调用次数: {get_llm_call_count()}")
    print(f"LLM 用量: {get_llm_usage()}")
