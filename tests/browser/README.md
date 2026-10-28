# Playwright 浏览器复现与回归

工具独立于 `frontend`，不改变前端业务依赖或构建。CLI 用于探索和复现，Playwright Test 用于保存可重复执行的回归。两个工具均为 Apache-2.0 许可，具体版本固定在本目录的 `package.json` 和 `package-lock.json`。

## 安装与自检

需要 Node.js 20+、npm 和本机 Google Chrome。所有命令从仓库根目录执行：

```sh
npm --prefix tests/browser ci
npm --prefix tests/browser run test:smoke
```

自检自动启动仅监听 `127.0.0.1:4198` 的静态页面，验证浏览器启动、页面加载、输入、点击和断言，结束后关闭页面服务。它不连接业务后端，也不代表 SQLBot 功能回归通过。端口冲突时可设置 `PLAYWRIGHT_DEMO_PORT`。

默认复用本机 Chrome，不自动下载浏览器。Test 可通过 `PLAYWRIGHT_CHANNEL=msedge` 改用已安装的 Edge。若 CI 使用 Playwright Chromium，先在本目录执行 `npm exec -- playwright install chromium`，再设置 `PLAYWRIGHT_CHANNEL=chromium`。CLI 的浏览器选择独立配置，默认 Chrome，可在 `open` 时指定 `--browser=msedge`。

## 使用 CLI 复现

确保目标开发或测试服务已就绪。本工具不启动 SQLBot 后端或执行数据库迁移。

```sh
npm --prefix tests/browser run cli -- -s=tapd-1077724 open http://127.0.0.1:5173
npm --prefix tests/browser run cli -- -s=tapd-1077724 find 登录
npm --prefix tests/browser run cli -- -s=tapd-1077724 snapshot
# 从快照取得目标 ref 后执行 click/fill，或使用稳定的 role/CSS 定位器。
npm --prefix tests/browser run cli -- -s=tapd-1077724 console error
npm --prefix tests/browser run cli -- -s=tapd-1077724 close
```

每条缺陷使用不同的 `-s=` 会话名，所有命令带上同一会话名。`open` 默认无头；需要可视操作时加 `--headed`。CLI 使用独立、非持久化浏览器上下文，不使用个人 Chrome 用户资料。

配置位于 `.playwright/cli.config.json`。快照及控制台等输出写入 `output/cli/`，终端显示文件路径；优先 `find` 或局部 `snapshot`，只读取相关片段。已知操作可合并为一条 `run-code`，只返回必要结果。按需截图，避免每个动作后全页截图；不要把完整快照反复读回上下文。

CLI 自检可使用静态演示页。在一个终端启动：

```sh
npm --prefix tests/browser run demo
```

另一个终端执行：

```sh
npm --prefix tests/browser run cli -- -s=tooling open http://127.0.0.1:4198
npm --prefix tests/browser run cli -- -s=tooling run-code 'async page => { await page.getByLabel("测试内容").fill("CLI 已就绪"); await page.getByRole("button", { name: "显示内容" }).click(); return await page.getByLabel("显示结果").textContent(); }'
npm --prefix tests/browser run cli -- -s=tooling close
```

完成后在演示页终端按 Ctrl-C 停止服务。不要使用 `close-all` 或 `kill-all` 影响其他任务的浏览器。

## 使用 Test 回归

```sh
# 工具自检 + 可选应用冒烟；未设置应用 URL 时明确跳过应用用例。
npm --prefix tests/browser test

# 仅访问已经启动的指定环境，不会自动启动完整产品。
PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173 npm --prefix tests/browser run test:app

# 定向运行、调试及查看报告。
npm --prefix tests/browser test -- --project=tooling
npm --prefix tests/browser run test:smoke -- --headed
npm --prefix tests/browser run report
```

应用冒烟只验证 HTTP 导航、`#app` 挂载及挂载期间未捕获的页面脚本异常，不验证登录成功或任何业务流程。`PLAYWRIGHT_APP_PATH` 可指定入口路径，例如 `/#/login`。

`playwright.config.mjs` 使用单 worker，默认不重试，CI 重试一次。终端使用 dot 简短报告，HTML 报告保存在 `output/report/` 且不会自动打开。成功用例不保留截图、trace；失败时保留截图及 trace 到 `output/test-results/`，默认不录视频。失败后先查看断言和错误摘要，需要时再查看对应截图、trace。

