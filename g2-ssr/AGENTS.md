# g2-ssr Agent 说明

## 定位

无框架 Node.js http 服务，端口 `3000`。接收后端提交的图表配置，用 `@antv/g2-ssr` + `node-canvas` 渲染为 PNG。`app.js` 是唯一入口；图表实现位于 `charts/`（bar、column、line、pie、utils）。

## 修改

- 新增图表类型：新建 `charts/<type>.js` 导出 `get<Xxx>Options`，并在 `app.js` 中注册。
- 请求体、图表配置或输出路径是与 backend 的契约（图表配置在 `backend/apps/chat` 的会话流程中生成）；变更时两侧一起核对字段一致。
- 依赖变更只改 `package.json`，`package-lock.json` 不入库；注意容器构建依赖 canvas 相关系统库。
- Dockerfile 只 COPY `app.js`、`package.json`、`charts/*`、`*.ttf` 和 `supervisord.conf`，运行目录 `/opt/sqlbot/g2-ssr`；新增文件或改路径时核对 COPY 范围。

## 验证

在仓库根目录运行改动文件的语法检查。调整数值或百分比格式时，用 Node 内置测试验证图表数据、标签和提示框：

```bash
node --check g2-ssr/app.js
node --check g2-ssr/charts/<changed-file.js>
node --test g2-ssr/test/chart-percent.test.cjs
```
