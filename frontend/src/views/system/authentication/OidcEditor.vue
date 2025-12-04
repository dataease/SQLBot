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
const oidcForm = ref<FormInstance>()

const id = ref<number | null>(null)
const state = reactive({
  form: reactive<any>({
    client_id: '',
    client_secret: '',
    metadata_url: '',
    redirect_uri: getSQLBotAddr(),
    realm: '',
    scope: '',
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
const validateMapping = (rule, value, callback) => {
  if (!value) {
    callback()
  }
  try {
    JSON.parse(value)
  } catch (e: any) {
    console.error(e)
    callback(new Error(t('authentication.in_json_format')))
  }
  callback()
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
const rule = reactive<FormRules>({
  client_id: [
    {
      required: true,
      message: t('common.require'),
      trigger: 'blur',
    },
    {
      min: 2,
      max: 50,
      message: t('common.input_limit', [2, 50]),
      trigger: 'blur',
    },
  ],
  client_secret: [
    {
      required: true,
      message: t('common.require'),
      trigger: 'blur',
    },
    {
      min: 5,
      max: 50,
      message: t('common.input_limit', [5, 50]),
      trigger: 'blur',
    },
  ],
  redirect_uri: [
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
  metadata_url: [
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
  realm: [
    {
      required: false,
      message: t('common.require'),
      trigger: 'blur',
    },
    {
      min: 2,
      max: 50,
      message: t('common.input_limit', [2, 50]),
      trigger: 'blur',
    },
  ],
  scope: [
    {
      required: true,
      message: t('common.require'),
      trigger: 'blur',
    },
    {
      min: 2,
      max: 255,
      message: t('common.input_limit', [2, 255]),
      trigger: 'blur',
    },
  ],

  mapping: [{ required: false, validator: validateMapping, trigger: 'blur' }],
})

const edit = () => {
  showLoading()
  request
    .get('/system/authentication/2')
    .then((res) => {
      if (!res?.config) {
        return
      }
      id.value = res.id
      const data = JSON.parse(res.config)
      for (const key in data) {
        state.form[key] = data[key] as any
      }
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
        id: 2,
        type: 2,
        config: JSON.stringify(param),
        name: 'oidc',
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
  resetForm(oidcForm.value)
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
    type: 2,
    name: 'oidc',
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
    :title="t('authentication.oidc_settings')"
    modal-class="platform-info-drawer"
    size="600px"
    direction="rtl"
  >
    <el-form
      ref="oidcForm"
      require-asterisk-position="right"
      :model="state.form"
      :rules="rule"
      label-width="80px"
      label-position="top"
    >
      <el-form-item :label="t('authentication.client_id')" prop="client_id">
        <el-input v-model="state.form.client_id" :placeholder="t('common.please_input')" />
      </el-form-item>

      <el-form-item :label="t('authentication.client_secret')" prop="client_secret">
        <el-input
          v-model="state.form.client_secret"
          type="password"
          show-password
          :placeholder="t('common.please_input')"
        />
      </el-form-item>
      <el-form-item :label="t('authentication.metadata_url')" prop="metadata_url">
        <el-input v-model="state.form.metadata_url" :placeholder="t('common.please_input')" />
      </el-form-item>
      <el-form-item :label="t('authentication.realm')" prop="realm">
        <el-input v-model="state.form.realm" :placeholder="t('common.please_input')" />
      </el-form-item>
      <el-form-item :label="t('authentication.scope')" prop="scope">
        <el-input v-model="state.form.scope" :placeholder="t('common.please_input')" />
      </el-form-item>
      <el-form-item :label="t('authentication.redirect_url')" prop="redirect_uri">
        <el-input v-model="state.form.redirect_uri" :placeholder="t('common.please_input')" />
      </el-form-item>
      <el-form-item :label="t('authentication.field_mapping')" prop="mapping">
        <el-input
          v-model="state.form.mapping"
          :placeholder="t('authentication.oidc_field_mapping_placeholder')"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button secondary @click="resetForm(oidcForm)">{{ t('common.cancel') }}</el-button>
        <el-button secondary :disabled="!state.form.client_id" @click="validate">
          {{ t('ds.test_connection') }}
        </el-button>
        <el-button type="primary" @click="submitForm(oidcForm)">
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
