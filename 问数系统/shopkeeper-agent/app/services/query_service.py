import asyncio
import json
import time
from uuid import uuid4

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.llm import get_llm_call_count, get_llm_usage, reset_llm_call_count
from app.agent.state import DataAgentState
from app.conf.app_config import app_config
from app.core.badcase import record_badcase
from app.core.errors import QueryFlowError
from app.core.log import logger
from app.core.query_log import record_query_log
from app.core.sql_safety import check_query_input
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


def _sse(obj: dict) -> str:
    """把 dict 包装成 SSE 消息文本"""
    return f"data: {json.dumps(obj, ensure_ascii=False, default=str)}\n\n"


def _timeout_payload() -> dict:
    """PRD 六a.4：单次查询总耗时超预算 → 强制终止并返回查询超时话术"""
    return {
        "type": "error",
        "schema_version": "1.0",
        "code": "query_timeout",
        "message": "【查询量过大，请调整查询信息范围或问题】",
        "need_clarification": False,
        "correction_count": 0,
    }


# LLM 供应商连接/过载类失败特征（PRD 八.3 降级触发、九.3 LLM 不可用回滚条件）
_PROVIDER_PATTERNS = (
    "apiconnectionerror", "apitimeouterror", "connecterror", "readtimeout",
    "connection", "service is too busy", "service_unavailable",
    "503", "429", "temporarily unavailable", "unreachable", "max retries",
)


def provider_unavailable(detail: str) -> bool:
    """判断异常文本是否为 LLM 供应商不可用（而非业务逻辑错误）"""
    d = detail.lower()
    return any(p in d for p in _PROVIDER_PATTERNS)


