# 可复用 Prompt 模板库 · AI 产品工程通用版

> **用途**：分阶段驱动 AI 完成一个完整工程（环境 → 客户端 → 知识/数据层 → 智能体 → API → 交付）。
> **使用方法**：新案例开始时，把本文件 + 场景描述一起丢给 AI，AI 按模板 001→013 顺序逐阶段执行。

---

## 一、给 AI 的执行说明（新案例开始时先读这段）

1. 用户会提供新的业务场景和项目背景，先向用户确认下方「场景参数表」中缺失的信息。
2. 按模板 001 → 013 顺序，**一次只执行一个阶段**，等用户确认后再进入下一阶段。
3. 每个模板中：
   - 【项目背景】按场景参数表填写
   - 标注 `📌业务` 的内容替换为用户场景
   - 其余标注 `🔧技术` 的内容直接使用，不要改动
4. 每阶段完成后按【验收要点】自查，向用户报告实际结果，用户确认后再继续。
5. 缺少信息时列「待确认」，不要编造；用户未授权的商业能力不要自行加入范围。

---

## 二、场景参数表（执行前向用户确认）

| 参数 | 示例（电商问数） | 你的项目 |
|---|---|---|
| 业务类型 | 电商自然语言问数系统 | ___ |
| 核心能力 | NL2SQL（自然语言→SQL→查询） | ___ |
| 技术栈 | Python 3.14 + FastAPI + LangGraph | ___ |
| 包管理 | uv | ___ |
| 配置管理 | OmegaConf + YAML | ___ |
| 数据库 | MySQL（双库：元数据 + 业务数据） | ___ |
| 向量库 | Qdrant（COSINE） | ___ |
| 全文检索 | Elasticsearch + IK 中文分词 | ___ |
| Embedding | TEI + bge-large-zh-v1.5（1024 维） | ___ |
| LLM | Anthropic 协议 | ___ |
| 业务对象 | 表 / 字段 / 指标 / 字段取值 | ___ |
| 业务示例 | "统计华北地区的销售总额" → GMV 41099.5 | ___ |

---

## 三、复用速查表

| 模板 | 通用度 | 换场景需要改什么 |
|---|---|---|
| 011 FastAPI 流式接口 | ⭐⭐⭐⭐⭐ | 只改【项目背景】 |
| 012 依赖注入与 Service | ⭐⭐⭐⭐⭐ | 改【项目背景】+ 依赖对象列表 |
| 001 Qdrant + ES 客户端 | ⭐⭐⭐⭐ | 改背景 + 检索用途描述 |
| 002 MySQL + Embedding + 日志 | ⭐⭐⭐⭐ | 改背景 + 数据库名/测试表名 |
| 006 LangGraph 工作流骨架 | ⭐⭐⭐⭐ | 改背景 + 节点名字（按你的业务流程命名） |
| 013 SSE 协议 + 异常 + 日志 | ⭐⭐⭐⭐ | 改背景 + 节点名字 |
| 005 检索能力构建 | ⭐⭐⭐ | 改背景 + 召回对象（字段/指标→你的业务对象） |
| 007 关键词抽取与多路召回 | ⭐⭐⭐ | 改背景 + 召回对象 |
| 009 过滤与补全 | ⭐⭐⭐ | 改背景 + 过滤对象 + 环境信息字段 |
| 003 数据/知识库骨架 | ⭐⭐ | 改背景 + 配置文件结构（YAML 字段按你的对象定义） |
| 004 信息同步到库 | ⭐⭐ | 改背景 + 实体字段 + 同步的数据来源 |
| 008 召回信息合并 | ⭐⭐ | 改背景 + 合并规则（按你的对象关系设计） |
| 010 生成与执行闭环 | ⭐ ⚠️ | **NL2SQL 专属**。换场景需重新设计"生成→校验→执行"环节 |

> 通用度说明：⭐⭐⭐⭐⭐ = 只改背景即可；⭐⭐ = 需替换具体业务字段/结构；⭐ = 架构需重新设计。

---

## 四、模板本体

---

### 模板 001：接入检索服务客户端

