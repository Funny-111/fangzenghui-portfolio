from dataclasses import asdict

from sqlalchemy import select

from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.models.column_info_mysql import ColumnInfoMySQL
from app.models.table_info_mysql import TableInfoMySQL
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.column_metric_mapper import ColumnMetricMapper
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper


class MetaMySQLRepository:
    def __init__(self, session):
        self.session = session

    # ============ 写入方法 ============

    async def save_table_infos(self, table_infos: list[TableInfo]):
        models = [TableInfoMapper.to_model(table_info) for table_info in table_infos]
        self.session.add_all(models)

    async def save_column_infos(self, column_infos: list[ColumnInfo]):
        models = [ColumnInfoMapper.to_model(column_info) for column_info in column_infos]
        self.session.add_all(models)

    async def save_metric_infos(self, metric_infos: list[MetricInfo]):
        models = [MetricInfoMapper.to_model(metric_info) for metric_info in metric_infos]
        self.session.add_all(models)

    async def save_column_metrics(self, column_metrics: list[ColumnMetric]):
        models = [ColumnMetricMapper.to_model(column_metric) for column_metric in column_metrics]
        self.session.add_all(models)

    # ============ 查询方法（第 12 章新增） ============

    async def get_column_info_by_id(self, id: str) -> ColumnInfo | None:
        """按字段 id 查询字段元数据"""
        column_info: ColumnInfoMySQL | None = await self.session.get(ColumnInfoMySQL, id)
        if column_info:
            return ColumnInfoMapper.to_entity(column_info)
        return None

    async def get_table_info_by_id(self, id: str) -> TableInfo | None:
        """按表 id 查询表元数据"""
        table_info: TableInfoMySQL | None = await self.session.get(TableInfoMySQL, id)
        if table_info:
            return TableInfoMapper.to_entity(table_info)
        return None

    async def get_key_columns_by_table_id(self, table_id: str) -> list[ColumnInfo]:
        """查询指定表的主外键字段"""
        # 走 ORM 而不是裸 SQL：examples / alias 是 JSON 列，
        # 只有带上 ORM 列类型信息，SQLAlchemy 才会把 JSON 字符串反序列化成 list
        stmt = select(ColumnInfoMySQL).where(
            ColumnInfoMySQL.table_id == table_id,
            ColumnInfoMySQL.role.in_(("primary_key", "foreign_key")),
        )
        result = await self.session.scalars(stmt)
        return [ColumnInfoMapper.to_entity(model) for model in result.all()]
