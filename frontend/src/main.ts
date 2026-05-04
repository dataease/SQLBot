import { createApp } from 'vue'
import { createPinia } from 'pinia'
import '@/styles/design-tokens.less'
import '@/styles/theme-presets.less'
import './style.less'
import { initUiThemeFromStorage } from '@/utils/uiTheme'

initUiThemeFromStorage()
import App from './App.vue'
import router from './router'
import { i18n } from './i18n'
import VueDOMPurifyHTML from 'vue-dompurify-html'

// import 'element-plus/dist/index.css'
const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(i18n)
app.use(VueDOMPurifyHTML)
app.mount('#app')