**复用度**：⭐⭐⭐⭐　**阶段目标**：给系统接入向量数据库和全文检索引擎，封装成全局管理器。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14 + FastAPI，
用 uv 管理依赖，配置用 OmegaConf 加载 YAML（conf/app_config.yaml）。
项目源码在 app/ 包下，客户端放在 app/clients/ 目录。

【本次任务】
帮我接入两个检索服务的客户端，并封装成全局管理器：

1. 向量数据库（🔧技术：Qdrant）
   - 地址：从 app_config 读取（host + port）
   - 用途：📌业务：存储【你的业务对象】的向量，做语义相似度召回
   - 向量维度：📌业务：1024（按你的 Embedding 模型调整），距离度量：COSINE

2. 全文检索引擎（🔧技术：Elasticsearch）
   - 地址：从 app_config 读取（host + port）
   - 用途：📌业务：为【你的可枚举字段/取值】建立倒排索引，做全文匹配
   - 中文场景需要 IK 分词（analyzer: ik_max_word）；非中文场景用 standard

【要求】
🔧技术：
- 用异步客户端（AsyncQdrantClient / AsyncElasticsearch）
- 每个客户端封装成 Manager 类，统一 init() 和 close()
- 创建全局单例对象，方便其他模块 import 使用
- 每个文件底部附带最小可运行测试（__main__ 块）
- 代码要有中文注释，解释关键参数
- Qdrant 测试：创建 collection → 写入随机向量 → query_points 查询
- ES 测试：创建 index（显式 mapping，区分 text/keyword）→ bulk 写入 → search 查询

📌业务验收要点：
- [ ] ES mapping 中 text/keyword 的字段按你的业务对象设置
- [ ] 向量维度与你的 Embedding 模型输出一致
```

---

### 模板 002：接入数据层与日志能力

**复用度**：⭐⭐⭐⭐　**阶段目标**：接入数据库连接、Embedding 客户端、统一日志。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14 + FastAPI，
用 uv 管理依赖，配置用 OmegaConf 加载 YAML（conf/app_config.yaml）。
项目源码在 app/ 包下。基础服务通过 Docker 部署：
- MySQL 8.0（端口 3306，📌业务：两个库——元数据库 + 业务数据库）
- Text Embeddings Inference（TEI，端口 8081，📌业务：模型名 + 向量维度）

【本次任务】
帮我实现三个基础能力：

1. MySQL 客户端管理器（app/clients/mysql_client_manager.py）
   🔧技术：
   - 用 SQLAlchemy 异步（create_async_engine + async_sessionmaker）
   - 驱动：asyncmy（连接串 mysql+asyncmy://）
   - 📌业务：创建两套客户端（按你的双库命名，如 meta/dw）
   - Engine：pool_size=10, pool_pre_ping=True
   - Session：autoflush=True, expire_on_commit=False
   - 提供 session_factory 供外部按需创建 Session
   - 测试：查询 📌业务：你的业务表 前 10 条

2. Embedding 客户端管理器（app/clients/embedding_client_manager.py）
   🔧技术：
   - 用 huggingface_hub 的 AsyncInferenceClient
   - model 参数直接传 TEI 服务地址（http://host:port），不加路径后缀
   - 测试：对一段文本调用 feature_extraction，打印向量前 3 维

3. 日志系统（app/core/context.py + app/core/log.py）
   🔧技术：
   - context.py：用 ContextVar 定义 request_id 上下文变量
   - log.py：用 loguru 实现统一日志配置
     - 格式：时间、级别、request_id、模块名、函数名、行号、消息
     - 双通道输出：console + file
     - 文件日志支持 rotation（按大小切分）和 retention（按时长清理）
     - 通过 logger.patch 注入 request_id

【要求】
🔧技术：
- 所有客户端地址从 app_config 读取，不硬编码
- 全局单例模式，统一 init() 和 close()
- 异步写法（await + asyncio.run）
- 代码有中文注释

📌业务验收要点：
- [ ] MySQL 客户端能查询到你的业务表数据
- [ ] Embedding feature_extraction 返回的维度与配置一致
- [ ] 日志输出含 request_id，支持 console + file 双通道
```