class QueryService:
    """查询接口核心业务逻辑，负责调用问数工作流"""

    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        embedding_client,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        value_es_repository: ValueESRepository,
    ):
        self.meta_mysql_repository = meta_mysql_repository
        self.embedding_client = embedding_client
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository

    async def query(self, query: str):
        """执行问数工作流，以 SSE 格式流式返回进度和结果"""
        # 本次查询的全局 ID：result 消息下发给前端，供反馈按钮回传（PRD 七.2）
        query_id = str(uuid4())

        # 降级开关（PRD 八.3）：DEGRADED_MODE=true 强制简易模式（演示用）；
        # 运行中检测到供应商不可用也会置位
        degraded = str(app_config.degraded_mode).lower() in ("true", "1", "yes")

        def _emit(obj: dict) -> str:
            # degraded 只挂终态消息（result/error），前端收到即亮简易模式横幅
            if degraded and obj.get("type") in ("result", "error"):
                obj = {**obj, "degraded": True}
            return _sse(obj)

        # 入口注入预检（PRD 六.5）：发现注入特征直接拦截，不进图
        guard = check_query_input(query)
        if not guard.ok:
            record_badcase(
                query=query, code=guard.code, message=guard.message,
                source="entry_guard",
            )
            # 入口拦截也要留流水账（PRD 七.1：每次提问一条）
            record_query_log(
                query=query, outcome="blocked", error_code=guard.code,
                elapsed_s=0.0, llm_calls=0, input_tokens=0, output_tokens=0,
            )
            yield _emit({
                "type": "error",
                "schema_version": "1.0",
                "code": guard.code,
                "message": guard.message,
                "need_clarification": False,
                "correction_count": 0,
            })
            return

        # 重置 LLM 调用计数与 token 用量（PRD 六a.4 预算 + 成本统计）
        # 必须在创建图任务之前：子任务复制上下文时共享这份状态
        reset_llm_call_count()

        # 单次查询总耗时预算（PRD 六a.4；修订 10：30s→60s，配置项 safety.total_budget_seconds）
        budget_seconds = app_config.safety.total_budget_seconds
        start_time = time.monotonic()

        state = DataAgentState(query=query)
        context = DataAgentContext(
            column_qdrant_repository=self.column_qdrant_repository,
            embedding_client=self.embedding_client,
            metric_qdrant_repository=self.metric_qdrant_repository,
            value_es_repository=self.value_es_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            dw_mysql_repository=self.dw_mysql_repository,
        )

        # 图在独立任务中运行：预算超时或客户端断开时可以真正取消，
        # 避免“浏览器已收到超时、后台仍跑完剩余 LLM 调用”的 token 浪费
        queue: asyncio.Queue = asyncio.Queue()

        async def _run_graph():
            try:
                async for chunk in graph.astream(
                    input=state,
                    context=context,
                    stream_mode="custom",
                ):
                    await queue.put(("chunk", chunk))
            except QueryFlowError as e:
                await queue.put(("flow_error", e))
            except Exception as e:  # noqa: BLE001 — 未知异常统一包装成 internal_error 下发
                await queue.put(("internal_error", e))
            finally:
                # 图已结束的哨兵：消费端收到即停止等待，避免“成功后再等到预算超时”的误报
                await queue.put(("end", None))

        task = asyncio.create_task(_run_graph())
        outcome = "unknown"
        error_code: str | None = None
        result_meta: dict = {}
        try:
            while True:
                # 墙钟预算：即使长时间没有事件返回（LLM 挂起），到点也强制终止
                remaining = budget_seconds - (time.monotonic() - start_time)
                if remaining <= 0:
                    outcome = "timeout"
                    error_code = "query_timeout"
                    yield _emit(_timeout_payload())
                    return

                try:
                    kind, payload = await asyncio.wait_for(queue.get(), timeout=remaining)
                except asyncio.TimeoutError:
                    outcome = "timeout"
                    error_code = "query_timeout"
                    yield _emit(_timeout_payload())
                    return

                if kind == "flow_error":
                    outcome = f"flow_error:{payload.code}"
                    error_code = payload.code
                    # 生成/召回环节包装的供应商连接失败 → 降级（PRD 八.3）
                    if provider_unavailable(payload.message):
                        degraded = True
                    yield _emit({
                        "type": "error",
                        "schema_version": "1.0",
                        "code": payload.code,
                        "message": payload.message,
                        "need_clarification": payload.need_clarification,
                        "correction_count": 0,
                    })
                    return

                if kind == "internal_error":
                    outcome = "internal_error"
                    error_code = "internal_error"
                    if provider_unavailable(f"{type(payload).__name__}: {payload}"):
                        degraded = True
                    yield _emit({
                        "type": "error",
                        "schema_version": "1.0",
                        "code": "internal_error",
                        "message": f"【系统内部错误】{str(payload)}",
                        "need_clarification": False,
                        "correction_count": 0,
                    })
                    return

                if kind == "end":
                    # 图正常结束（result 已在前面转发）；未收到 result 就结束也如实标记
                    if outcome != "success":
                        outcome = "ended_without_result"
                    break

                if isinstance(payload, dict) and payload.get("type") == "result":
                    outcome = "success"
                    payload["query_id"] = query_id
                    result_meta = {
                        "keywords": payload.get("keywords"),
                        "generated_sql": payload.get("generated_sql"),
                        "validation_status": payload.get("validation_status"),
                        "correction_count": payload.get("correction_count"),
                        "matched_tables": payload.get("matched_tables"),
                    }
                yield _emit(payload)
        finally:
            # 无论成功、失败还是超时，都取消图任务（已完成时 cancel 为 no-op）
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: PERF203 — 吞掉取消/收尾异常
                pass

            # 每请求一行用量日志：面试对比实验的稳定性与成本数据源（PRD 七.1 查询日志）
            usage = get_llm_usage()
            elapsed = time.monotonic() - start_time
            logger.info(
                f"查询结束：outcome={outcome} 总耗时={elapsed:.1f}s "
                f"LLM调用={get_llm_call_count()} "
                f"tokens(input={usage['input_tokens']}, output={usage['output_tokens']})"
            )
            # 结构化流水账落盘（PRD 七.1；脱敏红线见 query_log.record_query_log）
            record_query_log(
                query=query,
                outcome=outcome,
                error_code=error_code,
                elapsed_s=elapsed,
                llm_calls=get_llm_call_count(),
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                query_id=query_id,
                **result_meta,
            )
