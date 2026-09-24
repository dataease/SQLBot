# 打包与发布 Agent 说明

## 产物组成

运行镜像由多个阶段组成：

1. 前端构建：`frontend/` 执行 `npm install` 和 `npm run build`，产物进入 `/opt/sqlbot/frontend/dist`。
2. 后端构建：复制 `backend/`，使用 base 镜像中的 uv 安装依赖。以根 `Dockerfile` 为准：中间层包含 `uv sync --frozen` 尝试，最终层执行 `uv sync --extra cpu`，不是全程冻结安装。`uv.lock` 不入库，不能据此承诺全新 checkout 的依赖可复现；`|| echo` 的提示也不能证明失败只因缺少 lock，需检查实际构建日志。
3. 图表服务构建：复制 `g2-ssr/app.js`、`package.json` 和 `charts/`，安装 Node 依赖和 canvas 相关库。
4. 运行层：基于含 PostgreSQL / Python 的 base 镜像，复制前端、后端、g2-ssr、字体、向量模型和启动脚本。
5. 启动脚本依次准备 PostgreSQL、supervisor/g2-ssr、MCP 服务和主 FastAPI 服务。

修改路径、端口、依赖或构建脚本时，必须核对最终运行目录仍是 `/opt/sqlbot` 布局，且数据、图片、日志和字体路径没有断开。

## 本地验证

普通代码任务不要默认构建镜像；Docker 构建需要外部镜像、模型资源和较长耗时。任务已要求镜像或部署验收时，构建属于验证范围，明确目标平台后执行；仅需接口或浏览器验证时优先启动必要的隔离服务，不自动扩大为镜像构建。

可以做的轻量检查：

```bash
cd frontend
npm run build
```

```bash
cd backend
uv run pytest -q
```

```bash
node --check g2-ssr/app.js
node --check g2-ssr/charts/<changed-file.js>
```

修改 Dockerfile 或 installer 后，至少人工追踪：

- COPY 源路径和目标路径；
- 构建阶段产物是否被运行层复制；
- `start.sh` 启动顺序和健康检查端口；
- `8000` / `8001` / `3000` / `5432` 的用途；
- excel、file、images、logs、PostgreSQL 数据挂载；
- `installer/sqlbot/templates/sqlbot.conf` 中的环境变量仍然存在且默认值安全。

## GitHub Actions

| 工作流 | 用途 | 关键输入 |
| --- | --- | --- |
| `build-base-and-push` | 构建 PostgreSQL / Python base 镜像 | tag、架构、registry、是否 latest |
| `build-and-push` | 构建 SQLBot 主镜像 | tag、架构、registry、是否 latest |
| `package-and-push` | 构建 CE/EE 在线与离线安装包 | SQLBot tag、架构、registry、是否 EE |
| `Build Wheels Universal` | 从主仓库触发 xpack 多平台 wheel 构建 | xpack 分支、平台矩阵、是否发布、TestPyPI/PyPI |
| `Typos Check` | push 和 PR 的拼写检查 | — |
| `Synchronize to Gitee` | push 时同步镜像到 Gitee | — |
| `Sync to CNB` | 手动同步到 CNB | — |

规则：

- 根 `Dockerfile` 的构建阶段还依赖 `registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest`，该镜像不在本仓库工作流中构建（外部维护）；`build-base-and-push` 只产出 `sqlbot-python-pg` base 镜像。
- 这些工作流都是发布/分发流程，不要因为普通代码修改建议运行。
- `latest` 只应在正式发布时启用。
- arm64 和 amd64 的依赖、驱动和包名必须同时考虑。
- 离线包会替换 `SQLBOT_TAG` 并生成 version 文件；不要在源码里提交生成后的 tag。
- xpack 工作流会 checkout 独立仓库；不要把本地 `sqlbot-xpack/` 目录当作它的输入。

## 发布顺序

1. 主仓库功能和测试完成。
2. 若涉及 xpack：
   1. xpack 独立仓库完成实现、版本提升和静态构建；
   2. 发布目标 wheel；
   3. 主仓库更新 `backend/pyproject.toml` 版本范围并重新验证。
3. 确认迁移、默认配置和 installer 模板兼容。
4. 构建 base 镜像（仅在 base 变更时）。
5. 构建主镜像。
6. 构建在线 / 离线安装包。

发布版本号、镜像 tag、离线包名、backend 包版本和 Git tag 必须由使用者明确确认。agent 不要自行发布、上传、打 tag 或推送。
