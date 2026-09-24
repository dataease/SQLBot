# SQLBot Agent 指南

SQLBot 让业务用户用自然语言提问，基于已配置的数据源生成并安全执行 SQL，返回数据、图表、分析和后续问题建议。领域词汇表见 `CONTEXT.md`。

## 仓库结构

| 路径 | 职责 |
| --- | --- |
| `backend/` | Python 3.11 / FastAPI / SQLModel 后端。`main.py` 组装应用、MCP、中间件、静态资源和 xpack；业务域在 `apps/`，共享代码在 `common/`，迁移在 `alembic/versions/`，全部测试（含仓库守卫）在 `tests/`。 |
| `frontend/` | Vue 3、TypeScript strict、Vite、Pinia、Vue Router 和 Element Plus。请求在 `src/api/`，共享实体在 `src/entity/`，状态在 `src/stores/`，路由在 `src/router/`，UI 在 `src/views/` 和 `src/components/`。 |
| `g2-ssr/` | Node.js 图表渲染服务，使用 `@antv/g2-ssr`；图表实现位于 `charts/`，目录内有独立 `AGENTS.md`。 |
| `installer/` | 离线安装、卸载、配置模板和服务控制脚本。 |
| `Dockerfile*`、`docker-compose.yaml`、`start.sh` | 容器组装和运行时进程启动。 |

商业扩展源码维护在独立仓库 [dataease/sqlbot-xpack](https://github.com/dataease/sqlbot-xpack)。它不是 submodule，也不是本仓库的固定子目录。本地 `sqlbot-xpack/` checkout 会被主仓库忽略，永远不应出现在本仓库 PR 中。

## xpack 工作流

默认使用开源版 SQLBot 工作流：把 `sqlbot-xpack` 视为版本范围由 `backend/pyproject.toml` 约束的已发布 wheel（精确版本冻结在不入库的 `uv.lock`）。不读取、不修改本地 xpack checkout。

只有任务确实需要修改或调试闭源 xpack 代码，或需要两个仓库联动验证时，才按 `docs/agents/xpack.md` 检查本地关联开关（`AGENTS.local.env`）并协调两个仓库的变更。

## 按需文档

| 触发条件 | 必读文档 |
| --- | --- |
| 修改业务逻辑、数据模型（SQLModel）、权限、Chat 问题流程、助手集成、前端信息架构，或需要命名和领域术语 | `CONTEXT.md` |
| 修改后端业务代码 | `docs/agents/backend.md` |
| 修改前端代码 | `docs/agents/frontend.md` |
| 修改或新增测试、执行验证 | `docs/agents/testing.md` |
| 修改用户可见文案或新增语言 | `docs/agents/i18n.md` |
| 修改认证、授权、SQL 执行、上传/下载、嵌入协议或前端渲染安全 | `docs/agents/security.md` |
| 修改 SQLModel 模型或 Alembic 迁移 | `docs/agents/migrations.md` |
| 修改 Dockerfile、installer、GitHub Actions 或发布产物 | `docs/agents/packaging.md` |
| 修改或调试闭源 xpack 代码、双仓库联动验证 | `docs/agents/xpack.md` |
| 修改图表渲染服务、后端图表配置或图表字段/输出契约 | `g2-ssr/AGENTS.md` |
| 领域边界仍不明确 | `docs/agents/domain-open-questions.md`，并向使用者确认 |

## 全局硬规则

- 在正确仓库检查 status/diff；SQLBot 主仓库和 xpack 独立仓库不要混出同一个提交。
- 不要提交日志、构建产物、`.env` 值、密钥、本地路径、私有 registry 配置或生成的 xpack 产物。
- 提交信息和 PR 描述不添加 `Co-Authored-By`、"Generated with" 等任何 AI 工具署名行。
- 提交信息沿用仓库既有 conventional 风格：`fix:`、`feat:`、`refactor:` 等前缀（可带 scope），单行概述。
- 不要为了通过测试削弱安全守卫；安全、权限、SQL、Host、路径和嵌入认证改动必须有相关回归验证。
- 修改 Docker、installer 或路径配置时，核对前端构建产物、后端工作目录、`/opt/sqlbot` 数据目录、图表输出和日志挂载仍然一致。
- 依赖、lockfile 和版本号只在任务明确需要时更新；不要顺手刷新。
- 验证以构建和测试为准；除非用户明确要求，不构建 Docker 镜像、不启动完整运行栈。
- 除非用户明确要求，不要上传、发布或推送镜像 / wheel / 包。
- 变更涉及本文件或 `docs/agents/` 描述的约定（目录职责、命令、流程）时，同步更新对应文档。