新增业务回归时，将用例放在 `specs/`，并在配置中为实际项目增加明确的 `testMatch`；不要让应用用例误入工具自检项目。可按缺陷号建立文件，如 `tapd-1077724.spec.mjs`。优先 `getByRole/getByLabel` 等稳定定位，确有必要才给业务组件补 `data-testid`。回归必须包含能在修复前失败、修复后通过的行为断言；纯后端问题优先 Python 定向测试。

## 登录状态和输出

确需复用登录状态时，使用测试账号手动登录并保存到被忽略的 `.auth/`：

```sh
mkdir -p tests/browser/.auth
umask 077
npm --prefix tests/browser run cli -- -s=login open http://127.0.0.1:5173 --headed
# 在独立浏览器中完成登录后保存；路径相对 tests/browser。
npm --prefix tests/browser run cli -- -s=login state-save .auth/local.json
npm --prefix tests/browser run cli -- -s=login close
PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173 PLAYWRIGHT_STORAGE_STATE=.auth/local.json npm --prefix tests/browser run test:app
```

`.auth/`、`output/`、CLI 临时输出、`.env*` 和 `node_modules/` 均被本目录 `.gitignore` 排除；`package-lock.json` 单独纳入版本管理。登录状态、快照、请求详情、截图和 trace 可能包含凭据或业务数据，不提交这些产物，也不要直接把原始内容贴到 TAPD 或公开报告。

## 参考

- [Playwright CLI](https://playwright.dev/docs/getting-started-cli)
- [Playwright Test 配置](https://playwright.dev/docs/test-configuration)
- [命令行运行测试](https://playwright.dev/docs/test-cli)

## 个人改密初始密码策略回归

```sh
npm --prefix tests/browser test -- --config=password.config.mjs
```

需要先安装 `frontend` 依赖。独立 Vite 夹具监听 `127.0.0.1:4208`，加载当前 checkout 的真实 `PwdForm.vue`、`userApi` 和 HTTP 请求封装，替换会话/Store 边界，并通过 Playwright 拦截改密响应。覆盖中英文策略拒绝提示、保留表单、修改后重试成功、允许保存及网络失败提示。测试使用合成密码，不访问业务数据库；它不验证真实系统参数保存、鉴权、数据库事务或重新登录。

后端对应离线测试为 `backend/tests/test_initial_password_policy.py`，提取实际函数并替换配置、用户和 Session 边界，验证开启/关闭策略、普通用户/管理员、旧密码与格式校验、拒绝时不写入。真实环境验收仍需在隔离账号上完成“开启策略 → 改密拒绝 → 合法改密 → 重新登录”。

## 菜单语言与切换账号回归

```sh
npm --prefix tests/browser test -- --config=menu-language.config.mjs
```

需要 Node.js 20+、本机 Chrome 及已安装的 `frontend` 依赖。独立 Vite 夹具仅监听
`127.0.0.1:4217`，加载当前 checkout 的真实静态/动态路由、用户 Store、i18n、
`Menu.vue` 和 `MenuItem.vue`，替换账号 API、缓存、页面内容及导航守卫。
测试模拟英语账号退出后另一账号登录，覆盖五种语言的普通导航、设置子菜单、
切回英语、管理员菜单即时切换语言、普通成员的动态菜单过滤及扩展直接标题兼容。
账号均为合成数据，不连接业务后端；本测试不替代真实登录、权限鉴权、xpack 路由或完整布局验收。

## 欢迎语与恢复默认回归

```sh
npm --prefix tests/browser test -- --config=welcome-language.config.mjs
```

独立 Vite 夹具监听 `127.0.0.1:4218`，需要已安装的前端依赖、Node.js 20+ 和本机 Chrome。
加载真实助手入口、设置组件、五种语言及聊天页的欢迎区域模板和相关 computed 声明；
隔离聊天记录、查询执行等无关生命周期，用合成会话及内存保存接口替代账号和服务端边界。
覆盖基础／高级助手浮窗与全屏、页面嵌入和普通问数首页的默认值、空值、旧版已翻译默认值、
自定义文案，以及两个设置页恢复默认、保存空字符串、重新打开、切换语言和再次编辑。
外观设置分别覆盖平台区域和登录区域的恢复默认；登录页保留真实欢迎区域模板和 computed，
隔离登录表单及认证生命周期，验证登录欢迎语预览、保存、显示开关及旧版默认文案兼容。
不访问业务数据库或 LLM，不替代完整 SDK 握手、真实鉴权和持久化验收。
后端 `tests/test_assistant_welcome_defaults.py` 提取真实 Schema 和保存函数，验证空字符串覆盖、
省略字段保留、会话提交和缓存失效；它同样隔离鉴权与数据库。
