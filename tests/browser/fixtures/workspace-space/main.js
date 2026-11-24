import { createApp, ref, h } from 'vue'
import { createI18n } from 'vue-i18n'
import ElementPlus, { ElMessage } from 'element-plus-secondary'
import 'element-plus-secondary/dist/index.css'
import '@/style.less'
import AddDialog from '@/views/system/workspace/AuthorizedWorkspaceDialogForModelAdd.vue'
import EditDialog from '@/views/system/workspace/AuthorizedWorkspaceDialogForModel.vue'
import zh from '@/i18n/zh-CN.json'

globalThis.ElMessage = ElMessage

createApp({
  setup() {
    const addDialog = ref()
    const editDialog = ref()
    return () =>
      h('div', [
        h('button', { onClick: () => addDialog.value.open('99') }, '打开新增授权'),
        h('button', { onClick: () => editDialog.value.open('99') }, '打开修改授权'),
        h(AddDialog, { ref: addDialog }),
        h(EditDialog, { ref: editDialog }),
      ])
  },
})
  .use(createI18n({ legacy: false, locale: 'zh-CN', messages: { 'zh-CN': zh } }))
  .use(ElementPlus)
  .mount('#app')
