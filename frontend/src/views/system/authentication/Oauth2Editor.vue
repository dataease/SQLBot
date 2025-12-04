<script lang="ts" setup>
import { ref, reactive, onBeforeMount } from 'vue'
import { ElMessage, ElLoading } from 'element-plus-secondary'
import { useI18n } from 'vue-i18n'
import {
  type FormInstance,
  type FormRules,
  ElInput,
  ElRadio,
  ElRadioGroup,
  ElSelect,
} from 'element-plus-secondary'
import { request } from '@/utils/request'
import { getSQLBotAddr } from '@/utils/utils'

const { t } = useI18n()
const dialogVisible = ref(false)
const loadingInstance = ref<ReturnType<typeof ElLoading.service> | null>(null)
const oauth2Form = ref<FormInstance>()
const id = ref<number | null>(null)

const state = reactive({
  form: reactive<any>({
    authorize_url: '',
    token_url: '',
    userinfo_url: '',
    revoke_url: '',
    scope: '',
    client_id: '',
    client_secret: '',
    redirect_url: getSQLBotAddr(),
    token_auth_method: 'basic',
    userinfo_auth_method: 'header',
    logout_redirect_url: '',
    mapping: '',
  }),
})
const componentMap = {
  'el-input': ElInput,
  'el-select': ElSelect,
  'el-radio-group': ElRadioGroup,
  'el-radio': ElRadio,
} as any

const getComponent = (name: string) => {
  return componentMap[name]
}
const form_config_list = ref<any[]>([
  /* {
    label: '自定义配置',
    field: 'authMethod',
    value: '',
    // component: resolveComponent('ElInput') as typeof ElInput,
    component: 'el-input',
    attrs: {
      placeholder: t('common.please_input') + 123,
    },
    validator: [
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
      { required: true, pattern: /^[a-zA-Z][a-zA-Z0-9_]{3,15}$/, message: '', trigger: 'blur' },
    ],
  }, */
])
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
  if (value === null || value === '') {
    callback()
  }
  try {
    JSON.parse(value)
  } catch (e) {
    console.error(e)
    callback(new Error(t('authentication.in_json_format')))
  }
  callback()
}
const rule = reactive<FormRules>({
  authorize_url: [
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
  token_url: [
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
  userinfo_url: [
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

  scope: [
    {
      min: 2,
      max: 50,
      message: t('common.input_limit', [2, 50]),
      trigger: 'blur',
    },
  ],
  client_id: [
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
  client_secret: [
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
  ],
  redirect_url: [
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
    .get('/system/authentication/4')
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
        id: 4,
        type: 4,
        config: JSON.stringify(param),
        name: 'oauth2',
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
  resetForm(oauth2Form.value)
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
    type: 4,
    name: 'oauth2',
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

onBeforeMount(() => {
  if (form_config_list.value?.length) {
    form_config_list.value.forEach((item: any) => {
      rule[item.field] = item.validator
      state.form[item.field] = item.value
    })
  }
})
</script>

<template>
  <el-drawer
    v-model="dialogVisible"
    :title="t('authentication.oauth2_settings')"
    modal-class="platform-info-drawer"
    size="600px"
    direction="rtl"
  >
    <el-form
      ref="oauth2Form"
      require-asterisk-position="right"
      :model="state.form"
      :rules="rule"
      label-width="80px"
      label-position="top"
    >
      <el-form-item :label="t('authentication.authorize_url')" prop="authorize_url">
        <el-input v-model="state.form.authorize_url" :placeholder="t('common.please_input')" />
      </el-form-item>
      <el-form-item :label="t('authentication.token_url')" prop="token_url">
        <el-input v-model="state.form.token_url" :placeholder="t('common.please_input')" />
      </el-form-item>
      <el-form-item :label="t('authentication.userinfo_url')" prop="userinfo_url">
        <el-input v-model="state.form.userinfo_url" :placeholder="t('common.please_input')" />
      </el-form-item>
      <el-form-item :label="t('authentication.revoke_url')" prop="revoke_url">
        <el-input v-model="state.form.revoke_url" :placeholder="t('common.please_input')" />
      </el-form-item>

      <el-form-item :label="t('authentication.scope')" prop="scope">
        <el-input v-model="state.form.scope" :placeholder="t('common.please_input')" />
      </el-form-item>

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

      <el-form-item :label="t('authentication.redirect_url')" prop="redirect_url">
        <el-input v-model="state.form.redirect_url" :placeholder="t('common.please_input')" />
      </el-form-item>

      <el-form-item :label="t('authentication.logout_redirect_url')" prop="logout_redirect_url">
        <el-input
          v-model="state.form.logout_redirect_url"
          :placeholder="t('authentication.logout_redirect_url_placeholder')"
        />
      </el-form-item>

      <el-form-item :label="t('authentication.field_mapping')" prop="mapping">
        <el-input
          v-model="state.form.mapping"
          :placeholder="t('authentication.oauth2_field_mapping_placeholder')"
        />
      </el-form-item>

      <!-- <el-form-item :label="t('datasource.auth_method')" prop="authMethod">
        <el-radio-group v-model="state.form.authMethod">
          <el-radio label="0">Authorization Code</el-radio>
          <el-radio label="1">Client Secret Jwt</el-radio>
        </el-radio-group>
      </el-form-item> -->

      <el-form-item :label="t('authentication.token_auth_method')" prop="token_auth_method">
        <el-radio-group v-model="state.form.token_auth_method">
          <el-radio value="basic">Basic</el-radio>
          <el-radio value="body">Body</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item :label="t('authentication.userinfo_auth_method')" prop="userinfo_auth_method">
        <el-radio-group v-model="state.form.userinfo_auth_method">
          <el-radio value="header">Header</el-radio>
          <el-radio value="query">Query</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item
        v-for="form_item in form_config_list"
        :key="form_item.field"
        :label="form_item.label"
        :prop="form_item.field"
      >
        <component
          :is="getComponent(form_item.component)"
          v-model="state.form[form_item.field]"
          v-bind="form_item.attrs"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button secondary @click="resetForm(oauth2Form)">{{ t('common.cancel') }}</el-button>
        <el-button secondary :disabled="!state.form.client_id" @click="validate">
          {{ t('ds.test_connection') }}
        </el-button>
        <el-button type="primary" @click="submitForm(oauth2Form)">
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