---

### 模板 003：搭建数据/知识库骨架

**复用度**：⭐⭐　**阶段目标**：配置驱动的分层骨架——配置文件、配置结构、入口脚本、服务层。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14 + FastAPI。
📌业务：【核心能力的前提是先让系统知道你的业务对象结构——如表/字段/指标（NL2SQL）、
或知识条目/标签/分类（RAG）、或工单类型/状态/优先级（工单系统）】。
项目采用分层架构：scripts（入口）→ services（业务）→ repositories（存储）。

【本次任务】
帮我搭建骨架，共 4 个文件：

1. conf/[你的配置文件名].yaml — 配置驱动的同步/构建清单
   📌业务：YAML 顶层结构按你的对象设计，例如：
   - NL2SQL：tables（表）+ metrics（指标）
   - RAG：documents（文档）+ tags（标签）
   - 工单：ticket_types（工单类型）+ statuses（状态）
   每项含 name、description、📌业务：你的业务字段
   顶层字段都设为 Optional（可以只同步其中一部分）

2. app/conf/[配置结构].py — 配置结构定义
   🔧技术：
   - 与 YAML 顶层字段一一对应的 dataclass
   - 顶层字段 Optional[list[...]] = None
   - 用 OmegaConf 加载 YAML 并合并成对象

3. app/scripts/build_xxx.py — 入口调度脚本
   🔧技术：
   - argparse 接收 -c/--conf 参数
   - 初始化数据库客户端，创建 Repository
   - 创建 Service 并注入 Repository
   - 调用 service.build(config_path)
   - 结束后关闭连接
   - 入口只做调度，不写业务逻辑

4. app/services/xxx_service.py — 服务层骨架
   🔧技术：
   - __init__ 接收 Repository
   - build(config_path)：OmegaConf 加载 YAML → 按顶层字段分支处理（先写骨架）
   - 用 loguru 记录关键步骤

【要求】
🔧技术：
- 配置驱动：同步范围由 YAML 决定，不写死在代码里
- 分层清晰：scripts 只调度，services 只编排，repositories 只读写
- 异步写法
- 代码有中文注释
```

---

### 模板 004：信息同步到数据库

**复用度**：⭐⭐　**阶段目标**：配置描述 → 补齐真实数据 → 转实体 → 转 ORM → 事务落库。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14。
同步链路：配置文件描述对象 → 系统去源数据补齐真实信息 → 转换业务实体
→ Mapper 转 ORM → 事务写入数据库。
已有：MySQL 客户端（SQLAlchemy 异步）、loguru、OmegaConf、配置文件。

【本次任务】
帮我实现完整同步链路：

1. 业务实体（app/entities/）
   📌业务：按你的对象定义实体，例如 NL2SQL 用 TableInfo/ColumnInfo，
   RAG 用 Document/Tag，工单用 TicketType/Status。
   关键：📌业务：设计唯一 ID 格式，防止同名冲突（如"表名.字段名"）

2. ORM 模型（app/models/）
   🔧技术：base.py（DeclarativeBase）+ 每个实体一个映射文件
   📌业务：字段类型按你的数据设计（列表/字典用 JSON 类型）

3. 源数据 Repository
   📌业务：定义从哪里补齐真实信息——
   - NL2SQL：从数仓查字段类型、示例值
   - RAG：从原始文档查元信息
   - 其他：从你的数据源查

4. Mapper（app/repositories/.../mappers/）
   🔧技术：to_model()（实体→ORM，用 asdict 展开）

5. 目标库 Repository
   🔧技术：save_xxx(entities)：Mapper 转换后 session.add_all()

6. Service 层新增同步方法
   🔧技术：
   a. 遍历配置，构造实体
   b. 调源数据 Repository 补齐真实信息（不在配置里手填的字段）
   c. 开启事务（session.begin()），批量保存
   d. 返回实体列表

【关键设计】
🔧技术：
- 能自动获取的信息不在配置里手填
- 事务放在 Service 层，同批数据要么一起成功要么一起失败
- Repository 对外暴露业务实体，内部用 Mapper 转 ORM

【要求】
- 异步写法
- 代码有中文注释
```

