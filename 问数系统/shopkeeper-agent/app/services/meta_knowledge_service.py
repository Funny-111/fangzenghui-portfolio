import uuid
from dataclasses import asdict
from pathlib import Path

from omegaconf import OmegaConf

from app.conf.meta_config import MetaConfig
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class MetaKnowledgeService:
    """负责串联元数据知识库构建流程的应用服务"""

    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        embedding_client,
        value_es_repository: ValueESRepository,
        metric_qdrant_repository: MetricQdrantRepository,
    ):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.embedding_client = embedding_client
        self.value_es_repository = value_es_repository
        self.metric_qdrant_repository = metric_qdrant_repository

    async def _save_tables_to_meta_db(self, meta_config: MetaConfig) -> list[ColumnInfo]:
        """把配置里的表字段信息补齐后写入 Meta MySQL"""
        table_infos: list[TableInfo] = []
        column_infos: list[ColumnInfo] = []

        for table in meta_config.tables:
            table_info = TableInfo(
                id=table.name,
                name=table.name,
                role=table.role,
                description=table.description,
            )
            table_infos.append(table_info)

            # 去 DW 查这张表所有字段的真实类型
            column_types: dict[str, str] = await self.dw_mysql_repository.get_column_types(
                table.name
            )

            for column in table.columns:
                column_values: list = await self.dw_mysql_repository.get_column_values(
                    table.name, column.name, 10
                )
                column_info = ColumnInfo(
                    id=f"{table.name}.{column.name}",
                    name=column.name,
                    type=column_types[column.name],
                    role=column.role,
                    examples=column_values,
                    description=column.description,
                    alias=column.alias,
                    table_id=table.name,
                )
                column_infos.append(column_info)

        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.save_table_infos(table_infos)
            await self.meta_mysql_repository.save_column_infos(column_infos)

        logger.info(f"已保存 {len(table_infos)} 张表、{len(column_infos)} 个字段到元数据库")
        return column_infos

    async def _save_column_info_to_qdrant(self, column_infos: list[ColumnInfo]):
        """把字段元数据推进成可语义检索的 Qdrant 向量点"""
        await self.column_qdrant_repository.ensure_collection()

        points: list[dict] = []
        for column_info in column_infos:
            # 字段名建一个 point
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": column_info.name,
                    "payload": asdict(column_info),
                }
            )
            # 字段描述建一个 point
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": column_info.description,
                    "payload": asdict(column_info),
                }
            )
            # 每个别名各建一个 point
            for alia in column_info.alias:
                points.append(
                    {
                        "id": uuid.uuid4(),
                        "embedding_text": alia,
                        "payload": asdict(column_info),
                    }
                )

        # 逐条调用 Embedding 服务，避免并发过高触发 TEI 限流
        # feature_extraction 返回 List[List[float]]，单条文本需取 [0] 解包
        embeddings: list[list[float]] = []
        embedding_texts = [point["embedding_text"] for point in points]
        for text in embedding_texts:
            result = await self.embedding_client.feature_extraction(text)
            embeddings.append(result[0])

        ids = [point["id"] for point in points]
        payloads = [point["payload"] for point in points]
        await self.column_qdrant_repository.upsert(ids, embeddings, payloads)
        logger.info(f"已为 {len(column_infos)} 个字段建立向量索引（共 {len(points)} 个 point）")

    async def _save_value_info_to_es(
        self, meta_config: MetaConfig, column_infos: list[ColumnInfo]
    ):
        """把允许同步的字段真实取值写入 Elasticsearch 全文索引"""
        await self.value_es_repository.ensure_index()

        # 构建"字段id -> 是否同步"的快速查询表
        column2sync: dict[str, bool] = {}
        for table in meta_config.tables:
            for column in table.columns:
                column2sync[f"{table.name}.{column.name}"] = column.sync

        value_infos: list[ValueInfo] = []
        for column_info in column_infos:
            if column2sync[column_info.id]:
                # 查该字段的全部真实取值
                current_values = await self.dw_mysql_repository.get_column_values(
                    column_info.table_id, column_info.name, 100000
                )
                current_value_infos = [
                    ValueInfo(
                        id=f"{column_info.id}.{value}",
                        value=value,
                        column_id=column_info.id,
                    )
                    for value in current_values
                ]
                value_infos.extend(current_value_infos)

        await self.value_es_repository.index(value_infos)
        logger.info(f"已为字段取值建立全文索引（共 {len(value_infos)} 条值记录）")

    async def _save_metrics_to_meta_db(self, meta_config: MetaConfig) -> list[MetricInfo]:
        """把指标信息和字段依赖关系写入 Meta MySQL"""
        metric_infos: list[MetricInfo] = []
        column_metrics: list[ColumnMetric] = []

        for metric in meta_config.metrics:
            metric_info = MetricInfo(
                id=metric.name,
                name=metric.name,
                description=metric.description,
                relevant_columns=metric.relevant_columns,
                alias=metric.alias,
            )
            metric_infos.append(metric_info)

            for column in metric.relevant_columns:
                column_metric = ColumnMetric(column_id=column, metric_id=metric.name)
                column_metrics.append(column_metric)

        async with self.meta_mysql_repository.session.begin():
            await self.meta_mysql_repository.save_metric_infos(metric_infos)
            await self.meta_mysql_repository.save_column_metrics(column_metrics)

        logger.info(f"已保存 {len(metric_infos)} 个指标到元数据库")
        return metric_infos

    async def _save_metrics_to_qdrant(self, metric_infos: list[MetricInfo]):
        """把指标元数据推进成可语义检索的 Qdrant 向量点"""
        await self.metric_qdrant_repository.ensure_collection()

        points: list[dict] = []
        for metric_info in metric_infos:
            # 指标名建一个 point
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": metric_info.name,
                    "payload": asdict(metric_info),
                }
            )
            # 指标描述建一个 point
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": metric_info.description,
                    "payload": asdict(metric_info),
                }
            )
            # 每个别名各建一个 point
            for alia in metric_info.alias:
                points.append(
                    {
                        "id": uuid.uuid4(),
                        "embedding_text": alia,
                        "payload": asdict(metric_info),
                    }
                )

        # feature_extraction 返回 List[List[float]]，单条文本需取 [0] 解包
        embeddings: list[list[float]] = []
        embedding_texts = [point["embedding_text"] for point in points]
        for text in embedding_texts:
            result = await self.embedding_client.feature_extraction(text)
            embeddings.append(result[0])

        ids = [point["id"] for point in points]
        payloads = [point["payload"] for point in points]
        await self.metric_qdrant_repository.upsert(ids, embeddings, payloads)
        logger.info(f"已为 {len(metric_infos)} 个指标建立向量索引（共 {len(points)} 个 point）")

    async def build(self, config_path: Path):
        """读取配置并依次构建 Meta MySQL、Qdrant 和 ES 中的元数据索引"""
        context = OmegaConf.load(config_path)
        schema = OmegaConf.structured(MetaConfig)
        meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))
        logger.info("加载配置文件")

        # 表链路：入库 -> 向量索引 -> 全文索引
        if meta_config.tables:
            column_infos = await self._save_tables_to_meta_db(meta_config)
            await self._save_column_info_to_qdrant(column_infos)
            await self._save_value_info_to_es(meta_config, column_infos)

        # 指标链路：入库 -> 向量索引
        if meta_config.metrics:
            metric_infos = await self._save_metrics_to_meta_db(meta_config)
            await self._save_metrics_to_qdrant(metric_infos)

        logger.info("元数据知识库构建完成")
