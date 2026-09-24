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
- `EMBEDDING_ENABLED=false` 时退化为纯关键词/包含匹配。
- embedding 召回按相似度降序取 top N（默认 5）、相似度阈值默认 0.4，由 `EMBEDDING_*_SIMILARITY` / `EMBEDDING_*_TOP_COUNT` 配置。
- 注入顺序固定：自定义提示词 → 术语 → SQL 示例，各自独立成段附在 schema 信息之后。
- 术语另有一个独立用途：提取的关键词经术语同义词扩展后用于表匹配，与术语注入互不影响。

## 已知边界

- 关键词/包含匹配的命中数量没有上限，极端情况下可能注入大量内容（token 风险）；只有 embedding 召回受 top N 限制。

## 代码入口

- 命中与作用域查询：`backend/apps/terminology/curd/terminology.py`、`backend/apps/data_training/curd/data_training.py`、`sqlbot-xpack/src/sqlbot_xpack/custom_prompt/curd/custom_prompt.py`。
- 注入编排：`backend/apps/chat/task/llm.py` 的 `filter_terminology_template` / `filter_training_template` / `filter_custom_prompts`。
- `backend/apps/settings/models/setting_models.py` 的 `term_model` 是无引用的遗留代码，与术语功能无关，不要在其上扩展。