---

### 模板 005：检索能力构建

**复用度**：⭐⭐⭐　**阶段目标**：把同步好的数据推进成可检索对象（向量索引 + 全文索引）。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14。
📌业务：【你的核心能力的检索前提——如 NL2SQL 需要字段/指标/取值三路召回，
RAG 需要文档/标签两路召回，搜索系统需要标题/正文/标签多路召回】。

【本次任务】
帮我构建检索链路：

1. 业务实体（app/entities/）
   📌业务：按你的检索对象定义（如 ValueInfo/MetricInfo/ColumnMetric）

2. ORM 模型（app/models/）
   📌业务：按你的数据表设计（联合主键、JSON 字段等）

3. 向量仓储（app/repositories/qdrant/xxx_repository.py）
   🔧技术：
   - collection_name（📌业务：按对象命名，字段/指标分开建 collection）
   - ensure_collection()：维度从配置读，distance=COSINE
   - upsert(ids, embeddings, payloads)：zip 拼 PointStruct，分批写入

4. 全文索引仓储（app/repositories/es/xxx_repository.py）
   🔧技术：
   - 显式 mapping，区分 text（搜索字段）和 keyword（ID 字段）
   - 中文用 ik_max_word 分词
   - ensure_index() + index(items)：bulk 操作行+数据行交替，分批写入

5. Service 层新增索引构建方法
   🔧技术：
   - 每个对象拆成多个向量点（📌业务：如名字+描述+别名，让不同表达都能召回）
   - 逐条调 embedding_client.feature_extraction(text)，返回值取 [0] 解包（返回类型是 [[float]]）
   - Embedding 逐条串行调用，避免 TEI 限流（MAX_CONCURRENT_REQUESTS=16）
   - point id 用 uuid4()（一个对象拆多个 point，不能用业务 id）
   - 全文索引：从配置判断哪些对象需要同步真实取值，批量写入 ES

6. build() 完整调用链
   🔧技术：[你的对象A] → 入库 → 向量索引 → 全文索引；[对象B] → 入库 → 向量索引

【关键设计】
🔧技术：
- 一个对象拆多个向量点，让不同自然语言表达都能召回
- 不同对象类型用独立 collection，召回时可区分
- feature_extraction 返回 [[float]]，单条文本取 [0] 解包
- Embedding 逐条串行，避免 429 限流

📌业务验收要点：
- [ ] Qdrant 各 collection 的 point 数不为 0
- [ ] ES 能搜到你的真实业务取值
- [ ] 数据库有对应的实体和关联记录
- [ ] 重跑不因主键冲突报错（先清空或用 upsert）
```

---

### 模板 006：搭建智能体工作流骨架

**复用度**：⭐⭐⭐⭐　**阶段目标**：用 LangGraph 搭工作流图骨架——节点、边、条件分支、流式输出，先不写业务逻辑。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14，用 LangGraph 编排智能体工作流。
📌业务：【你的前置能力已就绪——如元数据知识库/向量索引/全文索引已建好】。
现在需要搭工作流骨架，先不写业务逻辑，只验证图能跑通。

【工作流结构】
📌业务：按你的流程画图，例如 NL2SQL 是：
START → extract_keywords → 三路并行召回 → merge → 两路并行过滤
  → add_extra_context → generate_sql → validate_sql
  → 条件分支：error=None → run_sql → END / error≠None → correct_sql → run_sql
📌其他场景示例：
- RAG：START → retrieve → rerank → generate → END
- 客服：START → classify → route → answer → END

【本次任务】
创建以下文件：

1. app/agent/state.py — State（TypedDict）
   🔧技术：初始只需 query 和 error 两个字段，后续章节补充

2. app/agent/context.py — Context（TypedDict，暂时 pass）

3. app/agent/nodes/ 目录下 N 个占位节点文件
   🔧技术：
   - 函数签名：async def node_name(state, runtime: Runtime[Context])
   - 节点内只做：runtime.stream_writer("进度文字") + await asyncio.sleep(0.5)
   - 📌业务：校验/判断类节点需返回 {"error": None}，让条件边正常走

4. app/agent/graph.py — 组装图
   🔧技术：
   - StateGraph(state_schema=..., context_schema=...)
   - add_node × N
   - add_edge（固定顺序）+ add_conditional_edges（条件分支）
   - compile() 得到可运行 graph
   - __main__ 测试：graph.astream(stream_mode="custom") 打印输出

【关键点】
🔧技术：
- 普通边表示固定顺序；一个节点可以有多条出边表示并行
- 条件边用 path=lambda + path_map 实现分支
- stream_mode="custom" 只接收 stream_writer 写出的自定义数据
- 占位节点不写业务逻辑，后续阶段逐个补齐

【要求】
- 异步写法
- 代码有中文注释
```

