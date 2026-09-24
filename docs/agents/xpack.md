# xpack 工作流 Agent 说明

`sqlbot-xpack` 默认作为版本范围由 `backend/pyproject.toml` 约束的已发布 wheel 使用；`uv.lock` 不入库，只用于冻结本机安装。日常任务不读取、不修改本地 xpack checkout。

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
