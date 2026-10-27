import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(fileURLToPath(import.meta.url))
const frontend = path.resolve(root, '../../../../frontend')
const require = createRequire(path.join(frontend, 'package.json'))
const { createServer } = await import(require.resolve('vite'))
const { default: vue } = await import(require.resolve('@vitejs/plugin-vue'))
const { default: svg } = await import(require.resolve('vite-svg-loader'))
const bridge = path.join(root, 'bridge.mjs')
const server = await createServer({
  configFile: false,
  root,
  cacheDir: path.resolve(root, '../../output/menu-language-vite'),
  plugins: [
    {
      name: 'isolate-pages',
      enforce: 'pre',
      resolveId(id, importer) {
        if ((id.endsWith('.vue') && importer?.includes('/src/router/')) ||
            (id === './watch' && importer?.endsWith('/router/index.ts'))) {
          return path.join(root, 'route-stub.mjs')
        }
      }
    },
    vue(),
    svg()
  ],
  resolve: { alias: [
    ...['@/api/login', '@/utils/useCache', '@/utils/utils'].map(find => ({ find, replacement: bridge })),
    { find: '@', replacement: path.join(frontend, 'src') },
    ...['vue', 'vue-router', 'vue-i18n', 'pinia', 'element-plus-secondary', 'mitt'].map(name => ({
      find: name, replacement: path.join(frontend, 'node_modules', name)
    }))
  ] },
  server: { host: '127.0.0.1', port: 4217, strictPort: true, fs: { allow: [root, frontend] } }
})
await server.listen()
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, async () => { await server.close(); process.exit() })
}
