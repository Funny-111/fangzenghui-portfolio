# PRD↔代码差距对照清单（prd-gap.md）

> **依据**：PRD「上线计划 · 上线准备清单 · 合同符合性」——五列结构：PRD 条目 ｜ 代码现状 ｜ 差距 ｜ 处置（修复/接受/挂账）｜ 计划时点。
> **准入规则**：本清单**零差距，或差距项经 PM + 研发评审签字接受并挂账**，才进放量流程（内测开始前核对）。
> **更新规则**：每次 PRD 修订或实现变更后同步更新；「修复」项完成后移入已修复表并注明日期与验证方式。
> **收录边界**：分期项（附件完整解析、知识库完整形态等）另见 PRD「后续迭代计划」，本清单不重复记账；本清单只收行为合同与接口层的实现差距。
> **编号约定**：条目编号 gap-NN 与 PRD 正文标注一一对应，PRD 侧搜索 `gap-NN` 可直达本行。
> **维护人**：PM（c君） · 建立日期：2026-11-09 · 最近更新：2026-11-10（v5，补收 7 条漏收项）

## 一、待处置差距

| PRD 条目 | 代码现状 | 差距 | 处置 | 计划时点 |
|---|---|---|---|---|
| 【gap-01】五类输出契约一律 JSON（计划 / 子结论 / 充分性 / 报告 / 澄清） | `app/prompt/prompts.yml` 为自由文本输出，无 schema 校验；主提示词仅要求「生成 todo-list」，未定义执行计划结构 | 行为合同未落地：前端与评测机无法按合同消费 | 修复 | 内测开始前（合同符合性） |
| 【gap-02】传输层消息类型至少覆盖：计划下发、澄清追问、报告就绪（含文件列表与置信度档位） | `monitor.py` 仅 6 类事件（session_created / tool_start / assistant_call / task_result / task_cancelled / error），无 plan、clarify、report_ready，confidence 不下发 | PRD 承诺的四类消息前端收不到 | 修复（随五类契约改造一并落地） | 内测开始前 |
| 【gap-03】断连补推：事件流带会话内序号 + 服务端按会话缓存 + 重连按序续传 + 心跳超时判定 | 仅 ping/pong 心跳应答与重连防误删（`disconnect` 的 stale 判断），无事件序号、无服务端缓存、无超时判定 | 断连重连后进度丢失，与 PRD 承诺不符 | 修复 | 内测开始前 |
| 【gap-04】文件读侧会话隔离：会话凭证与目标文件所属会话一致，A 会话不可读 B 会话产物 | 仅路径穿越防护（`resolve` + `is_relative_to`），无登录态、无会话归属校验 | 越权读其他会话产物的风险敞口 | 修复（随鉴权就绪一并落地） | 内测开始前 |
| 【gap-05】账号密码登录与三角色鉴权（用户 / PM / 研发） | 无任何鉴权；CORS `allow_origins=["*"]` 且 `allow_credentials=True` | 未授权可访问全部接口 | 修复 | 内测开始前 |
| 【gap-06】错误码契约 `{code, message}` 全接口覆盖 | 文件三接口（upload / files / download）已落地；任务接口（`/api/task`、cancel）仍为 `HTTPException` 的 `detail` 裸文本，`TASK_NOT_FOUND` 未使用 | 契约覆盖不全，前端任务类错误无法按 code 分支 | 修复 | 内测开始前 |
| 【gap-07】运行时限值：补搜 ≤3 轮、单路失败重试 1 次、LLM 输出解析重试 1 次、token 300k 熔断、墙钟 300s、澄清挂起 30 分钟 | 代码内无任何轮次/重试/预算计数与熔断；子智能体调用无超时、无重派；`run_deep_agent` 只有 `asyncio.CancelledError` 与兜底 `error` 事件 | PRD 六-1「失败出口与任务预算上限」整表无实现，异常流程的重试/超时兜底不可验收 | 修复（先在主循环加计数与熔断，再接事件流） | 内测开始前 |
| 【gap-08】高危机读：只允许 SELECT、只允许查白名单内 3 张表、越权拦截记审计日志 | `db_tools.execute_sql_query` 原样 `cursor.execute(query)`，连接 `autocommit=True`；注释自认「依赖提示词约束，生产环境应限制 SELECT/SHOW」；无表名白名单、无审计日志、无拦截计数 | 非 SELECT 语句会真实落库；「SELECT 守卫直接拦截」为 PRD 承诺的运行时行为，代码零实现 | 修复（P0，安全红线） | 内测开始前 |
| 【gap-09】数据合规：隐私字段按句拦截 + 检索词出网前去标识化过滤（专名/敏感实体词表） | 报告链路无隐私字段检测与打码；`tavily_tool` 将 query 原样发给 Tavily，无词表、无改写、无审计 | 两条均为 PRD 写死的运行时规则（含「按句拦截并标注已过滤」的具体交互），代码零实现；库内 `sales_records.customer_name`（医院/药房）与 `sales_rep`（人名）就是现实触发面 | 修复（P0，安全红线：隐私拦截先做字段级黑名单，词表迭代入二期） | 内测开始前 |
| 【gap-10】附件解析允许（系统层），不经模型工具链 | `read_file_content` 挂在主智能体 `tools` 上，由模型自行决定何时读、读哪个文件；解析依赖 python-docx / pypdf / pandas 按需导入 | 实现走模型工具链，与合同「系统层、不经模型工具链」不符；附件到底读没读到无法由系统保证 | 修复（改为任务启动时系统预解析并注入上下文）或挂账 | 内测开始前 |
| 【gap-11】`get_assistant_list / create_ask_delete` 工具语义待核实（PRD 原文即标注入清单） | `create_ask_delete` 每次调用 create_session → completions → delete_sessions；异常分支下不删会话；`chats[0]` 未判空 | 临时会话可能泄漏；重名助手取第一个命中，语义未经核实 | 修复（判空 + finally 删会话） | 内测开始前 |
| 【gap-12】`generate_markdown / convert_md_to_pdf` 合同归系统渲染，实现挂主智能体工具 | 两工具在 `main_agent.tools` 中，由模型调用；`word_converter.py` 存在但未挂载（主提示词却写「可生成 Markdown、Word、PDF 三种」） | 合同归属与实现位置不一致；提示词承诺 Word 能力但无对应工具 | 修复（提示词删 Word 表述；工具归属按合同收口） | 内测开始前 |
| 【gap-13】及格线「运行时探测」：每份报告交付后编造初筛 judge + 谎报日终批跑 | 无编造初筛调用、无日终批跑任务、无自动隔离（报告标「待核查、暂勿引用」/暂停提交） | 一票否决项的**运行时**触发链路缺失，只剩离线验收 | 修复（随 gap-01 的 JSON 报告落地后接入） | 内测开始前 |
| 【gap-14】越权工具调用按角色拦截并计数（一票否决「白名单外工具调用次数 =0」的测量方式） | 角色隔离靠 DeepAgents 子智能体各自的 `tools` 列表结构性保证；无运行时拦截层、无拦截日志、无计数接口 | 结构性隔离可用，但一票否决项缺少可断言的计数来源 | 修复（补拦截日志 + 计数接口） | 内测开始前 |
| 【gap-15】附件正面清单：docx / pdf / md / txt（能力边界 · 附件上传） | 上传入口已按白名单拦截；读取工具 `upload_file_read_tool` 另支持 xlsx / xls（超集） | 入口与工具口径不一致，但入口为准后 xlsx 实际进不来，工具侧为无害超集 | 接受 | —（口径以 PRD 白名单为准，工具超集不外显） |

