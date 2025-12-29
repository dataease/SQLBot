<script lang="ts" setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElLoading } from 'element-plus-secondary'
import { useI18n } from 'vue-i18n'
import type { FormInstance, FormRules } from 'element-plus-secondary'
import { request } from '@/utils/request'
const { t } = useI18n()
const dialogVisible = ref(false)
const loadingInstance = ref<ReturnType<typeof ElLoading.service> | null>(null)
const ldapForm = ref<FormInstance>()

const id = ref<number | null>(null)
const state = reactive({
  form: reactive<any>({
    server_address: '',
    bind_dn: '',
    bind_pwd: '',
    ou: '',
    user_filter: '',
    mapping: '',
  }),
})
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
const rule = reactive<FormRules>({
  server_address: [
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
  ],
  bind_dn: [
    {
      required: true,
      message: t('common.require'),
      trigger: ['blur', 'change'],
    },
  ],
  bind_pwd: [
    {
      required: true,
      message: t('common.require'),
      trigger: ['blur', 'change'],
    },
  ],
  ou: [
    {
      required: true,
      message: t('common.require'),
      trigger: ['blur', 'change'],
    },
  ],
  user_filter: [
    {
      required: true,
      message: t('common.require'),
      trigger: ['blur', 'change'],
    },
  ],
  mapping: [
    {
      required: false,
      message: t('common.require'),
      trigger: ['blur', 'change'],
    },
    { required: false, validator: validateMapping, trigger: 'blur' },
  ],
})

const edit = () => {
  showLoading()
  request
    .get('/system/authentication/3')
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
        id: 3,
        type: 3,
        config: JSON.stringify(param),
        name: 'ldap',
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
  resetForm(ldapForm.value)
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
    type: 3,
    name: 'ldap',
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
    :title="t('authentication.ldap_settings')"
    modal-class="platform-info-drawer"
    size="600px"
    direction="rtl"
  >
    <el-form
      ref="ldapForm"
      require-asterisk-position="right"
      :model="state.form"
      :rules="rule"
      label-width="80px"
      label-position="top"
    >
      <el-form-item :label="t('authentication.server_address')" prop="server_address">
        <el-input
          v-model="state.form.server_address"
          :placeholder="t('authentication.server_address_placeholder')"
        />
      </el-form-item>

      <el-form-item :label="t('authentication.bind_dn')" prop="bind_dn">
        <el-input
          v-model="state.form.bind_dn"
          :placeholder="t('authentication.bind_dn_placeholder')"
        />
      </el-form-item>

      <el-form-item :label="t('authentication.bind_pwd')" prop="bind_pwd">
        <el-input
          v-model="state.form.bind_pwd"
          type="password"
          show-password
          :placeholder="t('common.please_input')"
        />
      </el-form-item>

      <el-form-item :label="t('authentication.ou')" prop="ou">
        <el-input v-model="state.form.ou" :placeholder="t('authentication.ou_placeholder')" />
      </el-form-item>

      <el-form-item :label="t('authentication.user_filter')" prop="user_filter">
        <el-input
          v-model="state.form.user_filter"
          :placeholder="t('authentication.user_filter_placeholder', ['|', '|'])"
        />
      </el-form-item>

      <el-form-item :label="t('authentication.field_mapping')" prop="mapping">
        <el-input
          v-model="state.form.mapping"
          :placeholder="t('authentication.ldap_field_mapping_placeholder')"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button secondary @click="resetForm(ldapForm)">{{ t('common.cancel') }}</el-button>
        <el-button secondary :disabled="!state.form.server_address" @click="validate">
          {{ t('ds.test_connection') }}
        </el-button>
        <el-button type="primary" @click="submitForm(ldapForm)">
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
