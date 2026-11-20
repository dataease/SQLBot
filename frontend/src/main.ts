import 'core-js/features/object/has-own'
// @ts-ignore: css-has-pseudo/browser lacks official type definitions
import cssHasPseudo from 'css-has-pseudo/browser'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.less'
import App from './App.vue'
import router from './router'
import { i18n } from './i18n'
import VueDOMPurifyHTML from 'vue-dompurify-html'
import { isSupportFlexGap } from './utils/utils'

// import 'element-plus/dist/index.css'
cssHasPseudo(document)

isSupportFlexGap()

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
// Binding callbacks bypass the ordinary login component and never replace its token.
const bindingState = new URLSearchParams(location.search).get('state') || ''
if (/^sqlbot_bind_[A-Za-z0-9_-]{40,64}$/.test(bindingState)) {
  location.hash = '/account/binding-callback'
}
app.use(router)
app.use(i18n)
app.use(VueDOMPurifyHTML)
app.mount('#app')
