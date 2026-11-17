import { createApp } from "vue";
import { createPinia } from "pinia";
import { createI18n } from "vue-i18n";
import ElementPlus, { ElMessage } from "element-plus-secondary";
import "element-plus-secondary/dist/index.css";
import "@/style.less";
import Model from "@/views/system/model/Model.vue";
import zh from "@/i18n/zh-CN.json";
window.ElMessage = ElMessage;
createApp(Model)
  .use(createPinia())
  .use(ElementPlus)
  .use(
    createI18n({ legacy: false, locale: "zh-CN", messages: { "zh-CN": zh } }),
  )
  .mount("#app");
