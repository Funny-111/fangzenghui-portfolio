from sqlalchemy import text


class DWMySQLRepository:
    def __init__(self, session):
        self.session = session

    async def get_column_types(self, table_name: str) -> dict[str, str]:
        # 查询一张表所有字段的真实类型
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        return {row.Field: row.Type for row in result.fetchall()}

    async def get_column_values(self, table_name: str, column_name: str, limit: int):
        # 查询某个字段的一部分真实取值作为示例
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return result.scalars().fetchall()

    async def get_db_info(self):
        """读取当前数仓数据库的方言和版本，供 SQL 生成提示词使用"""
        sql = "select version()"
        result = await self.session.execute(text(sql))
        version = result.scalar()
        dialect = self.session.bind.dialect.name
        return {"dialect": dialect, "version": version}

    async def validate(self, sql: str):
        """用 explain 让数据库解析 SQL，提前发现语法、表名、字段名等问题"""
        sql = f"explain {sql}"
        await self.session.execute(text(sql))

    async def run(self, sql: str) -> list[dict]:
        """执行 SQL 并返回字典列表"""
        result = await self.session.execute(text(sql))
        return [dict(row) for row in result.mappings().fetchall()]
