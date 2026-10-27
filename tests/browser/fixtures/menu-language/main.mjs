import { createApp, h, nextTick } from 'vue'
import { i18n } from '@/i18n'
import { store } from '@/stores'
import { useUserStore } from '@/stores/user'
import router from '@/router'
import { generateDynamicRouters } from '@/router/dynamic'
import Menu from '@/components/layout/Menu.vue'
import { selectAccount } from './bridge.mjs'

const user = useUserStore()
// Extension routes are registered before mounting the layout, as in the app.
router.addRoute({
  path: '/extension', name: 'extension', component: { render: () => null },
  meta: { title: 'Extension title', iconActive: 'chat', iconDeActive: 'noChat' }
})
async function signIn(account) {
  selectAccount(account)
  await user.login({ username: 'synthetic', password: 'synthetic' })
  await user.info()
  generateDynamicRouters(router)
  await router.push('/chat/index')
  await nextTick()
}
await signIn({ id: 41, language: 'en', weight: 1 })
const app = createApp({ render: () => h('main', [
  h('p', { id: 'language' }, user.getLanguage),
  h('h1', i18n.global.t('menu.Data Q&A')),
  router.currentRoute.value.path !== '/login' ? h(Menu) : null
]) })
app.use(store).use(i18n).use(router).mount('#app')
window.menuFixture = {
  signIn,
  async signOut() { await user.logout(); await router.push('/login'); await nextTick() },
  async setLanguage(language) { user.setLanguage(language); await nextTick() },
  async go(path) { await router.push(path); await nextTick() }
}
