# 向量化参数界面配置设计与影响范围

将 10 个向量召回策略参数从仅启动时配置扩展为系统管理员可在 `system/setting/parameter` 页面配置。系统级参数覆盖部署默认值，并从下一次问数或后台任务开始生效。模型及目录仍是启动配置。核心决策见 [ADR 0001](../adr/0001-runtime-embedding-configuration.md)。

正式规格已发布为 [GitHub Issue #1403](https://github.com/dataease/SQLBot/issues/1403)，包含完整用户故事、实现决策和已确认的测试边界；本文保留源码影响索引。

本文已随 #1403 实现更新；下列源码链接是运行时行为的维护入口，验收条件仍用于区分实现与验证范围。持久化使用已发布 xpack wheel，未修改闭源源码。术语沿用根目录 [CONTEXT.md](../../CONTEXT.md)。

## 参数范围

启动默认值定义位于 [config.py](../../backend/common/core/config.py) 的 `Settings`，持久化键与不可变配置模型见 [embedding_config.py](../../backend/common/core/embedding_config.py)。

| 启动配置名 | 代码默认值 | 页面含义与实际影响 |
| --- | --- | --- |
| `EMBEDDING_ENABLED` | `true` | 知识向量化：共同控制术语与 SQL 示例的向量生成、补齐和召回，不是全系统总开关 |
| `EMBEDDING_TERMINOLOGY_SIMILARITY` | `0.4` | 术语向量召回相似度阈值，现状为严格大于阈值 |
| `EMBEDDING_TERMINOLOGY_TOP_COUNT` | `5` | 每个关键词的术语向量候选数量；多个关键词和字面匹配合并后可超出该数量 |
| `EMBEDDING_DATA_TRAINING_SIMILARITY` | `0.4` | SQL 示例向量召回相似度阈值，现状为严格大于阈值 |
| `EMBEDDING_DATA_TRAINING_TOP_COUNT` | `5` | SQL 示例向量候选数量；合并字面匹配后可超出该数量 |
| `TABLE_EMBEDDING_ENABLED` | `true` | 共同控制表与数据源向量生成、补齐和预筛选 |
| `TABLE_EMBEDDING_COUNT` | `10` | 表召回候选数量；明确提及的表、关系补全表可以超出该数量 |
| `TABLE_EMBEDDING_ALPHA` | `0.4` | 表混合匹配的向量权重，关键词权重为 `1 - alpha` |
| `TABLE_EMBEDDING_KEYWORD_ENABLED` | `true` | 关键词提取、术语同义词扩展与表混合匹配；独立于表向量开关，也影响术语匹配输入 |
| `DS_EMBEDDING_COUNT` | `10` | 自动选择数据源之前的向量预筛选候选数量 |

以下配置不增加页面控件：

- `DEFAULT_EMBEDDING_MODEL`、`LOCAL_MODEL_PATH`：保留部署配置。现有模型名称仅用于缓存默认 key，实际加载目录仍硬编码模型子目录，不具备通用模型切换能力。
- `EMBEDDING_DEFAULT_SIMILARITY`、`EMBEDDING_DEFAULT_TOP_COUNT`：仅在 `Settings` 类定义时提供具体字段的初始默认值，业务没有独立消费者。现有环境变量修改这两个字段并不会自动更新具体字段，不引入新的公共默认值继承。
- `SAMPLE_DATA_ENABLED`：属于表样例数据控制，本次不迁移。

## 已实现行为

系统管理员统一配置，所有工作空间共享。适用于页面、MCP、普通小助手、页面嵌入助手及高级应用各自已经使用这些参数的功能，不扩大高级应用的表或数据源筛选能力。

有效值优先级为已保存的页面值、启动配置、代码默认值。页面读取后端计算出的有效值，避免前端硬编码默认值覆盖既有部署配置。保存后，后续环境变量变化不覆盖该持久化值。

每次问数或后台任务在开始时读取一份一致的配置，执行中不切换规则。保存成功后的新任务无需重启即可使用新值，各服务进程必须一致。已开始的向量生成任务允许完成。

关闭知识或表向量开关后，不再开始对应向量生成或召回；修改内容时使受影响的旧向量失效。重新开启后异步补齐缺失或失效向量，保留仍有效的向量。旧任务不得将过期内容的向量写回；内容变更和向量写回之间必须有一致性保护。

补齐中或向量生成失败时，术语和 SQL 示例继续字面匹配，并使用已有有效向量补充召回。当前候选表或数据源存在缺失、失效向量时，跳过该层向量预筛选，交由后续流程处理原本可访问的候选集合；模型调用失败也应保留可用的降级路径。该行为可能增加上下文和耗时，不保证外部模型能够处理无限大的候选集合。

保留现有语义：知识向量召回与字面匹配取并集；表和数据源共享开关；关键词开关独立；历史记录保存的关键词仍可供后续分析使用。页面按知识召回、表与数据源筛选分组，不能因关闭表向量开关而把仍生效的关键词开关隐藏或视为无效。

页面与后端均校验：相似度和权重是 `[0,1]` 内的有限数值，候选数量是正整数，不新增任意数量上限。非法输入整次拒绝保存，不静默截断、替换默认值或部分写入。该规则针对新页面保存，不顺带重定义既有启动配置解析行为。

## 参数配置调用链

| 环节 | 源码入口 | 现状与改动关注点 |
| --- | --- | --- |
| 路由与页面 | [router/index.ts](../../frontend/src/router/index.ts)；[parameter/index.vue](../../frontend/src/views/system/parameter/index.vue) | `setting/parameter`；现有 `chat.limit_rows` 为参考。旧 `chat/login/platform` 控件保留；十个 `embedding.*` 字段按明确键与类型独立绑定、保存和回显 |
| 值解析 | [utils.ts](../../frontend/src/utils/utils.ts) 的 `formatArg` | 旧配置沿用 `formatArg`；新字段按布尔、数量和小数解析，避免把 `0/1` 混成布尔值 |
| 参数 API | [parameter.py](../../backend/apps/system/api/parameter.py) 的 `get_args/save_args` | GET/POST `/system/parameter` 要求系统管理员权限；保存有参数设置审计 |
| 持久化适配 | [parameter_manage.py](../../backend/apps/system/crud/parameter_manage.py) | 保存委托已发布 xpack 的 `save_group_args`；写入前整批校验并串行化参数写事务；有效向量配置直接读取 `sys_arg`，不依赖适配器缓存 |
| 存储结构 | [035_sys_arg_ddl.py](../../backend/alembic/versions/035_sys_arg_ddl.py) | `sys_arg` 使用 `pkey/pval`，没有工作空间维度；不因本次配置迁移引入工作空间覆盖 |
| 任务读取 | [llm.py](../../backend/apps/chat/task/llm.py) 的 `LLMService.create` | 构造任务时加载不可变 `EmbeddingConfig`；旧 `chat.*` 参数仍在 `create` 中加载，不修改全局 `settings` |

已用发布 wheel 验证未知 `embedding.*` 键的保存与读取。运行时读取不依赖适配器的缓存失效：每次任务以单条数据库查询取得全部覆盖值。历史迁移缺少 `pkey` 唯一约束，参数写事务使用 advisory lock 串行化；历史重复键按最大 ID 确定有效值，保存可更新该值。本次不新增迁移或修改 wheel。

## 向量生成与数据变更链

| 功能 | 源码入口与函数 | 影响 |
| --- | --- | --- |
| 模型加载 | [ai_model/embedding.py](../../backend/apps/ai_model/embedding.py) 的 `local_embedding_model`、`EmbeddingModelCache` | 模型路径及默认参数在导入时确定，模型对象为进程内缓存；本次不切模型 |
| 启动补齐 | [main.py](../../backend/main.py) 的 `lifespan`、三个 `init_*embedding*` 函数 | 迁移和缓存初始化后提交补齐；各进程均可恢复待补齐任务，工作线程读取有效开关 |
| 后台任务提交 | [embedding_threads.py](../../backend/common/utils/embedding_threads.py) 的全部 `run_save_*`、`fill_empty_*` | 术语、SQL 示例、表、数据源共用线程池和独立 session；任务执行时取得配置，不能遗漏这一读取路径 |
| 启动任务互斥 | [distributed_lock.py](../../backend/common/utils/distributed_lock.py) 的 `SingleWorkerGuard` | 旧启动锁不再承担向量补齐去重；`embedding_lifecycle.py` 按资源事务锁、锁后重读和条件发布协调各进程 |
| 术语新增、编辑、导入 | [terminology.py](../../backend/apps/terminology/curd/terminology.py) 的 `create_terminology/update_terminology/batch_create_terminology` | 提交父术语 id，生成覆盖主词和同义词；输入改变与向量失效在同一业务事务内 |
| 术语生成与补齐 | 同文件 `save_embeddings/run_fill_empty_embeddings` | 任务开始读取知识开关；业务修改先将过期向量清空，补齐只生成空向量并保留有效值 |
| SQL 示例新增、编辑、导入 | [data_training.py](../../backend/apps/data_training/curd/data_training.py) 的 `create_training/update_training/batch_create_training` | 向量输入为示例问题；问题变更时原子清空旧向量 |
| SQL 示例生成与补齐 | 同文件 `save_embeddings/run_fill_empty_embeddings` | 任务开始读取知识开关，补齐空向量；按问题输入条件写回 |
| 数据源创建、选择表与同步 | [datasource.py](../../backend/apps/datasource/crud/datasource.py) 的 `create_ds/chooseTables/sync_table/sync_single_fields` | 创建及选择表进入同步链；同步更新表和所属数据源向量 |
| 数据源与元数据编辑 | 同文件 `update_ds/update_table_and_fields/updateTable/updateField` | 名称、描述、表和字段内容影响表或数据源向量；失效必须沿依赖传播 |
| 表与数据源生成和补齐 | [table.py](../../backend/apps/datasource/crud/table.py) 的 `save_table_embedding/save_ds_embedding/run_fill_empty_table_and_ds_embedding` | 共用表向量开关；数据源向量包含名称、描述及表字段结构；扫描空值和无效 JSON 向量，保留有效向量；发布前重读完整输入 |
| 向量存储 | [terminology_model.py](../../backend/apps/terminology/models/terminology_model.py)、[data_training_model.py](../../backend/apps/data_training/models/data_training_model.py)、[datasource/models/datasource.py](../../backend/apps/datasource/models/datasource.py) | 术语和 SQL 示例使用 pgvector；表和数据源使用 Text JSON，失效/补齐需覆盖两种表示 |

## 问数及其他消费链

| 功能 | 源码入口与函数 | 影响与边界 |
| --- | --- | --- |
| 术语召回 | [terminology.py](../../backend/apps/terminology/curd/terminology.py) 的 `select_terminology_by_word/get_terminology_template` | 工作空间、数据源、高级应用三条向量 SQL；与字面匹配合并，按关键词逐次召回 |
| SQL 示例召回 | [data_training.py](../../backend/apps/data_training/curd/data_training.py) 的 `select_training_by_question/get_training_template` | 数据源和高级应用两条向量 SQL；与双向包含匹配合并 |
| SQL 上下文注入 | [llm.py](../../backend/apps/chat/task/llm.py) 的 `filter_terminology_template/filter_training_template/init_messages` | 自动选数据源和已指定数据源两条问数路径都需传递同一配置快照；保持知识作用域隔离 |
| 自动选择数据源 | 同文件 `select_datasource`；[ds_embedding.py](../../backend/apps/datasource/embedding/ds_embedding.py) 的 `get_ds_embedding` | 多数据源时先截断向量候选，再交 LLM 选择；表开关还影响选择结果持久化分支，不可遗漏 |
| 表结构筛选 | `llm.py` 的 `choose_table_schema`；[datasource.py](../../backend/apps/datasource/crud/datasource.py) 的 `get_table_schema/get_table_obj_by_ds` | 使用已有权限及选中状态约束后的候选；开关关闭保留该候选集合；配置不能绕过权限过滤 |
| 表混合匹配 | [table_embedding.py](../../backend/apps/datasource/embedding/table_embedding.py) 的 `calc_table_embedding/_calc_vector_only/_select_tables` | 关键词与向量按 alpha 融合，保留问题明确提到的表，再按数量补充；异常或不完整向量的降级不能任意丢表 |
| 关系与样例数据 | `datasource.py` 的 `get_table_schema/get_tables_sample_data`；`llm.py` 的 `choose_table_schema` | 筛选后仅从原授权表和字段补充关系上下文，明确表与关系表可超出候选数；样例数据使用最终选表 |
| 关键词提取和同义词扩展 | `llm.py` 的 `extract_keywords` 及两条问数入口；`terminology.py` 的 `expand_with_terminology` | 关键词开关控制额外 LLM 调用、术语匹配输入及扩展结果保存，即使表向量关闭仍可生效 |
| 分析 | `llm.py` 的 `generate_analysis` | 使用记录已保存的关键词并重新检索术语，后续新发起分析受新知识召回参数影响 |
| 预测 | 同文件 `generate_predict` | 当前不重新筛选术语，不能声称直接采用新术语阈值；可间接使用之前形成的上下文 |
| 推荐问题 | 同文件推荐问题生成链 | 独立获取 schema 时显式 `embedding=False`；问数链内可能复用此前已筛选 schema |
| 已选表上下文重建 | 同文件 `run_task` 中生成图表前调用 `get_table_schema` 的路径 | 显式 `embedding=False`，不对已确定的表再次筛选 |
| 页面、普通及嵌入助手 | [chat/api/chat.py](../../backend/apps/chat/api/chat.py) 的 `question_answer_inner` 等任务创建入口 | 进入共同 `LLMService` 流程；各任务都需取得有效配置 |
| MCP | [mcp.py](../../backend/apps/mcp/mcp.py) 的问数入口 | 也调用 `question_answer_inner`；现有 `embedding` 入参没有被 `LLMService` 消费，不能据此判断 MCP 不使用向量功能 |
| 高级应用 | [assistant.py](../../backend/apps/system/crud/assistant.py) 的 `AssistantOutDs.get_db_schema`；`llm.py` 的助手分支 | 术语与 SQL 示例仍按高级应用作用域召回；表向量调用被注释，数据源向量预筛选被当前调用方排除，本次不新增 |

`table_embedding.py` 的旧 `get_table_embedding` 仍读取表数量，但当前没有活动调用。`ds_embedding.py` 内虽保留高级应用动态向量分支，当前唯一调用方却排除了该类助手。维护时应区分活动链路与这些遗留分支，不把后者描述为已有产品能力。

## 实现约束与验收条件

五条术语和 SQL 示例向量 SQL 已改为执行时参数绑定阈值和数量。统一不可变 `EmbeddingConfig` 及持久化读取负责优先级，问数快照和后台任务共用该入口。知识生成使用资源事务锁与输入条件写回；表和数据源发布前按父数据源、子表顺序锁行、重读并比较完整输入。失败有限重试后保持未完成状态，后续任务或进程启动可恢复。

| 验收场景 | 可观察结果 |
| --- | --- |
| 首次打开与已有部署配置 | 10 个参数显示后端有效值；未保存值沿用启动配置，刷新不改变 |
| 保存与再次打开 | 布尔、整数、小数正确回显；持久化值优先于启动配置；其他已有参数保留 |
| 非法输入 | 越界、非有限小数、非整数或非正数量被前后端拒绝；整次保存无部分更新 |
| 权限 | 系统管理员可以读取和保存；非管理员拒绝保存且无持久化变化 |
| 热更新与任务一致性 | 保存后所有 worker 与 MCP 新任务使用新值；在途任务继续使用原配置 |
| 知识召回 | 关闭后保留字面匹配；阈值和数量在新查询生效；覆盖术语三个作用域和 SQL 示例两个作用域 |
| 表与数据源筛选 | 数量、alpha、关键词开关在新任务生效；明确表和关系补全保留；权限边界不扩大 |
| 关闭期间新增及修改 | 不启动对应向量生成；新增向量为空，修改过的旧向量不可继续视为有效 |
| 重新开启与重启 | 自动补齐缺失/失效向量；并发保存、多个进程与重启不导致漏补或重复失控 |
| 内容修改与旧任务完成竞态 | 旧内容的生成结果不会覆盖新内容的失效状态或新向量 |
| 补齐中与失败 | 知识匹配仍可用；表/数据源向量不完整时不因预筛选漏候选；失败不伪报完成 |
| 不同入口与后续任务 | 覆盖页面、MCP、普通/嵌入助手、高级应用知识作用域及分析重新检索；未使用向量的路径保持边界 |
| 页面说明 | 两组参数、开关关系和候选数量含义准确；关键词开关保持独立可理解 |

[test_table_embedding.py](../../backend/tests/test_table_embedding.py) 覆盖表匹配逻辑；参数与生命周期测试进一步覆盖配置解析、持久化覆盖、任务快照、失效与补齐和并发写回。真实 API/数据库、独立 MCP 传输和页面保存回显分别记录证据；构建和源码守卫不能替代这些验证。

规格确认采用两个既有业务测试边界：参数管理的真实读取/保存接口，以及问数、分析和资源变更的任务入口。前者观察权限、有效值和持久化结果，后者观察候选、模型上下文和向量结果；使用可控模型提供者复现边界与并发，并另行以真实数据库、多进程和浏览器验证集成行为。

## 验证入口与限制

从 `backend/` 执行默认离线回归；集成测试必须显式选择授权的可销毁 PostgreSQL/pgvector 数据库，每个用例创建并清理独立 schema：

```bash
uv run --no-sync pytest -q
SQLBOT_RUN_EMBEDDING_INTEGRATION=1 SQLBOT_TEST_DATABASE_URL="$DISPOSABLE_DATABASE_URL" \
  uv run --no-sync pytest -q tests/test_embedding_parameters_integration.py \
  tests/test_knowledge_lifecycle_integration.py tests/test_table_parameters_integration.py \
  tests/test_datasource_lifecycle_integration.py tests/test_mcp_parameters_integration.py
```

前端类型与打包在 `frontend/` 执行 `npm run build`。使用已准备环境时保留 `--no-sync`；未入库 lockfile，源码 SHA 本身不能冻结依赖。验证采用发布 wheel `sqlbot-xpack==0.0.5.36`、PostgreSQL 17/pgvector 和受控模型提供者；未调用外部 LLM，未验证模型语义质量、真实外部数据源、生产多机部署或镜像安装。参数快照、资源并发和锁释放由真实 PostgreSQL、多进程测试验证，不能用直接构造 `LLMService` 的用例代替 MCP 网络入口验收。

MCP 集成用例通过独立 Uvicorn `main:mcp_app` 的 SSE 传输调用 `mcp_start/mcp_question`，另一个 API 进程保存参数；仅控制模型和外部数据源提供者。fixture 建立 schema，因此 API 进程不运行迁移 lifespan；MCP 进程保留正常 lifespan。该用例不覆盖完整部署启动或图表图片服务。浏览器逐控件保存与刷新结果单独记录，不以构建或 API 测试代替。
