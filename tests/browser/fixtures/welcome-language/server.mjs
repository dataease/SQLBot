import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(fileURLToPath(import.meta.url))
const frontend = path.resolve(root, '../../../../frontend')
const require = createRequire(path.join(frontend, 'package.json'))
const { createServer } = await import(require.resolve('vite'))
const { default: vue } = await import(require.resolve('@vitejs/plugin-vue'))
const { default: svg } = await import(require.resolve('vite-svg-loader'))
const ts = require('typescript')
const bridge = path.join(root, 'bridge.mjs')
function welcomeDeclarations(source, names) {
  const script = source.split(/<script[^>]*>/)[1].split('</script>')[0]
  const ast = ts.createSourceFile('welcome.ts', script, ts.ScriptTarget.Latest, true)
  return ast.statements.filter(n =>
    n.declarationList?.declarations.some(d => names.includes(d.name.getText(ast))) ||
    (ts.isImportDeclaration(n) && n.moduleSpecifier.text === '@/i18n/welcome')
  ).map(n => n.getText(ast)).join('\n')
}
const server = await createServer({
  configFile: false, root, cacheDir: '../../output/welcome-language-vite',
  plugins: [
    {
      name: 'isolate-chat-welcome', enforce: 'pre',
      transform(source, id) {
        if (id.endsWith('/views/login/index.vue')) {
          const start = source.indexOf('<div v-if="appearanceStore.getShowSlogan"')
          const end = source.indexOf('<div class="login-form">', start)
          if (start < 0 || end < 0) throw new Error('Login welcome seam changed')
          return `<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
const appearanceStore = useAppearanceStoreWithOut()
const { t } = useI18n()
${welcomeDeclarations(source, ['loginSlogan'])}
</script><template>${source.slice(start, end)}</template>`
        }
        if (!id.endsWith('/views/chat/index.vue')) return
        // Keep the actual welcome template and its production computed declarations.
        // Exclude query execution, charts, history and unrelated chat lifecycle hooks.
        const start = source.indexOf('<div class="welcome-content flex-gap-fallback flex-col">')
        const end = source.indexOf('</div>\n        </div>\n        <div v-else-if', start)
        if (start < 0 || end < 0) throw new Error('Chat welcome seam changed')
        const declarations = welcomeDeclarations(source, ['isCompletePage', 'pageWelcome', 'pageWelcomeDesc'])
        return `<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAssistantStore } from '@/stores/assistant'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
defineProps(['welcome','welcomeDesc','logoAssistant','pageEmbedded','appName'])
const assistantStore = useAssistantStore()
const appearanceStore = useAppearanceStoreWithOut()
const { t } = useI18n()
const loginBg = null, selectAssistantDs = true, currentChatId = undefined
const createNewChatSimple = () => {}
${declarations}
</script><template>${source.slice(start, end + 6)}</template>`
      }
    }, vue(), svg()
  ],
  optimizeDeps: { noDiscovery: true, include: ['vue', 'vue-router', 'vue-i18n', 'element-plus-secondary', 'lodash-es', 'element-resize-detector', 'dompurify'] },
  resolve: { alias: [
    ...['@/stores/assistant', '@/stores/user', '@/stores/appearance', '@/utils/utils', '@/utils/useCache', '@/utils/request'].map(find => ({ find, replacement: bridge })),
    { find: '@', replacement: path.join(frontend, 'src') },
    ...['vue', 'vue-router', 'vue-i18n', 'pinia', 'element-plus-secondary', 'lodash-es', 'element-resize-detector', 'dompurify'].map(name => ({ find: name, replacement: path.join(frontend, 'node_modules', name) }))
  ] },
  server: { host: '127.0.0.1', port: 4218, strictPort: true, fs: { allow: [root, frontend] } }
})
await server.listen()
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, async () => { await server.close(); process.exit() })
