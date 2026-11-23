# xpack 工作流 Agent 说明

`sqlbot-xpack` 默认作为版本范围由 `backend/pyproject.toml` 约束的已发布 wheel 使用；`uv.lock` 不入库，只用于冻结本机安装。日常任务不读取、不修改本地 xpack checkout。

## 主工程对 xpack 的运行时依赖

以下描述以当前依赖实现为背景；包内路由、许可证和静态资源行为会随 xpack 版本变化。修改相关集成时记录实际安装版本，并核对对应 wheel 的 `core.py` / `init_fastapi_app`；源码联调核对目标 checkout，不把本文当作所有版本的固定契约。主仓库入口见 `backend/main.py`、`backend/pyproject.toml` 和 `frontend/src/router/watch.ts`：

- `sqlbot-xpack` 是 `backend/pyproject.toml` 的**必装依赖**（不是 optional extra），索引指向 TestPyPI，CE 镜像构建必然包含；构建环境需能访问 test.pypi.org。
- 后端启动即无条件 import：`backend/main.py` 与多个业务模块（登录加解密、AES 落库、审计、行权限、参数管理、embedded 签名）顶层 import，没有降级路径——xpack 缺失则后端无法启动。8001 的 MCP 进程因 `uvicorn main:mcp_app` import 同一 `main` 模块，同样加载。
- `sqlbot_xpack.init_fastapi_app(app)` 在 import main 时执行：license/config/sse/row-permission/embedded 路由无条件注册；新版共享账号绑定模型可用时，`/system/account-bindings` 也无条件注册（能力查询、列表及解绑可在到期后使用，发起认证及确认绑定仍检查许可证）；appearance/custom_prompt/authentication/platform/audit 仅在许可证 valid 时注册，到期后由监控任务动态摘除。
- 静态资源在启动时从 wheel 解包复制到 `../frontend/dist/xpack_static`（相对路径，要求后端进程 CWD 在 `backend/`），由主 app 挂载 serve——前端 dist 静态挂载的实际位置在 xpack `core.py`，不在 `main.py`。
- 许可证只做功能门控，不做加载门控：无许可证时 xpack 仍完整加载，登录加密、SSE、行权限、审计等基础功能照常走 xpack 代码。
- 前端首次路由必加载 `/xpack_static/license-generator.umd.js`（window 全局 `LicenseGenerator`，无类型声明）；登录/改密加密和动态路由注册硬依赖它，脚本加载失败无降级，只提示并中断导航。

只有任务确实需要修改或调试闭源 xpack 代码，或者需要两个仓库联动验证时，才检查本地关联开关。未提交的根目录 `AGENTS.local.env` 保存本机配置：

```dotenv
# 请把路径替换为本机真实的 xpack 仓库根目录绝对路径。
SQLBOT_XPACK_LINK_ENABLED=true
SQLBOT_XPACK_REPO=/replace/with/your/sqlbot-xpack-checkout
```

| 开关状态 | 行为 |
| --- | --- |
| 未配置或值无效 | 仅当任务需要 xpack 时，询问一次是否开启本地关联；同意后验证并保存路径。 |
| `false` | 继续使用已发布 wheel。不读取路径、不安装 editable 包、不修改 xpack、不重复询问。若任务无法绕开闭源实现，说明需要用户主动开启开关。 |
| `true` | 验证路径后读取目标仓库根目录的 `AGENTS.md`，在已授权的任务范围内联调；开关本身不授权无关修改、推送或发布。 |

路径目录名可以任意，但必须是指向 xpack Git 仓库根目录的绝对路径；用 `git -C "$SQLBOT_XPACK_REPO" rev-parse --show-toplevel` 验证。环境变量优先于 `AGENTS.local.env`；文件按键值读取（不 `source` 执行内容、不展开变量），只接受 `SQLBOT_XPACK_LINK_ENABLED` 和 `SQLBOT_XPACK_REPO` 两个键，未知键或值无效时报错而非忽略。不要静默覆盖该文件，也不要在其中保存密钥。xpack 仓库侧的 `AGENTS.local.env`（`SQLBOT_MAIN_REPO`）只在直接从 xpack 仓库发起工作时需要，从本仓库发起联调不必创建它。

