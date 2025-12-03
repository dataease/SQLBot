<script lang="ts" setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElLoading } from 'element-plus-secondary'
import { useI18n } from 'vue-i18n'
import type { FormInstance, FormRules } from 'element-plus-secondary'
import { request } from '@/utils/request'
import { getSQLBotAddr } from '@/utils/utils'
const { t } = useI18n()
const dialogVisible = ref(false)
const loadingInstance = ref<ReturnType<typeof ElLoading.service> | null>(null)
const casForm = ref<FormInstance>()
const id = ref<number | null>(null)
interface CasForm {
  idpUri?: string
  casCallbackDomain?: string
  mapping?: string
}
const state = reactive({
  form: reactive<CasForm>({
    idpUri: '',
    casCallbackDomain: getSQLBotAddr(),
    mapping: '',
  }),
})
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-expect-error
const validateUrl = (rule, value, callback) => {
  const reg = new RegExp(/(http|https):\/\/([\w.]+\/?)\S*/)
  if (!reg.test(value)) {
    callback(new Error(t('authentication.incorrect_please_re_enter')))
  } else {
    callback()
  }
}
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-expect-error
const validateCbUrl = (rule, value, callback) => {
  const addr = getSQLBotAddr()
  if (value === addr || `${value}/` === addr) {
    callback()
  }
  callback(new Error(t('authentication.callback_domain_name_error')))
}
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-expect-error
const validateMapping = (rule, value, callback) => {
  if (!value) {
    callback()
  }
  if (value.startsWith('{') === false || value.endsWith('}') === false) {
    callback(new Error(t('authentication.in_json_format')))
    return
  }
  try {
    JSON.parse(value)
  } catch {
    callback(new Error(t('authentication.in_json_format')))
    return
  }
  callback()
}
const rule = reactive<FormRules>({
  idpUri: [
    {
      required: true,
      message: t('common.require'),
      trigger: 'blur',
    },
    {
      min: 10,
      max: 255,
      message: t('common.input_limit', [10, 255]),
      trigger: 'blur',
    },
    { required: true, validator: validateUrl, trigger: 'blur' },
  ],
  casCallbackDomain: [
    {
      required: true,
      message: t('common.require'),
      trigger: 'blur',
    },
    {
      min: 10,
      max: 255,
      message: t('common.input_limit', [10, 255]),
      trigger: 'blur',
    },
    { required: true, validator: validateCbUrl, trigger: 'blur' },
  ],
  mapping: [{ required: false, validator: validateMapping, trigger: 'blur' }],
})

const edit = () => {
  showLoading()
  request
    .get('/system/authentication/1')
    .then((res) => {
      if (!res?.config) {
        return
      }
      id.value = res.id
      const data = JSON.parse(res.config)
      const resData = data as Partial<CasForm>
      ;(Object.keys(resData) as (keyof CasForm)[]).forEach((key) => {
        const value = resData[key]
        if (value !== undefined) {
          state.form[key] = value as any
        }
      })
    })
    .finally(() => {
      closeLoading()
    })
  dialogVisible.value = true
}

const emits = defineEmits(['saved'])
const submitForm = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  await formEl.validate((valid) => {
    if (valid) {
      const param = { ...state.form }
      const data = {
        id: 1,
        type: 1,
        config: JSON.stringify(param),
        name: 'cas',
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
  id.value = null
  dialogVisible.value = false
}

const reset = () => {
  resetForm(casForm.value)
}

const showLoading = () => {
  loadingInstance.value = ElLoading.service({
    target: '.platform-info-drawer',
  })
}
const closeLoading = () => {
  loadingInstance.value?.close()
}

const validate = () => {
  const url = '/system/authentication/status'
  const config_data = state.form
  const data = {
    type: 1,
    name: 'cas',
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
}

defineExpose({
  edit,
})
</script>

<template>
  <el-drawer
    v-model="dialogVisible"
    :title="t('authentication.cas_settings')"
    modal-class="platform-info-drawer"
    size="600px"
    direction="rtl"
  >
    <el-form
      ref="casForm"
      require-asterisk-position="right"
      :model="state.form"
      :rules="rule"
      label-width="80px"
      label-position="top"
    >
      <el-form-item label="IdpUri" prop="idpUri">
        <el-input v-model="state.form.idpUri" :placeholder="t('common.please_input')" />
      </el-form-item>

      <el-form-item :label="t('authentication.callback_domain_name')" prop="casCallbackDomain">
        <el-input v-model="state.form.casCallbackDomain" :placeholder="t('common.please_input')" />
      </el-form-item>

      <el-form-item :label="t('authentication.field_mapping')" prop="mapping">
        <el-input
          v-model="state.form.mapping"
          :placeholder="t('authentication.field_mapping_placeholder')"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button secondary @click="resetForm(casForm)">{{ t('common.cancel') }}</el-button>
        <el-button secondary :disabled="!state.form.idpUri" @click="validate">
          {{ t('ds.test_connection') }}
        </el-button>
        <el-button type="primary" @click="submitForm(casForm)">
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
