# SQLBot 开发用 MCP

项目级 MCP 布局，提供 TAPD、Playwright 和 DBHub 启动器。
这里服务于 Codex 开发任务，与 SQLBot 产品对外提供的 MCP 接口无关。

## 配置与启用

[Codex 官方 MCP 文档](https://developers.openai.com/codex/mcp)支持受信任项目使用 `.codex/config.toml`。
本仓库三个服务配置为 `enabled = true`。首次使用前需完成本地配置；暂不使用的服务应设为 `enabled = false`，避免缺少配置时启动失败。

1. 在本机安装需要的 MCP 服务，记录其入口文件位置；启动器不会自动安装依赖。
2. 将相应目录的 `.env.example` 复制为同目录 `.env.local`，填写自己的入口、解释器和项目配置。
3. 在 `.codex/config.toml` 中确认需要的服务为 `enabled = true`，其余设为 `false`；从 SQLBot 仓库根启动新的 Codex 会话，并检查 MCP 连接状态。

配置中的启动脚本路径相对于仓库根。不要从子目录启动这些相对路径命令。
`.env.local` 使用 `KEY="value"` 格式，值必须是 JSON 字符串；不支持 shell 展开、单引号或行尾注释。
未知字段、重复字段和缺失必填值会导致启动失败，错误消息不回显配置值。
本地配置、浏览器资料及输出已被 Git 忽略；建议将 `.env.local` 权限设为 `600`。
不要复制其他项目的凭据、项目 ID 或浏览器会话。

## 服务约定

- **TAPD**：填写 SQLBot 对应的 `TAPD_WORKSPACE_ID`、个人用户名、令牌和入口。配置保留参考项目的 Node/Python 两种实现的读取工具白名单，不开放写入工具。Python `mcp-server-tapd` 调用仍须显式传本项目 `workspace_id`；启动器不会自动注入每次调用。不要使用会另行加载其他个人凭据的包装入口。
- **Playwright**：使用支持 Chrome、`--user-data-dir` 和 `--output-dir` 参数的 `@playwright/mcp` 入口，并准备本机 Chrome。浏览器资料位于 `playwright_mcp/browser-profile/`，截图等产物位于 `playwright_mcp/output/`。`TEST_BASE_URL` 是本机示例，需按实际测试环境调整；`TEST_*` 仅供执行测试时按需使用，启动器不会自动登录。
- **DBHub**：沿用参考项目针对 `@bytebase/dbhub@1.3.1` 的配置格式，入口须支持 `--config`。示例 DSN 已改为 PostgreSQL/sqlbot，仅用于展示格式。DSN 通过环境变量传递，`dbhub.toml` 为 `execute_sql` 设置 `readonly = true` 和最多 1000 行；数据库账号本身也必须只读。只在任务授权的测试环境使用，不用生产或共享业务库做配置验证。

## 运行时

外层启动器需要 PATH 中的 Python 3.9+。`mcp_runtime.py` 统一处理配置和入口解析：

- `MCP_RUNTIME="auto"` 根据 `.js/.cjs/.mjs`、`.py` 或 Node/Python shebang 识别运行时，也可明确指定 `node` 或 `python`。
- MCP 入口须为已存在的绝对路径；`NODE_BIN` / `PYTHON_BIN` 可为绝对路径或 PATH 命令名。桌面应用 PATH 可能与终端不同，推荐在本地配置中填写解释器绝对路径。
- Python MCP 使用其安装环境的解释器。Python TAPD 将 `TAPD_API_TOKEN` 映射为 `TAPD_ACCESS_TOKEN`，将用户名映射为 `CURRENT_USER_NICK`，并使用 stdio。
- 运行时识别不保证不同 MCP 实现的命令行参数和工具 API 兼容。Playwright、DBHub 模板面向上述 Node 实现。

## 验证

从仓库根运行：

```bash
python3 -B backend/tests/test_codex_mcp_runtime.py
```

离线测试覆盖配置校验、解释器选择和启动参数/环境变量传递，不连接外部服务。
配置解析或离线测试通过不代表真实 MCP 握手、工具调用或数据库只读权限已经验证。
