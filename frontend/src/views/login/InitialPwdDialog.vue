<script lang="ts" setup>
import { reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { AuthApi } from '@/api/login'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  account: { type: String, required: true },
  oldPwd: { type: String, required: true },
})
const emits = defineEmits(['update:modelValue', 'pwdSaved'])

const { t } = useI18n()
const pwdRef = ref()
const pwdForm = reactive({
  pwd: '',
  new_pwd: '',
  confirm_pwd: '',
})
const PWD_REGEX =
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[~!@#$%^&*()_+\-={}|:"<>?`\[\];',./])[A-Za-z\d~!@#$%^&*()_+\-={}|:"<>?`\[\];',./]{8,20}$/
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
const validatePass = (rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error(t('common.please_input', { msg: t('user.upgrade_pwd.new_pwd') })))
  } else {
    if (!PWD_REGEX.test(value)) {
      callback(new Error(t('user.upgrade_pwd.pwd_format_error')))
      return
    }
    if (pwdForm.confirm_pwd !== '') {
      if (!pwdRef.value) return
      pwdRef.value.validateField('confirm_pwd')
    }
    callback()
  }
}
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
const validatePass2 = (rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error(t('common.please_input', { msg: t('user.upgrade_pwd.confirm_pwd') })))
  } else if (!PWD_REGEX.test(value)) {
    callback(new Error(t('user.upgrade_pwd.pwd_format_error')))
  } else if (value !== pwdForm.new_pwd) {
    callback(new Error(t('user.upgrade_pwd.two_pwd_not_match')))
  } else {
    callback()
  }
}
const rules = {
  pwd: [
    {
      required: true,
      message: t('common.please_input', { msg: t('user.upgrade_pwd.old_pwd') }),
      trigger: 'blur',
    },
  ],
  new_pwd: [{ validator: validatePass, trigger: 'blur' }],
  confirm_pwd: [{ validator: validatePass2, trigger: 'blur' }],
}

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      pwdForm.pwd = props.oldPwd
      pwdForm.new_pwd = ''
      pwdForm.confirm_pwd = ''
    }
  }
)

const closeHandler = () => {
  emits('update:modelValue', false)
}

const submit = () => {
  pwdRef.value.validate((res: any) => {
    if (res) {
      AuthApi.changePwd({
        account: props.account,
        pwd: pwdForm.pwd,
        new_pwd: pwdForm.new_pwd,
      }).then(() => {
        ElMessage({
          type: 'success',
          message: t('login.force_change_pwd_success'),
        })
        emits('pwdSaved', pwdForm.new_pwd)
        closeHandler()
      })
    }
  })
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="t('login.force_change_pwd_title')"
    width="480"
    append-to-body
    @update:model-value="(val: boolean) => emits('update:modelValue', val)"
    @close="closeHandler"
  >
    <div class="initial-pwd-tips">{{ t('login.force_change_pwd_tips') }}</div>
    <el-form
      ref="pwdRef"
      :rules="rules"
      label-position="top"
      :model="pwdForm"
      style="width: 100%"
      @submit.prevent
    >
      <el-form-item prop="pwd" :label="t('user.upgrade_pwd.old_pwd')">
        <el-input
          v-model="pwdForm.pwd"
          :placeholder="t('common.please_input', { msg: t('user.upgrade_pwd.old_pwd') })"
          type="password"
          show-password
          clearable
        />
      </el-form-item>
      <el-form-item prop="new_pwd" :label="t('user.upgrade_pwd.new_pwd')">
        <el-input
          v-model="pwdForm.new_pwd"
          :placeholder="t('common.please_input', { msg: t('user.upgrade_pwd.new_pwd') })"
          type="password"
          show-password
          clearable
        />
      </el-form-item>
      <el-form-item prop="confirm_pwd" :label="t('user.upgrade_pwd.confirm_pwd')">
        <el-input
          v-model="pwdForm.confirm_pwd"
          :placeholder="t('common.please_input', { msg: t('user.upgrade_pwd.confirm_pwd') })"
          type="password"
          show-password
          clearable
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button secondary @click="closeHandler">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="submit">{{ t('common.save') }}</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="less" scoped>
.initial-pwd-tips {
  margin-bottom: 16px;
  color: var(--ed-color-warning, #e6a23c);
  font-size: 14px;
  line-height: 22px;
}
</style>
