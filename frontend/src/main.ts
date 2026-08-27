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
app.use(router)
app.use(i18n)
app.use(VueDOMPurifyHTML)
app.mount('#app')
