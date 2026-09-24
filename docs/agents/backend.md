# 后端 Agent 说明

## 领域与代码映射

- `oid` 和 `workspace_id` 是同一个工作空间 ID 的历史命名。
- `AssistantModel.type`：
  - `0`：普通小助手；
  - `1`：高级应用；
  - `4`：页面嵌入。
- `AssistantModel.domain` 表示对接目标系统的域名，不是业务领域。
- `DataTraining` 是「SQL 示例库」概念的持久化命名。

## 代码组织

- 领域代码放在 `backend/apps/<domain>/`。多数域采用 `api/`、`crud/` 或 `curd/`、`models/` 分层；`schemas/` 仅 `system` 和 `settings` 有，`chat` 另有 `task/`，`ai_model`、`db`、`mcp`、`template`、`swagger` 不遵循该布局——新代码跟随所在域的既有形态。
- 项目同时存在 `crud` 和 `curd` 拼写；不要为统一命名制造无关重构。
- 新 router 注册到 `backend/apps/api.py`。
- 应用组装、中间件、MCP、静态资源挂载和 xpack 初始化属于 `backend/main.py`。
- SQLModel 结构变更必须配套 Alembic 迁移；细节见 `docs/agents/migrations.md`。
- 用户可见后端消息使用 `backend/locales/`，不要硬编码新文案。

## API 黄金路径

新 endpoint 参考 `terminology`、`data_training` 域和 `datasource` 域内的 `recommended_problem` 模块（`backend/apps/datasource/api/recommended_problem.py`）的分层：

1. 在 `api/<domain>.py` 定义 router、prefix、tags 和 Swagger summary；
2. 使用 `SessionDep`、`CurrentUser`、`Trans` 等依赖注入；
3. 资源型接口配置 `@require_permissions`，确认 `keyExpression` 指向真实资源；
4. 需要审计的操作配置 `@system_log`，新代码优先让权限装饰器位于审计装饰器外层，只记录已授权操作；
5. handler 只做参数解析、权限上下文提取和分支，业务规则下沉到 CRUD/service；
6. 返回领域对象、DTO 或既有分页 dict；正常 JSON 由 `ResponseMiddleware` 包装，不要手工包一层 `code/data/msg`；
7. 用户可见异常通过 `Trans` 使用 locale key；`HTTPException` 留在 API 层，不要让 CRUD 依赖 FastAPI 响应细节。

Endpoint 命名沿既有风格：

- 分页：`GET /page/{current_page}/{page_size}`；
- 新增或更新：`PUT ""`，按 `info.id` 分支；
- 删除：`DELETE ""`，传 ID 列表；
- 启用/禁用：`GET /{id}/enable/{enabled}`；
- 导出：`GET /export`；
- 导入：`POST /uploadExcel`。

只在确实与现有 API 兼容性冲突时发明新形态，并说明原因。

## CRUD 与查询

- 查询构建参考 `build_<entity>_query` 的分层：
  1. `get_<entity>_base_query` 构造工作空间过滤；
  2. `build_<entity>_query` 追加搜索、作用域、join、count 和分页；
  3. `execute_<entity>_query` 转换为 DTO/result；
  4. `page_<entity>` 返回 API 需要的分页元数据。
- 默认过滤当前 `current_user.oid`；管理员或助手场景必须显式说明为何可以切换工作空间。
- 使用 SQLAlchemy `select` / `and_` / `or_` 表达查询；不要为用户输入拼接 SQL 字符串。
- 分页先 count，再计算 `total_pages`，最后构造 offset/limit 子查询。
- 创建/更新前完成重复性、必填和作用域校验；不要先写入再依赖唯一约束报错。
- 事务提交通常发生在 CRUD/service 边界；API handler 不要随意中途 commit。
- embedding、缓存清理或后台任务沿用当前领域的线程任务模式，不在请求路径中阻塞等待长任务。

## 异步与阻塞

- FastAPI handler 可以是 `async def`，但不要在事件循环中执行外部 HTTP、pandas 大文件解析、CPU 密集转换或长时间文件 IO。
- 这些操作参考现有 `asyncio.to_thread(inner)` 模式。
- 数据库 session 由依赖注入管理；在线程中需要新 session 时使用对应 `session_maker()` 并确保清理。
- 不要把 `asyncio.to_thread` 当成绕过权限或事务边界的手段。

## 模型与 DTO

- 表模型继承 `SQLModel, table=True`；输入/输出 DTO 使用 Pydantic BaseModel 或非 table SQLModel。
- 大 ID 使用 `BigInteger`；返回给前端时按既有 DTO 规则处理超过 JavaScript 安全整数的情况。
- 时间、启用状态、工作空间归属和高级应用/数据源作用域要显式建模，不依赖调用方隐式状态。
- 新增字段同时考虑迁移、导入/导出、embedding、缓存和 xpack 调用。

## 安全与事务边界

- 保留认证、工作空间/数据源权限、审计日志和既有错误响应模式；不要在 handler 中绕过它们。
- 生成 SQL、路径、Host 头和上传文件都按不可信输入处理。
- 不要削弱行数限制、权限过滤、元数据查询控制、Host 校验或路径穿越防护。
- 修改连接池、事务和异步执行边界时，先阅读相邻实现和回归测试；不要把阻塞调用移回事件循环。
- 商业实现留在 xpack；本仓库只保留对已发布包的调用和初始化。

## Chat 问题流程

主要入口在 `backend/apps/chat/api/chat.py`：

1. `POST /chat/start` 与 `POST /chat/assistant/start` 在工作空间内创建会话，并可绑定初始数据源或助手上下文。
2. `POST /chat/question` 先解析快速命令。普通问题进入 `stream_sql`；`/regenerate` 直接再生。`/analysis` 和 `/predict` 在会话内会直接拒绝（temporary not supported），实际通过 `POST /record/{chat_record_id}/{action_type}` 触发。
3. `stream_sql` 构造 `LLMService`，创建 `ChatRecord`，并启动异步执行。
4. 已绑定数据源时，服务先提取关键词并扩展术语，再筛选适用的术语、SQL 示例和自定义提示词，随后组装 SQL 消息。
5. 未绑定数据源时，先由模型选择数据源；服务随后校验数据源访问权和连接可用性。
6. 模型生成 SQL 后，服务解析 SQL、对照允许的表元数据校验引用表，并按需应用行权限或助手动态 SQL 变换。
7. 服务执行最终 SQL，规范化大数字和带限定名的列结果，并持久化查询结果。
8. 模型基于实际使用的表结构生成图表配置；服务校验并持久化配置。非会话式流式调用还可请求渲染图片。
9. 分析和预测是基于既有图表记录的独立后续执行。
10. 猜测问题与已配置的推荐问题分开生成。

`ChatFinishStep` 允许一次执行在生成 SQL、查询数据或生成图表后停止。不要假设所有调用方都需要完整图表流程。

验证要求与测试选择标准见 `docs/agents/testing.md`。
