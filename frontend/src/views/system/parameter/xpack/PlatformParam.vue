<template>
  <div v-if="xpackValid" class="card">
    <div class="card-title">
      {{ t('parameter.third_party_platform_settings') }}
    </div>
    <div class="card-item" style="width: 100%">
      <div class="label">
        {{ t('parameter.by_third_party_platform') }}
      </div>
      <div class="value">
        <el-switch v-model="formData['platform.auto_create']" />
      </div>
    </div>
    <div class="card-item">
      <div class="label">
        {{ t('parameter.platform_user_organization') }}
        <span class="require"></span>
        <el-tooltip
          effect="dark"
          :content="t('parameter.and_platform_integration')"
          placement="top"
        >
          <el-icon size="16">
            <icon_info_outlined_1></icon_info_outlined_1>
          </el-icon>
        </el-tooltip>
      </div>
      <div class="value">
        <el-select v-model="formData['platform.oid']" filterable>
          <el-option
            v-for="item in organizations"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
      </div>
    </div>
    <div class="card-item" style="margin-left: 16px">
      <div class="label">
        {{ t('workspace.member_type') }}
        <span class="require"></span>
        <el-tooltip
          effect="dark"
          :content="t('parameter.and_platform_integration')"
          placement="top"
        >
          <el-icon size="16">
            <icon_info_outlined_1></icon_info_outlined_1>
          </el-icon>
        </el-tooltip>
      </div>
      <div class="value">
        <el-select v-model="formData['platform.rid']" filterable>
          <el-option
            v-for="item in roles"
            :key="item.value"
            :label="item.name"
            :value="item.value"
          />
        </el-select>
      </div>
    </div>
  </div>

  <div v-if="anyPlatformEnable" class="card">
    <div class="card-title">
      {{ t('parameter.login_settings') }}
    </div>
    <div class="card-item" style="width: 100%">
      <div class="label">
        {{ t('parameter.default_login') }}
      </div>
      <div class="value">
        <el-radio-group v-model="formData['login.default_login']">
          <el-radio v-for="item in loginTypeOptions" :key="item.value" :label="item.value">{{
            item.label
          }}</el-radio>
        </el-radio-group>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { inject, onMounted, reactive, ref, shallowRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { workspaceList } from '@/api/workspace'
import { request } from '@/utils/request'
import icon_info_outlined_1 from '@/assets/svg/icon_info_outlined_1.svg'

const { t } = useI18n()

const anyPlatformEnable = ref(false)
const defaultForm = reactive<Record<string, any>>({
  'platform.auto_create': false,
  'platform.oid': 1,
  'platform.rid': 1,
  'login.default_login': 0,
})

const loginTypeOptions = shallowRef<any[]>([{ value: 0, label: t('login.account_login') }])

const formData = inject<Record<string, any>>('parameterForm', {})

const xpackValid = ref(false)

const organizations = shallowRef<any[]>([])
const roles = [
  {
    name: t('workspace.administrator'),
    value: 1,
  },
  {
    name: t('workspace.ordinary_member'),
    value: 0,
  },
]
const platformMapping = {
  cas: { value: 1, label: 'CAS' },
  oidc: { value: 2, label: 'OIDC' },
  ldap: { value: 3, label: 'LDAP' },
  oauth2: { value: 4, label: 'Oauth2' },
  saml2: { value: 5, label: 'Saml2' },
} as any
const setDefaultForm = () => {
  for (const key in defaultForm) {
    if (formData[key] === undefined) {
      formData[key] = defaultForm[key]
    }
  }
}
const queryCategoryStatus = () => {
  const url = `/system/authentication/platform/status`
  return request.get(url)
}
onMounted(async () => {
  // eslint-disable-next-line no-undef
  const obj = LicenseGenerator.getLicense()
  if (obj?.status !== 'valid') {
    xpackValid.value = false
    return
  }
  const wsRes: any = await workspaceList()
  organizations.value = wsRes
  const platformStatusRes: any = await queryCategoryStatus()
  platformStatusRes.forEach((item: any) => {
    if (item.enable) {
      loginTypeOptions.value.push(platformMapping[item.name])
      anyPlatformEnable.value = true
    }
  })
  if (
    !formData['login.default_login'] ||
    !loginTypeOptions.value.some(
      (option: any) => parseInt(formData['login.default_login']) === option.value
    )
  ) {
    formData['login.default_login'] = 0
  }
  formData['login.default_login'] = parseInt(formData['login.default_login'])
  setDefaultForm()
  xpackValid.value = true
})
</script>

<style lang="less" scoped>
.card {
  width: 100%;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #dee0e3;
  display: flex;
  flex-wrap: wrap;
  margin-top: 16px;
  .card-title {
    font-weight: 500;
    font-style: Medium;
    font-size: 16px;
    line-height: 24px;
    width: 100%;
  }
  .card-item {
    margin-top: 16px;
    width: calc(50% - 8px);
    .label {
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;
      display: flex;
      align-items: center;

      .ed-icon {
        margin-left: 4px;
      }

      .require::after {
        content: '*';
        color: var(--ed-color-danger);
        margin-left: 4px;
      }
    }

    .value {
      margin-top: 8px;
      line-height: 20px;
    }
  }
}
</style>
