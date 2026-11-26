from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from omegaconf import OmegaConf

# 从当前文件 app/conf/app_config.py 出发，回到项目根目录
project_root = Path(__file__).parents[2]

# 先加载根目录下的 .env，让 ${oc.env:LLM_API_KEY} 能找到环境变量
# 显式指定路径，不依赖运行时的当前工作目录
load_dotenv(project_root / ".env")

# 再定位到 conf/app_config.yaml 这个配置文件
config_file = project_root / "conf" / "app_config.yaml"


# 文件日志配置，对应 logging.file 这一组参数
@dataclass
class File:
    enable: bool
    level: str
    path: str
    rotation: str
    retention: str


# 控制台日志配置，对应 logging.console 这一组参数
@dataclass
class Console:
    enable: bool
    level: str


# 把 file 和 console 两组日志配置再组合成 logging 总配置
@dataclass
class LoggingConfig:
    file: File
    console: Console


# 数据库配置
# 这里的结构既会给元数据库 db_meta 用，也会给数据仓库模拟库 db_dw 用
@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class QdrantConfig:
    host: str
    port: int
    embedding_size: int


# Embedding 服务配置，对应 YAML 里的 embedding 分组
@dataclass
class EmbeddingConfig:
    host: str
    port: int
    model: str


# Elasticsearch 配置，对应 YAML 里的 es 分组
@dataclass
class ESConfig:
    host: str
    port: int
    index_name: str


# 大模型配置，对应 YAML 里的 llm 分组
# provider/model_name/base_url 支持环境变量覆盖，便于对比不同模型（LLM_PROVIDER/LLM_MODEL/LLM_BASE_URL）
@dataclass
class LLMConfig:
    provider: str
    model_name: str
    api_key: str
    base_url: str
    # 推理型模型的 thinking 开关（enabled / disabled）。
    # 抽取、过滤等结构化任务不需要推理，thinking 会占满输出上限并抬高 token 成本
    thinking: str = "enabled"


# 安全与预算配置，对应 YAML 里的 safety 分组
@dataclass
class SafetyConfig:
    sql_timeout_seconds: int
    max_result_rows: int
    max_correction: int
    max_llm_calls: int
    sensitive_columns: list
    # 单次查询总耗时预算（PRD 六a.4；修订 10：30s→60s，见资料/PRD修订指引.md）
    total_budget_seconds: int


# AppConfig 是整个项目配置的总入口
# 这里的字段名，需要和 app_config.yaml 的顶层字段保持一致
@dataclass
class AppConfig:
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig
    safety: SafetyConfig
    # 降级演示开关（PRD 八.3）：DEGRADED_MODE=true 时强制进入简易模式，
    # 所有响应带 degraded 标记，前端亮【当前为简易模式】横幅
    degraded_mode: bool = False


# 读取 YAML 配置内容
context = OmegaConf.load(config_file)

# 根据 AppConfig 生成一份“结构化配置 schema”
schema = OmegaConf.structured(AppConfig)

# 把“配置结构”和“配置值”合并，再转换成真正可直接访问属性的对象
app_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))

if __name__ == '__main__':
    # 简单测试：验证配置是否能正常读取
    print(app_config.es.host)