**挂账签字栏**（处置为「挂账」的条目须签字方可进放量；上表当前无挂账项）：

| 条目 | PM 签字 | 研发签字 | 日期 |
|---|---|---|---|
| — | — | — | — |

## 二、本期已修复（闭环证据）

| PRD 条目 | 代码现状 | 差距 | 处置 | 计划时点 |
|---|---|---|---|---|
| 附件入口即时校验：格式白名单 + 单文件 ≤20MB，不符立即拒绝不落盘 | `app/api/server.py` 上传接口已实现：扩展名整批校验、边写边计数超限中断并回滚 | 无（原为校验缺失，落盘后才暴露） | 修复 | 已完成 2026-11-09；验证：TestClient 冒烟 11/11 通过（含超限不落盘、混传整批拒绝） |
| 会话 id 字符白名单校验，杜绝路径拼接穿越 | `/api/upload` 与 `/api/task` 双入口校验 `^[A-Za-z0-9_-]{1,64}$` | 无（原为 thread_id 直接拼路径） | 修复 | 已完成 2026-11-09；验证：`../escape` 双接口均返回 400 `INVALID_THREAD_ID` |
| 文件接口错误码契约 `{code, message}` | upload / files / download 三接口返回 HTTP 4xx + `{code, message}`；前端 `requestJson` 优先读 message | 无（原为 200 + 裸 `{"error"}`） | 修复 | 已完成 2026-11-09；验证：`FILE_TYPE_NOT_ALLOWED` / `FILE_TOO_LARGE` / `FILE_NOT_FOUND` / `PATH_ACCESS_DENIED` 断言通过 |

## 三、已对齐（非代码缺陷，PRD 侧口径修正）

| 项 | 原 PRD 口径 | 代码事实 | 处置 |
|---|---|---|---|
| 企业数据库 | dw 库 5 张电商表（dim_customer / dim_date / dim_product / dim_region / fact_order，115 行订单）「本期已接入，双路混合测试通过」 | `deepsearch_db` 3 张表：drugs（50）/ inventory（150）/ sales_records（100），药品域；区域为华东/华北/华南/华中/西南/西北/东北七档 | 已改 PRD 七.1 与评测集示例（2026-11-10，v5）；若后续切电商 dw 库，须同步回改本行并重标 L1 用例 |
| 知识库实现形态 | 「Dify 知识库实现」 | RAGFlow（`app/tools/ragflow_tools.py`，SDK 直连） | 已改 PRD 七.1（v5） |
| 基础设施 | 「内测期：Dify 自部署」 | FastAPI + uvicorn（`app/api/server.py`） | 已改 PRD 八.非 API 成本（v5） |
| 模型选型依据 | 「代码实现同款，迁移成本为零」 | `.env` 跑 qwen-max（DashScope OpenAI 兼容端点），从未在 DeepSeek-V4.1-Flash 上跑过 | 已改 PRD 八.选型依据①（v5） |
