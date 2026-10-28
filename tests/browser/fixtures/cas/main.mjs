import { createApp, h, ref } from 'vue'
import { createI18n } from 'vue-i18n'
import ElementPlus from 'element-plus-secondary'
import 'element-plus-secondary/dist/index.css'
import Cas from 'cas-form'
import zh from '@/i18n/zh-CN.json'
import en from '@/i18n/en.json'
const form = ref()
createApp({ render: () => h('div', [h(Cas, { ref: form }),
  h('button', { onClick: () => form.value.edit() }, 'Open CAS')
]) }).use(ElementPlus).use(createI18n({ legacy: false, locale: 'zh-CN', messages: { 'zh-CN': zh, en } })).mount('#app')
