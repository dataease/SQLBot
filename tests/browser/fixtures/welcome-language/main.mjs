import { createApp, h, ref, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import ElementPlus from 'element-plus-secondary'
import 'element-plus-secondary/dist/index.css'
import { i18n } from '@/i18n'
import SetUi from '@/views/system/embedded/SetUi.vue'
import Appearance from '@/views/system/appearance/index.vue'
import EmbeddedPage from '@/views/embedded/page.vue'
import Assistant from '@/views/embedded/index.vue'
import Chat from '@/views/chat/index.vue'
import Login from '@/views/login/index.vue'
import { db, assistant, appearance } from './bridge.mjs'

const view = ref(''), generation = ref(0), editor = ref()
const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
await router.push('/embeddedPage?id=fixture&type=0&lang=zh-CN')
createApp({ render: () => h('main', [
  view.value === 'settings' ? h(SetUi, { ref: editor, key: generation.value }) :
  view.value === 'appearance' ? h(Appearance, { key: generation.value }) :
  view.value === 'float' ? h(Assistant, { key: generation.value }) :
  view.value === 'page' ? h(EmbeddedPage, { key: generation.value }) :
  view.value === 'login' ? h(Login, { key: generation.value }) :
  view.value === 'chat' ? h(Chat, { key: generation.value }) : null
]) }).use(i18n).use(router).use(ElementPlus).mount('#app')

window.welcomeFixture = {
  saved: db.saved,
  async language(locale) { i18n.global.locale.value = locale; await nextTick() },
  async editor(kind, config = {}) {
    view.value = ''; await nextTick()
    if (kind === 'settings') db.assistant = { ...config }
    else db.appearance = Object.entries(config).map(([pkey, pval]) => ({ pkey, pval }))
    view.value = kind; generation.value++; await nextTick()
    if (kind === 'settings') editor.value.open({ id: '42', name: 'Fixture', configuration: JSON.stringify(db.assistant) })
    await nextTick()
  },
  async reopen() {
    if (view.value === 'settings') editor.value.open({ id: '42', name: 'Fixture', configuration: JSON.stringify(db.assistant) })
    else { view.value = ''; await nextTick(); view.value = 'appearance'; generation.value++ }
    await nextTick()
  },
  async render(kind, type, config = {}) {
    view.value = ''; await nextTick()
    assistant.assistant = kind !== 'chat'; assistant.type = type
    db.appearance = Object.entries(config).map(([pkey, pval]) => ({ pkey, pval }))
    await appearance.setAppearance()
    await router.push(`/embeddedPage?id=fixture&type=${type}&lang=${i18n.global.locale.value}`)
    view.value = kind; generation.value++; await nextTick()
    if (kind === 'chat' || kind === 'login') return
    window.dispatchEvent(new MessageEvent('message', { data: {
      eventName: kind === 'float' ? 'sqlbot_assistant_event' : 'sqlbot_embedded_event',
      messageId: 'fixture', type, busi: 'certificate', certificate: 'synthetic',
      sqlbot_embedded_token: 'synthetic', sqlbot_origin_data: { configuration: JSON.stringify(config) }
    } }))
    await nextTick(); await nextTick()
  }
}