本地联调前按上述优先级读取两个配置值：已设置的环境变量优先，只从本机可信配置文件补齐未设置项；不要直接 `source` 文件覆盖环境变量或执行其中任意 shell 内容。确认开关为 `true` 且路径验证通过后，导出解析得到的 `SQLBOT_XPACK_REPO`。下面命令从 SQLBot 根目录运行，作用于选定后端环境；优先使用隔离环境，使用共享环境时先确认受影响的运行服务，并记录恢复方式：

```bash
# 按键值读取 AGENTS.local.env（只取值，不 source 执行文件内容）；环境变量已设置时优先
SQLBOT_XPACK_REPO="${SQLBOT_XPACK_REPO:-$(sed -n 's/^SQLBOT_XPACK_REPO=//p' AGENTS.local.env | tr -d "\"'")}"
test -n "$SQLBOT_XPACK_REPO" || { echo "SQLBOT_XPACK_REPO 未配置" >&2; exit 1; }
cd backend
uv pip install -e "$SQLBOT_XPACK_REPO"
uv run --no-sync pytest -q
```

在 `backend/` 执行 `uv sync` 可恢复已发布包。变更和提交必须分开：SQLBot 变更留在本仓库，xpack 变更留在独立仓库。完整发布顺序以 `docs/agents/packaging.md` 为准。

**源码联调的前提与影响面**：checkout 里的 `src/sqlbot_xpack/static` 被 gitignore、全新 checkout 不存在，而后端启动时会把包内 `static` 复制到前端 dist——目录缺失会让 `init_fastapi_app` 直接抛错、后端无法启动。因此首次联调前必须先在 xpack 仓库根目录执行一次 `./build_scripts/build-dev.sh`（构建并复制静态资源），之后每次改动 `xpack_static/` 也要重跑再重启。editable 安装作用于 backend 共享环境，8000 主服务和 8001 MCP 进程都会改用源码；改 Python 源码同样需要重启后端才生效。

## 账号绑定共享契约

`UserBindingRequest` 与 `UserPlatformModel` 的关联字段、唯一约束由主工程模型及 `076_user_account_bindings.py` 管理，商业认证适配和绑定 API 留在 xpack。新版 xpack 对缺少 `UserBindingRequest` 的旧主工程不注册绑定路由，维持可导入性；新版主工程启用绑定前需先完成两仓库联调并消费包含绑定实现的 wheel。仅本地 editable 验证不能替代发布和依赖引用更新。原有登录组件不参与绑定回调，认证成功后的用户解析按显式关联 UID 获取原账号。

个人信息页通过已认证的 `GET /system/account-bindings/capabilities` 读取 `show_bindings`、`can_bind`，不以列表为空或许可证异常推断版本。有效许可证允许本地账号展示绑定管理并发起绑定；无有效许可证且本人无历史绑定时只显示基本信息，有历史绑定时仅展示已绑定项并允许验证本地密码后解绑。能力与列表仅查询当前本地用户，非本地账号不调用绑定 API。实际新增及确认接口仍独立校验许可证，前端能力信息不替代后端权限检查。

## Excel 导入错误报告

术语配置、SQL 示例库和 xpack 自定义提示词共用下载接口。三个导入入口在生成错误报告后返回 `report_id`（UUID）和供前端展示、保存文件用的 `error_excel_filename`，没有错误报告时这两个字段均为 `null`。下载请求只传 `report_id`。报告由主仓库的 `backend/common/core/file.py` 写入 Excel 目录下的 `import-error-reports/`，按当前用户和工作空间读取，无需数据库记录。切换此契约时，前端、主仓库后端和包含该改动的 xpack wheel 需要配套部署。

账号绑定新增 LDAP 凭据验证步骤（origin 3），复用认证源映射和显式确认协议。国际飞书（origin 9）仅允许历史关联管理；新增及确认均拒绝。审计将历史 `account_binding` 的 add/delete 记录映射为绑定/解绑类型，主工程新增操作枚举和五种语言文案需与 xpack 配套部署。