---

### 模板 007：关键词抽取与多路召回

**复用度**：⭐⭐⭐　**阶段目标**：给前几个节点填业务逻辑——关键词抽取 + LLM 扩展 + 多路检索。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14，LangGraph 编排。
已有：向量索引 + 全文索引 + Embedding 服务 + LLM。
工作流骨架已搭好。

【本次任务】
给前 N 个节点填业务逻辑：

1. app/agent/llm.py — 统一封装 LLM
   🔧技术：
   - init_chat_model(model=..., model_provider=..., base_url=..., api_key=..., temperature=0)
   - 从 app_config.llm 读取配置

2. app/prompt/prompt_loader.py — 提示词加载器
   🔧技术：load_prompt(name) 读取 prompts/{name}.prompt

3. prompts/ 目录下的扩展提示词
   📌业务：按你的召回对象各一个（如 NL2SQL 是字段/指标/取值三个，
   RAG 是文档/标签两个），要求 LLM 输出 JSON 数组

4. 修改 state.py 和 context.py
   🔧技术：加 keywords + retrieved_xxx 字段；context 加各仓储和 embedding_client

5. N 个召回节点实现
   🔧技术（通用模式）：
   - 第一个节点（如 extract_keywords）：分词工具 + 词性过滤 + 保留原始 query 兜底
   - 每个召回节点：LLM 扩展关键词 → 逐个 feature_extraction[0] → 检索 → 按 id 去重
   📌业务：
   - 向量检索的对象：语义匹配（用 Embedding）
   - 全文检索的对象：真实文本命中（直接用关键词查 ES，不需要 Embedding）

6. 各仓储加 search 方法
   🔧技术：search(embedding/keyword, score_threshold=0.6, limit=20)

7. graph.py 测试入口
   🔧技术：初始化客户端 → 创建仓储 → 传入 Context → astream 输出进度

【关键设计】
🔧技术：
- LLM 扩展关键词：用户口语和数据表达不一致，先让 LLM 补充近义表达
- 语义匹配用向量检索，真实文本命中用全文检索
- feature_extraction 返回 [[float]]，取 [0] 解包
- 多关键词命中同一对象时按 id 去重
- Embedding 逐条串行调用，避免限流

【要求】
- 异步写法
- 代码有中文注释
```

---

### 模板 008：召回信息合并与上下文构建

**复用度**：⭐⭐⭐　**阶段目标**：把多路召回的分散结果合并成下游生成能用的结构化上下文。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14，LangGraph 编排。
已完成：关键词抽取 + 多路并行召回，结果在 state 中。
现在需要实现合并节点，把分散结果合并成结构化上下文。

【本次任务】
实现合并节点和配套方法：

1. 修改 Mapper 文件：新增 to_entity()（ORM→实体反向转换）
   🔧技术：保留原有 to_model()

2. 修改目标库 Repository，新增按 id 查询方法
   🔧技术：session.get(Model, id) → to_entity
   📌业务：按需新增关联查询方法（如 NL2SQL 查主外键）

3. 修改 state.py
   📌业务：定义面向下游提示词的 State 结构（去掉内部 id 等噪音字段）
   - 嵌套结构：外层对象 → 内层字段列表（如有需要）

4. 修改 context.py：加目标库 Repository

5. 重写合并节点
   🔧技术（通用模式）：
   a. 多路结果按 id 转 Map（自然去重）
   b. 📌业务：补齐关联数据（如指标依赖的字段、A 依赖的 B，从库里按 id 查）
   c. 📌业务：把 B 类数据合并进 A 类（如取值写进字段 examples）
   d. 📌业务：按归属分组（如按表分组字段）
   e. 📌业务：兜底补齐关键关联（如主外键——下游 join 必需，召回容易漏）
   f. 组装面向提示词的 State 结构
   g. 组装关联对象 State（去内部 id）

6. graph.py 测试入口：加数据库初始化和 session 管理

【关键设计】
🔧技术：
- 主外键/关键关联必须兜底补齐——用户不会提，但下游必需
- 取值/示例写进关联对象——让模型知道真实存储值
- State 用独立 TypedDict——面向提示词，去掉内部噪音
- Mapper 双向转换——to_model 入库，to_entity 查询

【要求】
- 异步写法
- 代码有中文注释
```

