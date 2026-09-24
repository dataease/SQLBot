# SQLBot

SQLBot 让业务用户用自然语言提问，基于已配置的数据源生成并安全执行 SQL，然后返回数据、图表、分析和后续问题建议。

## Language

### 工作空间与数据

**Workspace / 工作空间**:
用户、会话、数据源、模型等 SQLBot 资源的隔离边界。
_Avoid_: Organization、tenant

**Workspace ID / 工作空间 ID**:
工作空间的标识。历史上的 `oid` 和 `workspace_id` 字段表示同一个概念。
_Avoid_: 把 `oid` 理解成独立的组织概念

**Datasource / 数据源**:
已配置的外部数据源，以及 SQLBot 用于生成查询的表、字段、关系和 embedding 等元数据。
_Avoid_: Database、connection

**SQL Example / SQL 示例**:
用于引导 SQL 生成的“问题 + SQL”示例。
_Avoid_: Data training、training data

**Terminology / 术语**:
业务词或短语的解释，可包含同义词，用于提升问题和表结构理解。
_Avoid_: Custom prompt、SQL example

**Custom Prompt / 自定义提示词**:
附加在模型任务上的场景指令，可按工作空间、数据源或助手场景生效。
_Avoid_: Terminology、SQL example

### 会话

**Chat / 会话**:
用户在一个工作空间内连续提出数据问题的对话。
_Avoid_: Assistant、dashboard

**Chat Record / 会话记录**:
一次问题执行的可持久化结果，包含问题、生成 SQL、查询结果、图表配置、错误以及关联的后续记录。
_Avoid_: Chat

**Analysis / 分析**:
基于既有问题结果的模型生成解读。
_Avoid_: Prediction

**Prediction / 预测**:
基于既有问题结果的模型生成前瞻性估计。
_Avoid_: Analysis

**Recommended Problem / 推荐问题**:
与数据源关联的已配置问题。
_Avoid_: Guess question

**Guess Question / 猜测问题**:
由模型根据会话上下文推测的后续问题。
_Avoid_: Recommended problem

### 助手与集成

**Assistant / 助手**:
把 SQLBot 问数能力暴露给外部系统的集成配置。
_Avoid_: Chat

**Ordinary Assistant / 普通小助手**:
标准的小助手集成形态。
_Avoid_: Advanced assistant、page-embedded assistant

**Advanced Assistant / 高级应用**:
面向更深集成场景的高级小助手形态。
_Avoid_: Ordinary assistant、page-embedded assistant

**Page-embedded Assistant / 页面嵌入助手**:
用于把 SQLBot 页面嵌入目标系统的小助手形态。
_Avoid_: Ordinary assistant、advanced assistant

**Assistant Domain / 助手目标域名**:
小助手对接的外部目标系统域名。
_Avoid_: Business domain、workspace

**Dashboard / 仪表板**:
为重复分析保存的数据视图集合。
_Avoid_: Chat、chat record
