<script lang="ts" setup>
import { ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const paramsRef = ref()
const paramsForm = reactive({
  name: '',
  key: '',
  val: '',
  id: '',
})

const rules = {
  name: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('model.display_name'),
      trigger: 'blur',
    },
  ],
  key: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('model.parameters'),
      trigger: 'blur',
    },
  ],
  val: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('model.parameter_value'),
      trigger: 'blur',
    },
  ],
}

const initForm = (item: any) => {
  if (item) {
    const formData = { ...item }
    // 如果val是对象，转换为JSON字符串
    if (typeof formData.val === 'object' && formData.val !== null) {
      formData.val = JSON.stringify(formData.val)
    }
    Object.assign(paramsForm, formData)
  }
  if (!paramsForm.id) {
    paramsForm.id = `${+new Date()}`
  }
  paramsRef.value.clearValidate()
}

const emits = defineEmits(['submit'])

const submit = () => {
  paramsRef.value.validate((res: any) => {
    if (res) {
      const submitData = { ...paramsForm }
      // 尝试将JSON字符串转回对象
      try {
        const parsed = JSON.parse(submitData.val)
        submitData.val = parsed
      } catch (e) {
        // 如果不是有效JSON，保持原字符串
      }
      emits('submit', submitData)
    }
  })
}

const close = () => {
  paramsForm.name = ''
  paramsForm.key = ''
  paramsForm.val = ''
  paramsForm.id = ''
}
defineExpose({
  initForm,
  submit,
  close,
})
</script>

<template>
  <div class="params-form">
    <el-form
      ref="paramsRef"
      :rules="rules"
      label-position="top"
      :model="paramsForm"
      style="width: 100%"
      @submit.prevent
    >
      <el-form-item prop="key" :label="$t('model.parameters')">
        <el-input
          v-model="paramsForm.key"
          clearable
          :placeholder="$t('datasource.please_enter') + $t('common.empty') + $t('model.parameters')"
        />
      </el-form-item>
      <el-form-item prop="name" :label="$t('model.display_name')">
        <el-input
          v-model="paramsForm.name"
          clearable
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('model.display_name')
          "
        />
      </el-form-item>
      <el-form-item prop="val" :label="$t('model.parameter_value')">
        <el-input
          v-model="paramsForm.val"
          clearable
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('model.parameter_value')
          "
        />
      </el-form-item>
    </el-form>
  </div>
</template>

<style lang="less" scoped>
.params-form {
  .ed-form-item--default {
    margin-bottom: 16px;

    &.is-error {
      margin-bottom: 40px;
    }
  }

  .ed-input-number {
    width: 100%;
  }
}
</style>
