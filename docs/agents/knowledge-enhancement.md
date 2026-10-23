# 知识增强

术语、SQL 示例和自定义提示词在问数流程中按作用域注入模型上下文。概念定义见根目录 `CONTEXT.md`；本文记录作用域、命中和组合的行为规则，修改相关知识逻辑前先对照本文确认预期行为。

## 作用域规则

三类知识的作用域维度不完全一致：

| 维度 | 术语 | SQL 示例 | 自定义提示词 |
|---|---|---|---|
| 工作空间级（全局） | 支持 | 不支持 | 支持 |
| 数据源级 | 支持多选 | 仅单选 | 支持多选 |
| 高级应用级 | 支持 | 支持 | 支持 |
| 任务环节分类 | 无 | 无 | 生成 SQL / 分析 / 预测 |

- SQL 示例必须绑定一个数据源或一个高级应用，没有工作空间级示例；两者都为空时不注入任何示例。
- 数据源场景取并集：工作空间级知识 + 绑定当前数据源的知识。
- 高级应用场景取替换：只注入绑定该高级应用的知识，工作空间级知识不生效。这是有意设计，不是缺陷。
- 作用域的工作空间解析：普通小助手按助手所属工作空间；页面嵌入助手按当前用户的工作空间；高级应用按助手所属工作空间并使用应用绑定。

## 命中与组合规则

- 组合语义是“命中即注入”：命中多少条注入多少条，不做全局排序或择优。
- 术语：优先用 LLM 提取的关键词匹配（无关键词时用原始问题），按逗号拆分逐词匹配；同义词命中归并到主词条目。
- SQL 示例：用完整问题做双向包含匹配（问题包含示例问题，或示例问题包含问题）。
- 自定义提示词：不做问题匹配，作用域内全部注入。
- 关键词/包含匹配与 embedding 召回是并集关系，不是优先级关系：embedding 只是补充召回渠道，不淘汰关键词命中的结果。
- 有效知识向量开关 `embedding.enabled=false` 时退化为纯关键词/包含匹配；它不控制表与数据源向量。
- embedding 召回按相似度降序取 top N（代码默认 5），相似度严格大于阈值（代码默认 0.4）。术语和 SQL 示例分别使用 `embedding.terminology_*` / `embedding.data_training_*` 的有效参数；多关键词和字面匹配合并后可超过 top N。
- 注入顺序固定：自定义提示词 → 术语 → SQL 示例，各自独立成段附在 schema 信息之后。
- 术语另有一个独立用途：提取的关键词经术语同义词扩展后用于表匹配，与术语注入互不影响。

## 运行时配置与向量生命周期

系统管理员在参数配置页保存系统级 `embedding.*` 参数；有效值按“持久化值 > 对应启动配置 > 代码默认值”解析。未保存的参数沿用 `EMBEDDING_*` / `TABLE_EMBEDDING_*` / `DS_EMBEDDING_COUNT` 部署值；保存后仅改变环境变量不会覆盖持久化值。页面 GET 显示同一有效值，保存前整批校验类型和范围。定义与读取入口为 `common/core/embedding_config.py`，不修改全局 `settings` 或依赖进程内参数缓存。

`LLMService` 创建任务时读取不可变快照，后续知识召回、数据源和表筛选共用该快照；新发起分析重新读取配置并保留记录中的历史关键词。后台向量任务在实际工作线程开始时读取配置，排队时间不算任务开始。保存后的新任务读取数据库提交，已开始任务可按原快照完成。

关闭期间不开始对应向量生成，但业务事务仍使输入变化的向量失效；重新开启和进程启动异步补齐，保留有效向量。术语主词/同义词、SQL 示例问题改变时清空对应向量；表字段变化沿表和父数据源传播失效。资源任务通过 PostgreSQL advisory lock 去重、锁后重读并按输入条件发布，防止旧结果覆盖已编辑或删除资源。失败有限重试后保持待补齐并报告异常，后续资源任务、重新开启或启动可重试。入口见 `common/utils/embedding_lifecycle.py`、`common/utils/embedding_threads.py` 和 `apps/datasource/crud/embedding_state.py`。

表与数据源使用独立的 `embedding.table_enabled` 开关；候选向量不完整或评分失败时，跳过该层向量预筛选，保留原本可访问候选。关键词提取与同义词扩展开关 `embedding.keyword_enabled` 独立于两个向量开关。完整参数与边界见 [设计与验证说明](../design/embedding-parameter-configuration.md)。

## 已知边界

- 关键词/包含匹配的命中数量没有上限，极端情况下可能注入大量内容（token 风险）；只有 embedding 召回受 top N 限制。

## 代码入口

- 命中与作用域查询：`backend/apps/terminology/curd/terminology.py`、`backend/apps/data_training/curd/data_training.py`、`sqlbot-xpack/src/sqlbot_xpack/custom_prompt/curd/custom_prompt.py`。
- 注入编排：`backend/apps/chat/task/llm.py` 的 `filter_terminology_template` / `filter_training_template` / `filter_custom_prompts`。
- `backend/apps/settings/models/setting_models.py` 的 `term_model` 是无引用的遗留代码，与术语功能无关，不要在其上扩展。
