import { ElMessage } from "element-plus-secondary";
window.ElMessage = ElMessage;
import { createApp, h, ref, nextTick } from "vue";
import { createI18n } from "vue-i18n";
import ElementPlus from "element-plus-secondary";
import "element-plus-secondary/dist/index.css";
import Form from "@/views/system/model/ModelForm.vue";
import zh from "@/i18n/zh-CN.json";
import { get_supplier, supplierList } from "@/entity/supplier";
const form = ref();
const visible = ref(true);
window.testSuppliers = supplierList.map(({ id, name }) => ({ id, name }));
window.selectTestSupplier = (id) => form.value.supplierChang(get_supplier(id));
window.editTestSupplier = (item) => form.value.initForm(item);
createApp({
  setup() {
    return () =>
      h("div", [
        visible.value
          ? h(Form, {
              ref: form,
              onSubmit: (data) => (window.savedModel = data),
              activeName: "通用OpenAI",
              editModel: true,
            })
          : null,
        h(
          "button",
          { onClick: () => (visible.value = !visible.value) },
          "Toggle form",
        ),
        h("button", { onClick: () => form.value.submitModel() }, "Save"),
        h(
          "button",
          {
            onClick: async () => {
              await nextTick();
              form.value.supplierChang(get_supplier(15));
            },
          },
          "New generic",
        ),
        h(
          "button",
          {
            onClick: () =>
              form.value.initForm({
                id: "1",
                supplier: 15,
                name: "Synthetic",
                base_model: "legacy-custom",
                model_type: 0,
                api_domain: "http://127.0.0.1:4232/v1",
                api_key: "",
                config_list: [
                  { key: "temperature", name: "temperature", val: 0.33 },
                ],
                protocol: 1,
              }),
          },
          "Edit legacy",
        ),
      ]);
  },
})
  .use(ElementPlus)
  .use(
    createI18n({ legacy: false, locale: "zh-CN", messages: { "zh-CN": zh } }),
  )
  .mount("#app");
