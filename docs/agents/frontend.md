# 前端 Agent 说明

## 技术与运行

- 技术栈：Vue 3、TypeScript strict mode、Vite、Pinia、Vue Router、Element Plus / `element-plus-secondary`、Less。
- 路径别名 `@/` 指向 `frontend/src/`。
- 构建目标是 Chrome 81，并启用 Vite legacy 插件；不要只按最新浏览器能力选择 API。
- 常用命令：

```bash
cd frontend
npm run dev
npm run build
```

`dev` 和 `build` 都会先运行 `vue-tsc -b`。依赖变更只手动修改 `package.json`；`package-lock.json` 由 npm 命令自动生成且不入库，不要手工编辑或强制加入提交，也不要提交私有 registry 配置。

## 代码组织

| 内容 | 位置 |
| --- | --- |
| 后端接口封装 | `src/api/<domain>.ts` |
| 仅单个业务域使用的类型和模型 | 跟随对应 `src/api/<domain>.ts` |
| 跨页面/跨模块共享实体与配置 | `src/entity/` |
| Pinia 状态 | `src/stores/<domain>.ts` |
| 路由 | `src/router/index.ts`、`dynamic.ts`、`watch.ts` |
| 页面级视图 | `src/views/<domain>/` |
| 业务域私有子组件 | 对应 `src/views/<domain>/` 子目录 |
| 跨业务复用组件 | `src/components/<component>/` |
| 工具函数 | `src/utils/` |
| 用户可见文案 | `src/i18n/` 五种语言 JSON |

组件目录常使用 `index.ts` 加 `src/` 的形式。新增复用组件时优先参考相邻组件结构；仅单个页面使用的组件不要提前提升到全局 `components/`。

## API 调用

- 不要在视图组件中直接使用 axios；统一通过 `@/utils/request.ts` 的 `request` 实例。
- 新接口放入对应 `src/api/<domain>.ts`，导出类似 `xxxApi` 的对象，并复用既有命名风格。
- 普通请求使用 `request.get/post/put/delete/patch`；SSE 使用 `request.fetchStream` 并传入 `AbortController`。
- 不要手工添加认证 token、助手 token、证书、语言或 xpack 静态资源头。普通请求的头由 request interceptor 统一处理；SSE 走 `request.fetchStream`（原生 fetch，不经过 axios interceptor），头部在 `fetchStream` 内单独拼装（当前不含 `Accept-Language`），新增请求头时两条路径都要核对。
- 下载类 blob 请求沿用：

```ts
request.get('/path', {
  responseType: 'blob',
  requestOptions: { customError: true },
})
```

- 后端统一响应中 `code === 0` 时 interceptor 会返回 `data`；调用方不要重复解包。
- 外部请求失败需要自定义处理时使用 `customError` 或 `silent`，不要绕开统一请求封装。

## 类型

- 新增代码优先使用具体 interface/type 或从 API 模块导出的模型；不要扩大 `any` 的使用范围。
- 后端返回结构复杂且已有转换函数时，参考 `src/api/chat.ts` 的模型类和 `toXxx` 转换函数模式。
- 共享类型放 `src/entity/`，业务专属类型跟随业务模块，避免相同 DTO 在多个视图中重复声明。
- 修改类型后必须运行 `npm run build`，让 `vue-tsc` 检查模板和引用。

## 状态管理

- 新 store 放 `src/stores/<domain>.ts`，使用 Pinia options API 风格：`state`、`getters`、`actions`。
- 为 state 定义 interface；getter 命名沿用 `getXxx`，action 命名表达业务行为。
- 需要在 setup 外使用的 store，参考现有模块通过 `stores/index.ts` 的 `store` 实例导出包装函数。
- 用户、语言、工作空间、助手上下文等状态已有 store；不要在组件里复制派生状态或直接改缓存键。

## 路由与权限

- 静态路由主要在 `src/router/index.ts`；由许可证或管理员能力控制的动态路由在 `dynamic.ts` 与 xpack 的 `LicenseGenerator.generateRouters` 中处理。
- 修改 `watch.ts` 时必须核对：
  - 普通登录和管理员登录白名单；
  - `/assistant`、`/embeddedPage`、`/embeddedCommon`、`/401` 助手白名单；
  - `userStore.isAdmin` 与 `isSpaceAdmin` 的路由差异；
  - xpack 静态脚本加载失败路径：`LicenseGenerator` 是无类型声明的 window 全局，登录/改密加密（`sqlbotEncrypt`）和动态路由注册都硬依赖它，脚本加载失败只提示并中断导航，没有降级。
- 新路由必须配置名称、标题 i18n 和正确父布局；不要绕过已有访问控制。

## 视图、组件与样式

- 页面组件使用 Vue 3 组合式 API；新组件优先使用 `<script setup lang="ts">`。
- Element Plus / `element-plus-secondary` 组件由插件自动导入；除非相邻代码已有显式导入，否则不要添加不必要的组件导入。
- 样式优先使用 scoped Less，并复用邻近页面的布局类、间距类和 `flex-gap-fallback` 模式。
- 只在有全局设计理由时修改 `src/style.less` 或跨页面公共样式；不要用行内样式解决可复用布局问题。
- 图表逻辑优先复用 `src/views/chat/component/` 和 dashboard 现有封装，不要直接散落 G2/S2 配置。

## 国际化与安全

- 用户可见文案必须使用 vue-i18n，并同步：
  - `en.json`
  - `zh-CN.json`
  - `zh-TW.json`
  - `ko-KR.json`
  - `th-TH.json`
- 新增语言时按 `docs/agents/i18n.md` 的完整链路检查，不要只添加 JSON 或漏掉文档更新。
- 不要在组件中硬编码新文案；枚举和 supplier 配置可保留 i18n key。
- 渲染模型输出或第三方内容时走既有 markdown/XSS 工具与安全指令；不要新增未净化的 `v-html`。
- 不要削弱助手 postMessage 证书流程、请求头、token 存储和嵌入白名单逻辑。

## 验证

```bash
cd frontend
npm run build
```

只检查改动文件时可运行：

```bash
cd frontend
npx eslint <changed-file...> --fix
```

不要默认执行 `npm run lint`，它会修复整个前端，容易产生无关变更。当前没有独立前端单测框架；跨前端结构或安全约定由 `backend/tests/` 中的守卫测试保护，必要时新增或更新对应守卫。
