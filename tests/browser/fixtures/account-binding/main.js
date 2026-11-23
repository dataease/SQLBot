import { createApp } from 'vue';
import { createI18n } from 'vue-i18n';
import ElementPlus from 'element-plus-secondary';
import 'element-plus-secondary/dist/index.css';
import '@/style.less';
import Account from '@/views/account/AccountBinding.vue';
import Callback from '@/views/account/BindingCallback.vue';
import zh from '@/i18n/zh-CN.json';
// Same default green palette applied by the real appearance initialization.
document.documentElement.style.setProperty('--ed-color-primary', '#1cba90');
document.documentElement.style.setProperty('--ed-color-primary-light-5', '#77d6bc');
document.documentElement.style.setProperty('--ed-color-primary-light-3', '#3ec5a1');
const app = createApp(new URLSearchParams(location.search).has('state') ? Callback : Account);
app
  .use(createI18n({ legacy: false, locale: 'zh-CN', messages: { 'zh-CN': zh } }))
  .use(ElementPlus).mount('#app');

window.bindingFixture.unmount = () => app.unmount();
