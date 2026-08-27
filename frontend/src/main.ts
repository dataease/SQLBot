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

// import 'element-plus/dist/index.css'
cssHasPseudo(document)

function supportsFlexGap() {
  const flex = document.createElement('div')

  flex.style.display = 'flex'
  flex.style.flexDirection = 'column'
  flex.style.rowGap = '1px'

  const child1 = document.createElement('div')
  const child2 = document.createElement('div')

  child1.style.height = '1px'
  child2.style.height = '1px'

  flex.appendChild(child1)
  flex.appendChild(child2)

  document.body.appendChild(flex)

  const isSupported = flex.scrollHeight === 3

  document.body.removeChild(flex)

  return isSupported
}

document.documentElement.setAttribute('data-no-flex-gap', String(!supportsFlexGap()))

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(i18n)
app.use(VueDOMPurifyHTML)
app.mount('#app')
