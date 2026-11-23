import { createApp, h, ref } from 'vue'
import { createI18n } from 'vue-i18n'
import ElementPlus, { ElMessage } from 'element-plus-secondary'
import 'element-plus-secondary/dist/index.css'
import Handler from '@/views/login/xpack/Handler.vue'
import Sync from '@/views/system/user/SyncUserDing.vue'
import zh from '@/i18n/zh-CN.json'
import en from '@/i18n/en.json'
window.ElMessage = ElMessage
window.LicenseGenerator = { getLicense: () => ({ status: 'valid' }) }
createApp({ setup() {
  const loading = ref(true)
  const sync = ref()
  const isSync = new URLSearchParams(location.search).get('view') === 'sync'
  return () => isSync ? h('div', [
    h('button', { onClick: () => sync.value.open(6, 'user.wecom') }, 'Open sync'), h(Sync, { ref: sync }),
  ]) : h('div', [
    h('p', { role: 'status' }, loading.value ? 'login loading' : 'login ready'),
    h(Handler, { loading: loading.value, 'onUpdate:loading': v => { loading.value = v } }),
  ])
}}).use(ElementPlus).use(createI18n({ legacy: false, locale: new URLSearchParams(location.search).get('lang') || 'zh-CN', messages: { 'zh-CN': zh, en } })).mount('#app')
