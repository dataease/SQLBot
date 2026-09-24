# xpack 工作流 Agent 说明

`sqlbot-xpack` 默认作为版本范围由 `backend/pyproject.toml` 约束的已发布 wheel 使用；`uv.lock` 不入库，只用于冻结本机安装。日常任务不读取、不修改本地 xpack checkout。

## 主工程对 xpack 的运行时依赖

以下事实在"已发布 wheel"与"源码联调（editable）"两种模式下一致，修改依赖、初始化、许可证或前端集成前先掌握：

- `sqlbot-xpack` 是 `backend/pyproject.toml` 的**必装依赖**（不是 optional extra），索引指向 TestPyPI，CE 镜像构建必然包含；构建环境需能访问 test.pypi.org。
- 后端启动即无条件 import：`backend/main.py` 与多个业务模块（登录加解密、AES 落库、审计、行权限、参数管理、embedded 签名）顶层 import，没有降级路径——xpack 缺失则后端无法启动。8001 的 MCP 进程因 `uvicorn main:mcp_app` import 同一 `main` 模块，同样加载。
- `sqlbot_xpack.init_fastapi_app(app)` 在 import main 时执行：license/config/sse/row-permission/embedded 路由无条件注册；appearance/custom_prompt/authentication/platform/audit 仅在许可证 valid 时注册，到期后由监控任务动态摘除。
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
| `true` | 验证路径后，把该 checkout 作为可修改的 xpack 工作区，读取 `sqlbot-xpack/AGENTS.md`，并协调两个仓库的变更。 |

路径目录名可以任意，但必须是指向 xpack Git 仓库根目录的绝对路径；用 `git -C "$SQLBOT_XPACK_REPO" rev-parse --show-toplevel` 验证。环境变量优先于 `AGENTS.local.env`。不要静默覆盖该文件，也不要在其中保存密钥。

本地联调时，先加载配置，把 xpack 以 editable 方式安装进后端环境，并使用 `--no-sync` 避免 uv 用锁定 wheel 替换它：

```bash
set -a
. ./AGENTS.local.env
set +a
cd backend
uv pip install -e "$SQLBOT_XPACK_REPO"
uv run --no-sync pytest -q
```

在 `backend/` 执行 `uv sync` 可恢复已发布包。变更和提交必须分开：SQLBot 变更留在本仓库，xpack 变更留在独立仓库。完整发布顺序以 `docs/agents/packaging.md` 为准。

**源码联调的前提与影响面**：checkout 里的 `src/sqlbot_xpack/static` 被 gitignore、全新 checkout 不存在，而后端启动时会把包内 `static` 复制到前端 dist——目录缺失会让 `init_fastapi_app` 直接抛错、后端无法启动。因此首次联调前必须先在 xpack 仓库根目录执行一次 `./build_scripts/build-dev.sh`（构建并复制静态资源），之后每次改动 `xpack_static/` 也要重跑再重启。editable 安装作用于 backend 共享环境，8000 主服务和 8001 MCP 进程都会改用源码；改 Python 源码同样需要重启后端才生效。
