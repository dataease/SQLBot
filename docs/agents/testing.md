# 测试 Agent 说明

## 测试布局

所有测试都在 `backend/tests/`，从 `backend/` 目录用同一条命令运行：

```bash
uv run pytest -q
uv run pytest -q tests/<relevant-test.py>
```

按用途分两类（目录内不按类再分层级）：

- 后端单元回归：纯函数、连接池、数据格式、embedding、驱动兼容、分布式锁。
- 仓库守卫：SQL 转义、权限过滤、Host 校验、嵌入认证等安全修复；关键前端组件之间的错误传递和结构契约；supplier/model 配置一致性；i18n 键。这类测试常直接读取源码文本或用 AST 提取局部实现，路径从 `backend/tests/` 推到仓库根。

前端没有独立单测框架；`npm run build` 中的 `vue-tsc` 是类型验证，结构性契约由上述守卫测试保护。xpack 在独立仓库内先做 compileall 和静态 SDK 构建；完整集成在 SQLBot 后端环境中执行。

不要为了速度跳过与改动相关的层，也不要把所有历史失败当成当前变更造成的问题；先用目标测试定位边界。

## 新增测试约定

- 测试可隔离的纯逻辑或服务函数；
- 用 `Mock`、`SimpleNamespace`、SQLite 或 AST 加载方式隔离外部数据库和驱动；
- 不访问真实 LLM、数据库或互联网；
- 命名和断言风格跟随相邻测试。

`LOG_FORMAT` 只是 `logging.Formatter` 的百分号格式串模板，代码中没有 JSON 日志实现；若本机环境把它设成了非默认格式串导致 formatter 初始化失败，测试前 `unset LOG_FORMAT` 恢复默认。

## 守卫维护

当 intentional 变更导致守卫失败时，更新守卫以表达新契约；不要删除断言、扩大白名单或降低安全约束来让测试通过。

## 前端验证

```bash
cd frontend
npm run build
```

- 类型、模板和打包验证由 `vue-tsc -b` 与 Vite 完成。
- 修改少量文件时可用 `npx eslint <changed-file...> --fix`。
- 不要默认运行全量自动修复脚本。
- 当前不要自行引入 Vitest/Jest/Playwright 等新测试框架；若需要，先提出框架、运行成本和 CI 影响。

## 图表渲染服务

修改 `g2-ssr/` 或后端图表配置时，验证命令与前后端字段契约见 `g2-ssr/AGENTS.md`。

## Ruff 和类型检查

后端 Ruff 只针对改动文件运行，避免全仓库历史问题产生无关 diff：

```bash
cd backend
uv run ruff check <changed-file.py...>
uv run ruff format <changed-file.py...>
```

`pyproject.toml` 配置了 mypy strict，但历史代码尚未建立全仓库通过基线。新代码应避免引入新的类型问题；是否运行 mypy 由改动范围和相邻模块现状决定，不要自动对全仓库执行大规模修复。

## 测试选择标准

必须至少运行相关测试的情况：

- 修复 bug：覆盖原始失败输入和边界输入；
- 安全逻辑：覆盖攻击样本、拒绝路径和合法路径；
- 数据格式/连接池/embedding：运行对应既有测试；
- API 或前端结构契约：运行相关守卫测试；
- i18n：确认五种语言键结构；
- xpack 联调：使用 editable 安装并运行 SQLBot 后端测试。

完成标准：

- 相关测试通过，或明确记录与本次改动无关的既有失败；
- 新行为有回归测试或说明为什么不适用；
- 没有为了通过测试削弱安全约束；
- 没有引入网络、数据库、密钥或不可重复依赖；
- 正确仓库的 status/diff 只包含任务相关变更。
