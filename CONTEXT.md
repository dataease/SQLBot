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

**System Admin / 系统管理员**:
内置的系统级管理员账号，拥有全部管理能力，不属于工作空间角色体系。
_Avoid_: Workspace Admin

**Workspace Admin / 工作空间管理员**:
工作空间内拥有管理能力的成员角色，由成员权重非零标识。
_Avoid_: System Admin

**Datasource / 数据源**:
已配置的外部数据源，以及 SQLBot 用于生成查询的表、字段、关系和 embedding 等元数据。
_Avoid_: Database、connection

**Excel Datasource / Excel 数据源**:
上传的 Excel/CSV 物化到内置库后按 PostgreSQL 处理的导入型数据源。
_Avoid_: 外部连接型数据源、内存数据源

**Dynamic Datasource / 动态数据源**:
高级应用每次会话从宿主 API 实时拉取的数据源，不落库。
_Avoid_: 内置数据源、普通数据源

**Table Relation / 表关系**:
人工在关系图上维护的表关联，为多表查询提供 JOIN 上下文。
_Avoid_: 外键约束（数据库层的约束）

**SQL Example / SQL 示例**:
用于引导 SQL 生成的“问题 + SQL”示例，必须归属于一个数据源或一个高级应用。
_Avoid_: Data training、training data

**Terminology / 术语**:
业务词或短语的解释，由主词和同义词构成，用于提升问题和表结构理解。
_Avoid_: Custom prompt、SQL example

**Custom Prompt / 自定义提示词**:
附加在模型任务上的场景指令，按任务环节（生成 SQL、分析、预测）分类，可按工作空间、数据源或高级应用生效。
_Avoid_: Terminology、SQL example

**Knowledge Scope / 知识作用域**:
术语、SQL 示例和自定义提示词生效的边界：工作空间、数据源或高级应用。高级应用是独立知识域，不继承工作空间级知识。
_Avoid_: 权限——作用域决定向模型注入哪些知识，权限决定用户能访问哪些数据

**Row Permission / 行权限**（xpack）:
对表追加的行级过滤条件；同一表命中多条时取 AND，经改写 SQL 执行。
_Avoid_: Column Permission

**Column Permission / 列权限**（xpack）:
从可见字段中剔除指定列；同一表命中多条时求交，作用于提供给模型的表结构。
_Avoid_: Row Permission

**Base Model / 基础模型**:
实际调用供应商 API 时使用的模型标识。
_Avoid_: 模型名称（仅显示用，与基础模型无强制关系）

**Default Model / 默认模型**:
系统全局唯一的默认问答模型；工作空间不设各自的默认模型。
_Avoid_: 工作空间默认模型（该概念不存在）

### 会话

**Chat / 会话**:
用户在一个工作空间内连续提出数据问题的对话。
_Avoid_: Assistant、dashboard

**Chat Origin / 会话来源**:
会话创建入口的溯源标记：页面、MCP 或小助手。
_Avoid_: 助手目标域名（Assistant Domain）

**Chat Record / 会话记录**:
一次问题执行的可持久化结果，包含问题、生成 SQL、查询结果、图表配置、错误以及关联的后续记录。
_Avoid_: Chat

**Opening Record / 开场记录**:
助手会话开始时自动创建的占位记录，无提问，承载数据源配置的推荐问题；不是一次真实的问答。
_Avoid_: 会话中第一条问答记录

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
允许承载小助手或嵌入页面的宿主 origin 精确白名单，仅在握手类接口校验。
_Avoid_: Business domain、workspace

**Assistant Certificate / 助手凭据**:
高级应用逐请求透传给宿主数据源 API 的宿主系统凭据。
_Avoid_: App Secret（验签密钥，不是透传凭据）

**App Secret / 应用密钥**:
页面嵌入应用与宿主页面共享的密钥，用作宿主自签 JWT 的验签依据。
_Avoid_: app_id（仅用于反查应用，无认证作用）、Assistant Certificate

**MCP**:
以独立服务进程暴露问数工具集的集成形态，调用者以真实用户身份接入，数据权限按该用户计算。
_Avoid_: Ordinary Assistant、Page-embedded Assistant

**Dashboard / 仪表板**:
由会话图表快照与文本、Tab 组件组成的画布；图表组件是会话记录的配置快照，数据在查看时实时查询。
_Avoid_: Chat、chat record

### 商业扩展（xpack）

以下词条的实现位于商业扩展包 sqlbot-xpack。

**License / 许可证**（xpack）:
商业授权凭据，以整体有效或失效门控商业功能，无功能级能力项。
_Avoid_: 社区版/企业版（代码仅区分许可证有效与否）

**Authentication Source / 认证源**（xpack）:
用于外部身份登录的 SSO 身份源，支持 CAS、OIDC、LDAP、OAuth2、SAML2。
_Avoid_: Platform Integration

**Platform Integration / 平台集成**（xpack）:
企业微信、钉钉、飞书、Larksuite 的组织与用户同步及扫码登录。
_Avoid_: Authentication Source
