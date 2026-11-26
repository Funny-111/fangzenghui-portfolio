from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import (
    ColumnInfoState,
    DataAgentState,
    MetricInfoState,
    TableInfoState,
)
from app.core.errors import RecallEmptyError
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo


async def merge_retrieved_info(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "合并召回信息"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        retrieved_column_infos = state["retrieved_column_infos"]
        retrieved_metric_infos = state["retrieved_metric_infos"]
        retrieved_value_infos = state["retrieved_value_infos"]
        meta_mysql_repository = runtime.context["meta_mysql_repository"]

        # 召回空检测（PRD 四.4）：三路全空 → 提示用户换一种表述
        if not retrieved_column_infos and not retrieved_metric_infos and not retrieved_value_infos:
            writer({"type": "progress", "step": step, "status": "error"})
            raise RecallEmptyError()

        # 1. 字段按 id 转 Map
        col_map = {c.id: c for c in retrieved_column_infos}

        # 2. 补齐指标依赖字段
        for m in retrieved_metric_infos:
            for rc in m.relevant_columns:
                if rc not in col_map:
                    c = await meta_mysql_repository.get_column_info_by_id(rc)
                    if c:
                        col_map[rc] = c

        # 3. 补齐字段取值到 examples
        for v in retrieved_value_infos:
            if v.column_id not in col_map:
                c = await meta_mysql_repository.get_column_info_by_id(v.column_id)
                if c:
                    col_map[v.column_id] = c
            if v.column_id in col_map and v.value not in col_map[v.column_id].examples:
                col_map[v.column_id].examples.append(v.value)

        # 4. 按表分组
        table_map: dict[str, list] = {}
        for c in col_map.values():
            table_map.setdefault(c.table_id, []).append(c)

        # 5. 补齐主外键
        for tid in table_map.keys():
            keys = await meta_mysql_repository.get_key_columns_by_table_id(tid)
            existing = [c.id for c in table_map[tid]]
            for k in keys:
                if k.id not in existing:
                    table_map[tid].append(k)

        # 6. 组装 TableInfoState
        table_infos = []
        for tid, cols in table_map.items():
            ti = await meta_mysql_repository.get_table_info_by_id(tid)
            columns = [
                ColumnInfoState(name=c.name, type=c.type, role=c.role,
                                examples=c.examples, description=c.description, alias=c.alias)
                for c in cols
            ]
            table_infos.append(TableInfoState(name=ti.name, role=ti.role, description=ti.description, columns=columns))

        # 7. 组装 MetricInfoState
        metric_infos = [
            MetricInfoState(name=m.name, description=m.description,
                            relevant_columns=m.relevant_columns, alias=m.alias)
            for m in retrieved_metric_infos
        ]

        logger.info(f"合并后的表信息：{[t['name'] for t in table_infos]}")
        logger.info(f"合并后的指标信息：{[m['name'] for m in metric_infos]}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"table_infos": table_infos, "metric_infos": metric_infos}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
