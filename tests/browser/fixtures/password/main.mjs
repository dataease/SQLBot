import { createApp, h, ref } from 'vue'
import { createI18n } from 'vue-i18n'
import ElementPlus, { ElMessage } from 'element-plus-secondary'
import 'element-plus-secondary/dist/index.css'
import PasswordForm from 'password-form'
import zh from '@/i18n/zh-CN.json'
import en from '@/i18n/en.json'
window.ElMessage = ElMessage
const saved = ref(false)
const form = ref()
createApp({ render: () => saved.value ? h('p', { role: 'status' }, 'saved') : h('div', [
  h(PasswordForm, { ref: form, onPwdSaved: () => { saved.value = true } }),
  h('button', { onClick: () => form.value.submit() }, 'Submit')
]) }).use(ElementPlus).use(createI18n({ legacy: false, locale: new URLSearchParams(location.search).get('lang') || 'zh-CN', messages: { 'zh-CN': zh, en } })).mount('#app')