---

### 模板 009：过滤与补全

**复用度**：⭐⭐⭐　**阶段目标**：生成前过滤掉不相关的上下文，补充环境信息。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14，LangGraph 编排。
已完成：多路召回 → 合并上下文。
现在需要实现生成前的过滤和补全节点。

【本次任务】

1. 复制过滤提示词到 prompts/
   📌业务：
   - NL2SQL：filter_table（选表+字段）+ filter_metric（选指标，允许空数组）
   - RAG：filter_documents（选相关文档）
   - 其他：按你的上下文类型设计过滤提示词
   🔧技术：让 LLM 只做选择题，输出 JSON，程序负责裁剪

2. 修改 state.py：加环境上下文字段
   🔧技术：DateInfoState（date/weekday/quarter）+ DBInfoState（dialect/version）
   📌业务：按需加其他环境信息（如租户、权限、时区）

3. 修改 context.py：加数据库 Repository

4. 修改数据库 Repository：加 get_db_info()
   🔧技术：select version() + session.bind.dialect.name

5. 3 个节点实现
   🔧技术：
   - filter_xxx：上下文转 YAML → LLM 选择 → 程序按结果裁剪（新建列表，不遍历删除）
   - add_extra_context：不用 LLM，程序查询/生成环境信息
   📌业务：过滤对象和环境字段按你的场景

6. graph.py 测试入口：加数据库初始化

【关键设计】
🔧技术：
- 模型只做选择题，程序负责裁剪——避免 LLM 重写复杂结构出错
- 过滤允许返回空——不是所有问题都需要所有上下文
- 不遍历删除元素——新建 filtered_list，避免索引错位
- 季度计算：(month-1)//3+1 而非 month//3+1
- YAML 转换用 allow_unicode=True + sort_keys=False

【要求】
- 异步写法
- 代码有中文注释
```

---

### 模板 010：生成与执行闭环 ⚠️ NL2SQL 专属

**复用度**：⭐　**阶段目标**：生成 → 校验 → 校正 → 执行。

> ⚠️ **换场景提示**：本模板的"生成→EXPLAIN 校验→校正→执行"是 NL2SQL 专属闭环。
> 换到其他场景（如 RAG 生成回答、客服生成回复），需要重新设计"校验"环节——
> 例如 RAG 可改为"生成→引用校验→重写"，客服可改为"生成→安全检查→发送"。
> 保留【生成→校验→条件分支→执行/修正】的框架，替换具体校验逻辑。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14，LangGraph 编排。
已完成：关键词抽取→多路召回→合并→过滤→补全上下文。
现在需要实现最后几个节点，完成从输入到输出的闭环。

【本次任务】

1. 复制生成提示词到 prompts/
   📌业务：按你的输出格式设计
   🔧技术关键约束：纯文本输出（不能带 Markdown）、结构清晰、只能用已提供的上下文

2. 修改数据库 Repository
   🔧技术：
   - validate(sql)：执行 "explain {sql}"，只关心能否解析
   - run(sql)：执行 SQL，返回 [dict(row) for row in result.mappings().fetchall()]
   📌业务：校验逻辑按你的场景（SQL 用 EXPLAIN，RAG 可用引用校验等）

3. 修改 state.py：加 output/结果字段

4. N 个节点实现
   🔧技术：
   - generate：上下文转 YAML → LLM → StrOutputParser → 写入 state
   - validate：执行校验，成功返回 {"error": None}，失败返回 {"error": str(e)}（不抛异常）
   - correct：完整上下文 + 原输出 + 错误 → LLM → 覆盖 state
   - run：执行最终输出，返回结构化结果

【关键设计】
🔧技术：
- 校验用"提前解析"思路（SQL 用 EXPLAIN），捕获具体错误
- 条件分支：error=None → 直接执行，error≠None → 校正 → 执行
- correct 传完整上下文+原输出+错误，避免修好格式改丢业务语义
- StrOutputParser（不是 JsonOutputParser），因为只需要纯文本
- run() 返回 list[dict]，前端友好

【要求】
- 异步写法
- 代码有中文注释
```

