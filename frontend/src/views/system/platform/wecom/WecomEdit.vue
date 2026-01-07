<script lang="ts" setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElLoading } from 'element-plus-secondary'
import { request } from '@/utils/request'
import { useI18n } from 'vue-i18n'
import type { FormInstance, FormRules } from 'element-plus-secondary'
const { t } = useI18n()
const dialogVisible = ref(false)
const loadingInstance = ref<ReturnType<typeof ElLoading.service> | null>(null)
const wecomForm = ref<FormInstance>()
interface WecomkForm {
  corpid?: string
  agent_id?: string
  corpsecret?: string
}
const state = reactive({
  form: reactive<WecomkForm>({
    agent_id: '',
    corpid: '',
    corpsecret: '',
  }),
})
const origin = ref(6)
const id = ref()
const rule = reactive<FormRules>({
  agent_id: [
    {
      required: true,
      message: t('common.require'),
      trigger: 'blur',
    },
    {
      min: 5,
      max: 20,
      message: t('common.input_limit', [5, 20]),
      trigger: 'blur',
    },
  ],
  corpid: [
    {
      required: true,
      message: t('common.require'),
      trigger: 'blur',
    },
    {
      min: 5,
      max: 20,
      message: t('common.input_limit', [5, 20]),
      trigger: 'blur',
    },
  ],
  corpsecret: [
    {
      required: true,
      message: t('common.require'),
      trigger: 'blur',
    },
    {
      min: 5,
      max: 100,
      message: t('common.input_limit', [5, 100]),
      trigger: 'blur',
    },
  ],
})

const edit = (row: any) => {
  state.form = {
    agent_id: row.agent_id,
    corpid: row.corpid,
    corpsecret: row.corpsecret,
  }
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
        name: 'wecom',
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
}

const reset = () => {
  resetForm(wecomForm.value)
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
    type: origin.value,
    name: 'wecom',
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
    :title="t('user.wechat_for_business')"
    modal-class="platform-info-drawer"
    size="600px"
    direction="rtl"
  >
    <el-form
      ref="wecomForm"
      require-asterisk-position="right"
      :model="state.form"
      :rules="rule"
      label-width="80px"
      label-position="top"
    >
      <el-form-item label="Corpid" prop="corpid">
        <el-input v-model="state.form.corpid" :placeholder="t('common.please_input')" />
      </el-form-item>

      <el-form-item label="AgentId" prop="agent_id">
        <el-input v-model="state.form.agent_id" :placeholder="t('common.please_input')" />
      </el-form-item>

      <el-form-item label="APP Secret" prop="corpsecret">
        <el-input
          v-model="state.form.corpsecret"
          type="password"
          show-password
          :placeholder="t('common.please_input')"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="resetForm(wecomForm)">{{ t('common.cancel') }}</el-button>
        <el-button
          :disabled="!state.form.corpid || !state.form.corpsecret || !state.form.agent_id"
          @click="validate"
        >
          {{ t('ds.check') }}
        </el-button>
        <el-button type="primary" @click="submitForm(wecomForm)">
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
