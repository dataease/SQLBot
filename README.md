<p align="center"><img src="https://resource-fit2cloud-com.oss-cn-hangzhou.aliyuncs.com/sqlbot/sqlbot.png" alt="SQLBot" width="300" /></p>
<h3 align="center">基于大模型和 RAG 的智能问数系统（二次开发版）</h3>
<hr/>

本项目基于开源项目 [dataease/SQLBot](https://github.com/dataease/SQLBot) 二次开发。在原有"自然语言提问 → 生成 SQL → 返回数据和图表"的基础上，增加了问数后自动生成分析结论的能力，分析中用到的派生数值由数据库计算，不由大模型心算。

## 二次开发内容

| 功能 | 说明 |
| --- | --- |
| 问数后自动分析 | 问数完成后自动生成分析结论，不需要再手动点击"数据分析"按钮。可以用 `CHAT_AUTO_ANALYSIS_ENABLED` 关闭。 |
| 补充计算 SQL | 生成分析前，大模型先规划占比、环比、合计这类派生指标的补充查询（最多 `ANALYSIS_SUPPLEMENTARY_QUERY_MAX` 条）。补充查询只能访问本次问数已授权的表，并且只允许只读语句，校验通过后在数据库执行，分析结论引用执行结果，减少数值错误。 |
| 执行过程可见 | "执行详情"里新增"规划分析计算"和"执行分析计算 SQL"两个步骤，分析过程的思考内容也会展示出来。 |
| 切换会话不丢进度 | 回答生成过程中切换到其他会话再切回来，页面会继续轮询并显示后端的执行进度，直到回答完成。 |
| 失败提示 | 分析生成失败时给出明确的错误信息（已覆盖中、英、繁中、韩、泰五种语言）。 |

主要改动位置：`backend/apps/chat/task/llm.py`、`backend/templates/template.yaml`、`backend/common/core/config.py`、`frontend/src/views/chat/`。单元测试位于 `backend/tests/test_chat_auto_analysis.py`。

## 部署（Docker，推荐）

### 1. 环境要求

- Linux 服务器或 WSL2，4 核 8 GB 内存以上，磁盘可用空间 20 GB 以上
- Docker 20.10+，并安装 Docker Compose v2（`docker compose version` 能正常输出）
- 构建时要能访问 `registry.cn-qingdao.aliyuncs.com`、`ghcr.io`、npm 源和 PyPI
- 一个可用的大模型 API（OpenAI 兼容接口即可，例如 DeepSeek、通义千问）

### 2. 获取代码并配置

```bash
git clone <本仓库地址> SQLBot
cd SQLBot

cp .env.example .env
# 把 .env 里的 SECRET_KEY 替换为随机值
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$(openssl rand -hex 32)/" .env
```

### 3. 构建并启动

```bash
docker compose up -d --build
```

镜像从本仓库源码构建，第一次构建需要 10 到 30 分钟，视网络情况而定。查看启动日志：

```bash
docker compose logs -f sqlbot
```

日志出现 `Uvicorn running on http://0.0.0.0:8000` 表示启动完成。

### 4. 访问

- 地址：`http://<服务器IP>:8000/`
- 用户名：`admin`
- 密码：`SQLBot@123456`

### 5. 首次使用

1. 登录后进入"系统管理 → AI 模型配置"，添加一个大模型并设为默认模型。
2. 进入"数据源"，添加一个数据库连接（MySQL、PostgreSQL 等），选择要问数的表。
3. 回到"智能问数"，选择该数据源后提问，例如"各地区上月销售额及占比"。回答完成后会自动生成分析结论，点开"执行详情"可以看到补充计算的 SQL。

### 停止与清理

```bash
docker compose down        # 停止服务，数据保留在 ./data 目录
rm -rf ./data              # 如需清空全部数据（不可恢复）
```

## 配置项

在 `.env` 中设置，修改后执行 `docker compose up -d` 生效。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SECRET_KEY` | 无，必填 | JWT 签名密钥 |
| `SERVER_IMAGE_HOST` | `http://localhost:8001/images/` | MCP 返回图表图片时使用的地址，外部访问时改成服务器 IP |
| `CHAT_AUTO_ANALYSIS_ENABLED` | `true` | 问数完成后是否自动生成分析 |
| `ANALYSIS_SUPPLEMENTARY_QUERY_MAX` | `3` | 每次分析最多执行的补充查询数，`0` 表示不做补充计算 |
| `ANALYSIS_PLAN_DATA_ROWS` | `50` | 规划补充查询时提供给大模型的结果行数上限 |
| `ANALYSIS_SUPPLEMENTARY_TIMEOUT` | `120` | 等待补充计算的最长秒数，超时则不使用补充结果 |

## 运行测试

```bash
cd backend
uv sync
uv run pytest tests/test_chat_auto_analysis.py
```

## 常见问题

- **启动报 `Set a unique SECRET_KEY in .env`**：没有创建 `.env` 或其中没有 `SECRET_KEY`，按第 2 步处理。
- **构建时拉取镜像失败**：检查服务器能否访问 `registry.cn-qingdao.aliyuncs.com` 和 `ghcr.io`，必要时为 Docker 配置代理或镜像加速。
- **8000 / 8001 端口被占用**：修改 `docker-compose.yaml` 中 `ports` 的左侧端口，例如 `18000:8000`。
- **提问没有回答**：确认已配置默认大模型，并且服务器能访问该模型的 API 地址。

## 致谢与 License

本项目基于 [dataease/SQLBot](https://github.com/dataease/SQLBot)（飞致云 DataEase 开源项目组）二次开发，遵循原项目的 [FIT2CLOUD Open Source License](LICENSE)。该协议本质上是 GPLv3，并附加以下限制：

- 不能替换和修改 SQLBot 的 Logo 和版权信息；
- 二次开发后的衍生作品必须遵守 GPL V3 的开源义务。