---

### 模板 011：API 接口基础与 FastAPI 入门

**复用度**：⭐⭐⭐⭐⭐　**阶段目标**：搭最小可测试的流式接口骨架（先用假数据验证协议）。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14，LangGraph 编排。
核心链路已跑通，现在需要封装成 HTTP API。

【本次任务】
搭建 FastAPI API 骨架，共 3 个文件：

1. app/api/schemas/query_schema.py — 请求体结构
   🔧技术：BaseModel，字段按你的输入设计（如 query: str）

2. app/api/routers/query_router.py — 路由
   🔧技术：
   - APIRouter()
   - fake_streamer()：异步生成器，循环 N 次 sleep 后 yield "data: step:{i}\n\n"
   - POST /api/[你的接口路径]，返回 StreamingResponse(..., media_type="text/event-stream")

3. main.py — FastAPI 应用入口
   🔧技术：
   - FastAPI(docs_url=None) 禁用默认 Swagger UI
   - 自定义 /docs 路由，用 get_swagger_ui_html 换 jsdelivr CDN（国内可达）
   - app.include_router(router)

【关键概念】
🔧技术：
- StreamingResponse：接收异步生成器，每 yield 一次向客户端写一段
- SSE 格式：data: xxx\n\n，外层 SSE 传输，内层 JSON 业务内容
- lifespan：yield 前=启动初始化，yield 后=关闭释放
- middleware：请求前后统一逻辑（如 request_id）
- Depends：依赖注入，声明需要什么，FastAPI 自动创建

【踩坑记录】
🔧技术：
- fastapi.docs 模块不存在，正确路径是 fastapi.openapi.docs
- Swagger UI 默认 CDN 国内加载不出来，换 jsdelivr

【要求】
- 异步写法
- 代码有中文注释
```

---

### 模板 012：查询接口实现与依赖组装

**复用度**：⭐⭐⭐⭐⭐　**阶段目标**：替换假流式接口，用依赖注入组装全套后端资源。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14，FastAPI + LangGraph。
核心链路已跑通，API 骨架已搭好（StreamingResponse + SSE 验证通过）。
现在需要把 fake_streamer() 替换成真实的 Service，用依赖注入组装全套资源。

【本次任务】
新建/修改 5 个文件：

1. app/api/lifespan.py — 应用生命周期管理
   🔧技术：
   - @asynccontextmanager lifespan(app)
   - yield 前：所有 client_manager.init()
   - yield 后：关闭需要关闭的客户端

2. app/api/dependencies.py — 依赖注入层
   🔧技术：
   - get_xxx_session：带 yield 的请求级 Session
   - get_xxx_repository：基于 Session 或已有客户端创建
   - get_xxx_service：组装以上全部依赖，返回 Service 实例

3. app/services/query_service.py — 核心业务层
   🔧技术：
   - __init__：接收全部依赖
   - query(input)：创建 State + Context → graph.astream(stream_mode="custom")
   - 每个 chunk 用 json.dumps 包装成 SSE：yield f"data: {json}\n\n"
   - 异常也包装成 SSE：{"type": "error", "message": str(e)}

4. 修改 main.py：FastAPI(lifespan=lifespan) + include_router

5. 修改 query_router.py：
   - 去掉 fake_streamer
   - 接收请求体 + Depends(get_service)
   - 返回 StreamingResponse(service.query(...), media_type="text/event-stream")

【关键设计】
🔧技术：
- lifespan 管应用级资源（客户端初始化/关闭），yield 依赖管请求级资源（Session）
- 依赖树自动解析：只声明 Depends(get_service)，FastAPI 从叶子递归组装
- State 放业务数据，Context 放外部工具，不混用
- 流式接口异常不能改状态码，包装成 SSE error 消息返回

【要求】
- 异步写法
- 代码有中文注释
```

