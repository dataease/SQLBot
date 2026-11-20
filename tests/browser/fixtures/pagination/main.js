import { createApp, ref, h } from 'vue';
import { createI18n } from 'vue-i18n';
import ElementPlus from 'element-plus-secondary';
import 'element-plus-secondary/dist/index.css';
import '@/style.less';
import Dialog from '@/views/system/workspace/AuthorizedWorkspaceDialog.vue';
import zh from '@/i18n/zh-CN.json';
createApp({
  components: { Dialog },
  setup() {
    const dialog = ref();
    const error = ref('');
    const open = async () => {
      error.value = '';
      try { await dialog.value.open('99'); } catch { error.value = 'load failed'; }
    };
    return () => h('div', [
      h('button', { onClick: open }, 'Open members'),
      h('p', { role: 'status' }, error.value),
      h(Dialog, { ref: dialog }),
    ]);
  },
}).use(createI18n({ legacy: false, locale: 'zh-CN', messages: { 'zh-CN': zh } }))
  .use(ElementPlus).mount('#app');
