# 打包与发布 Agent 说明

## 产物组成

运行镜像由多个阶段组成：

1. 前端构建：在 Node 22 Bookworm 镜像中对 `frontend/` 执行 `npm install` 和 `npm run build`，产物进入 `/opt/sqlbot/frontend/dist`。
2. 后端构建：从运行基础镜像派生编译层，使用 uv 同时解析应用依赖和镜像专用安全约束，构建 PostgreSQL 和 SQL Server 驱动，使其链接运行层系统库。`uv.lock` 不入库，构建会重新解析依赖。
3. 图表服务构建：复制 `g2-ssr/app.js`、`package.json` 和 `charts/`，从源码构建 canvas，使其使用运行层的 Debian 图形库。编译层和运行层使用相同的 Node 主版本和 Debian 发行版。
4. 运行层：`Dockerfile-pg-base` 基于 PostgreSQL 17 Bookworm 安装系统安全更新和 pgvector。`Dockerfile-base` 在此基础上加入 Python、Node、Oracle 客户端及许可证校验器。图形库从 Bookworm 源码包构建，HarfBuzz 应用 CVE-2023-25193 上游补丁，GDK Pixbuf 禁用未使用的 TIFF 加载器。应用镜像复制前端、后端、g2-ssr、字体、向量模型和启动脚本，并使用 dmPython wheel 提供的达梦客户端库。
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

- `build-base-and-push` 通过 `docker-bake.hcl` 先构建 PostgreSQL 层，再产出 `sqlbot-python-pg` 基础镜像。PostgreSQL 中间镜像只在构建图中使用。
- 构建应用镜像时，通过 `SQLBOT_RUNTIME_IMAGE` 传入已验证的基础镜像标签或 digest。`build-and-push` 的 `runtimeBaseImage` 输入支持此覆盖。默认使用阿里云 `latest`。
- 本地执行 `docker buildx bake -f docker-bake.hcl --load app` 可按顺序构建三层。单独验证基础镜像时，将目标改为 `base`。
- 这些工作流都是发布/分发流程，不要因为普通代码修改建议运行。
- `latest` 只应在正式发布时启用。
- arm64 和 amd64 的依赖、驱动和包名必须同时考虑。
- 离线包会替换 `SQLBOT_TAG` 并生成 version 文件；不要在源码里提交生成后的 tag。
- xpack 工作流会 checkout 独立仓库；不要把本地 `sqlbot-xpack/` 目录当作它的输入。

## 发布顺序

1. 主仓库功能和测试完成。
2. 若涉及 xpack：
   1. xpack 独立仓库完成实现、版本提升（经使用者确认）和静态构建；
   2. 发布目标 wheel；
   3. 主仓库更新 `backend/pyproject.toml` 版本范围，`uv sync` 重锁本机 lock 并安装新 wheel 后重新验证。
3. 确认迁移、默认配置和 installer 模板兼容。
4. 构建 base 镜像（仅在 base 变更时）。
5. 构建主镜像。
6. 构建在线 / 离线安装包。

发布版本号、镜像 tag、离线包名、backend 包版本和 Git tag 必须由使用者明确确认。agent 不要自行发布、上传、打 tag 或推送。