---

### 模板 013：前后端联调与日志追踪

**复用度**：⭐⭐⭐⭐　**阶段目标**：统一 SSE 消息协议、处理节点异常、request_id 日志追踪。

```
【项目背景】
我在开发一个【业务类型】（【核心能力】），Python 3.14，FastAPI + LangGraph。
核心链路已跑通，API 已接入真实工作流。
现在需要做交付级收尾：统一消息协议、处理节点异常、实现日志追踪。

【本次任务】

1. 统一 SSE 消息协议（三类）：
   🔧技术：
   - progress：节点进度，{"type":"progress","step":"...","status":"running/success/error"}
   - result：最终结果，{"type":"result","data":[...]}
   - error：全局错误，{"type":"error","message":"..."}
   - 区分：progress.status=error 告诉前端哪步失败；type=error 告诉前端失败原因

2. 所有节点统一异常处理结构
   🔧技术：
   - 进入：writer({"type":"progress","step":step,"status":"running"})
   - 成功：业务逻辑 → writer(...,"success") → return state 更新
   - 失败：logger.error → writer(...,"error") → **raise**（中断图执行）
   - 关键：捕获异常后必须 raise，否则 LangGraph 会继续执行后续节点

3. 校验类节点特殊处理（不 raise）
   🔧技术：
   - 校验通过 → return {"error": None} → 条件边走正常路径
   - 校验失败 → return {"error": str(e)} → 条件边走修正路径
   - 原则：系统异常要中断，业务分支要走条件流转

4. 最终执行节点输出 result
   🔧技术：执行成功后 writer({"type":"result","data":result})

5. main.py 加 middleware 生成 request_id
   🔧技术：
   - @app.middleware("http")：uuid.uuid4() → ContextVar.set()
   - ContextVar 保存请求上下文（并发请求不互相覆盖）
   - loguru 通过 patch(inject_request_id) 自动注入到每条日志

6. Service 兜底错误
   🔧技术：
   - 流式接口已开始返回后不能改状态码
   - 异常包装成 {"type":"error","message":str(e)} 作为 SSE 返回

【关键设计】
🔧技术：
- 节点捕获异常后必须 raise，中断错误链路
- 校验类节点是唯一不 raise 的（业务分支走条件流转）
- ContextVar 类比 Java ThreadLocal，每个异步上下文各自保存 request_id
- SSE 外层传输格式 + 内层业务 JSON 协议，两层分离

【要求】
- 异步写法
- 代码有中文注释
```

---

## 五、附：电商问数原始案例参数（参考对照用）

| 参数 | 值 |
|---|---|
| 业务类型 | 电商自然语言问数系统 |
| 核心能力 | NL2SQL |
| 技术栈 | Python 3.14 + FastAPI + LangGraph |
| 数据库 | MySQL 双库：meta（元数据）+ dw（业务数仓） |
| 向量库 | Qdrant，1024 维，COSINE |
| 全文检索 | Elasticsearch + IK 中文分词 |
| Embedding | TEI + BAAI/bge-large-zh-v1.5（1024 维） |
| LLM | Anthropic 协议（MiMo mimo-v2.6-flash） |
| 业务对象 | 表 / 字段 / 指标 / 字段取值 |
| 业务示例 | "统计华北地区的销售总额" → `SELECT SUM(...) AS 销售总额 ... WHERE region_name='华北'` → 41099.5 |
| 工作流 | 12 节点：extract_keywords → 三路召回 → merge → 两路过滤 → add_extra_context → generate_sql → validate_sql → correct_sql/run_sql |
