<script lang="ts" setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElLoading } from 'element-plus-secondary'
import { request } from '@/utils/request'
import { useI18n } from 'vue-i18n'
import type { FormInstance, FormRules } from 'element-plus-secondary'
import { settingMapping } from './common/SettingTemplate'
const { t } = useI18n()
const dialogVisible = ref(false)
const loadingInstance = ref<ReturnType<typeof ElLoading.service> | null>(null)
const platformForm = ref<FormInstance>()

const state = reactive({
  form: reactive<any>({}),
  settingList: [] as any[],
})
const origin = ref(6)
const id = ref()
const rule = reactive<FormRules>({})
const formTitle = ref('')
const busiMapping = {
  6: 'wecom',
  7: 'dingtalk',
  8: 'lark',
  9: 'larksuite',
} as any
const initForm = (row: any) => {
  state.settingList.forEach((item: any) => {
    const key = item.realKey
    rule[key] = [
      {
        required: true,
        message: t('common.require'),
        trigger: 'blur',
      },
      {
        min: 5,
        max: 255,
        message: t('common.input_limit', [5, 255]),
        trigger: 'blur',
      },
    ]
    state.form[key] = row[key]
  })
}
const edit = (row: any) => {
  state.settingList = settingMapping[row.type]
  initForm(row)
  origin.value = row.type
  formTitle.value = row.title
  if (row?.id) {
    id.value = row.id
  }
  dialogVisible.value = true
}

const emits = defineEmits(['saved'])
const submitForm = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  await formEl.validate((valid) => {
    if (valid) {
      const param = { ...state.form }

      const data = {
        id: origin.value,
        type: origin.value,
        name: busiMapping[origin.value],
        config: JSON.stringify(param),
      }
      const method = id.value
        ? request.put('/system/authentication', data, { requestOptions: { silent: true } })
        : request.post('/system/authentication', data, { requestOptions: { silent: true } })
      showLoading()
      method
        .then((res) => {
          if (!res.msg) {
            ElMessage.success(t('common.save_success'))
            emits('saved')
            reset()
          }
        })
        .catch((e: any) => {
          if (
            e.message?.startsWith('sqlbot_authentication_connect_error') ||
            e.response?.data?.startsWith('sqlbot_authentication_connect_error')
          ) {
            emits('saved')
            ElMessage.error(t('ds.connection_failed'))
          }
        })
        .finally(() => {
          closeLoading()
        })
    }
  })
}

const resetForm = (formEl: FormInstance | undefined) => {
  if (!formEl) return
  formEl.resetFields()
  dialogVisible.value = false
  id.value = null
  origin.value = 6
  formTitle.value = ''
  state.settingList = []
  const keys = Object.keys(rule)
  keys.forEach((key: string) => delete rule[key])
}

const reset = () => {
  resetForm(platformForm.value)
}

const showLoading = () => {
  loadingInstance.value = ElLoading.service({
    target: '.platform-info-drawer',
  })
}
const closeLoading = () => {
  loadingInstance.value?.close()
}

const validate = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  await formEl.validate((valid) => {
    if (!valid) {
      return
    }
    const url = '/system/authentication/status'
    const config_data = state.form
    const data = {
      type: origin.value,
      name: busiMapping[origin.value],
      config: JSON.stringify(config_data),
    }
    showLoading()
    request
      .patch(url, data)
      .then((res) => {
        if (res) {
          ElMessage.success(t('ds.connection_success'))
        } else {
          ElMessage.error(t('ds.connection_failed'))
        }
      })
      .finally(() => {
        closeLoading()
        emits('saved')
      })
  })
}

defineExpose({
  edit,
})
</script>

<template>
  <el-drawer
    v-model="dialogVisible"
    :title="formTitle"
    modal-class="platform-info-drawer"
    size="600px"
    direction="rtl"
  >
    <el-form
      ref="platformForm"
      require-asterisk-position="right"
      :model="state.form"
      :rules="rule"
      label-width="80px"
      label-position="top"
    >
      <el-form-item
        v-for="setting in state.settingList"
        :key="setting.realKey"
        :label="setting.pkey"
        :prop="setting.realKey"
      >
        <el-input
          v-if="setting.type === 'password'"
          v-model="state.form[setting.realKey]"
          type="password"
          show-password
          :placeholder="t('common.please_input')"
        />
        <el-input
          v-else
          v-model="state.form[setting.realKey]"
          :placeholder="t('common.please_input')"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="resetForm(platformForm)">{{ t('common.cancel') }}</el-button>
        <el-button @click="validate(platformForm)">
          {{ t('ds.check') }}
        </el-button>
        <el-button type="primary" @click="submitForm(platformForm)">
          {{ t('common.save') }}
        </el-button>
      </span>
    </template>
  </el-drawer>
</template>

<style lang="less">
.platform-info-drawer {
  .ed-drawer__footer {
    height: 64px !important;
    padding: 16px 24px !important;
    .dialog-footer {
      height: 32px;
      line-height: 32px;
    }
  }
  .ed-form-item__label {
    line-height: 22px !important;
    height: 22px !important;
  }
}
</style>
<style lang="less" scoped>
.platform-info-drawer {
  .ed-form-item {
    margin-bottom: 16px;
  }
  .is-error {
    margin-bottom: 40px !important;
  }
  .input-with-select {
    .ed-input-group__prepend {
      width: 72px;
      background-color: #fff;
      padding: 0 20px;
      color: #1f2329;
      text-align: center;
      font-family: var(--de-custom_font, 'PingFang');
      font-size: 14px;
      font-style: normal;
      font-weight: 400;
      line-height: 22px;
    }
  }
}
</style>
