<template>
  <div v-if="loginCategory.qrcode" :class="{ 'de-qr-hidden': !qrStatus }">
    <QrTab
      v-if="qrStatus"
      :wecom="loginCategory.wecom"
      :dingtalk="loginCategory.dingtalk"
      :lark="loginCategory.lark"
      :larksuite="loginCategory.larksuite"
    />
  </div>
  <LdapLoginForm v-if="isLdap" />
  <div class="sqlbot-other-login">
    <el-divider v-if="anyEnable" class="de-other-login-divider">{{
      t('login.other_login')
    }}</el-divider>
    <el-form-item v-if="anyEnable" class="other-login-item">
      <div class="login-list">
        <QrcodeLdap
          v-if="loginCategory.qrcode || loginCategory.ldap"
          ref="qrcodeLdapHandler"
          :qrcode="loginCategory.qrcode"
          :ldap="loginCategory.ldap"
          @status-change="qrStatusChange"
        />
        <Oidc v-if="loginCategory.oidc" @switch-category="switcherCategory" />
        <Oauth2 v-if="loginCategory.oauth2" @switch-category="switcherCategory" />
        <Cas v-if="loginCategory.cas" @switch-category="switcherCategory" />
      </div>
    </el-form-item>
  </div>

  <el-dialog
    v-model="loginDialogVisible"
    :title="dialogTitle"
    width="420"
    :destroy-on-close="true"
    :close-on-click-modal="false"
    modal-class="login-platform-dialog"
    @closed="closeHandler"
  >
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="closeHandler">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="redirectImmediately">
          {{ t('login.redirect_immediately') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script lang="ts" setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import QrcodeLdap from './QrcodeLdap.vue'
import LdapLoginForm from './LdapLoginForm.vue'

import Oidc from './Oidc.vue'
import Cas from './Cas.vue'
import Oauth2 from './Oauth2.vue'
import QrTab from './QrTab.vue'
import { request } from '@/utils/request'
import { useCache } from '@/utils/useCache'

import router from '@/router'
import { useUserStore } from '@/stores/user.ts'
import { getQueryString, getSQLBotAddr, getUrlParams, isPlatformClient } from '@/utils/utils'
import { loadClient, origin_mapping, type LoginCategory } from './PlatformClient'

import { useI18n } from 'vue-i18n'
const isLdap = ref(false)
defineProps<{
  loading: boolean
}>()
const emits = defineEmits(['switchTab', 'autoCallback', 'update:loading'])
const updateLoading = (show: boolean, time: number = 1000) => {
  setTimeout(() => {
    emits('update:loading', show)
  }, time)
}
const { t } = useI18n()
interface Categoryparam {
  category: string
  proxy?: string
}

const adminLogin = computed(() => router.currentRoute?.value?.name === 'admin-login')
const loginDialogVisible = ref(false)
const dialogTitle = ref('')
const dialogInterval = ref<any>(null)
const currentCancelHandler = ref<((reason?: string) => void) | null>(null)
const currentSureHandler = ref<(() => void) | null>(null)
interface RedirectDialogResult {
  promise: Promise<boolean>
  sure: () => void
  cancel: (reason?: string) => void
}

const platformLoginMsg = ref('')
const { wsCache } = useCache()
const userStore = useUserStore()
const qrStatus = ref(false)
const loginCategory = ref({} as LoginCategory)
const anyEnable = ref(false)
const qrcodeLdapHandler = ref()
const saml2Handler = ref()

const openDialog = (origin_text: string): RedirectDialogResult => {
  const platforms: { [key: string]: string } = {
    cas: 'CAS',
    oidc: 'OIDC',
    ldap: 'LDAP',
    oauth2: 'OAuth2',
    saml2: 'Saml2',
  }

  let timer = 3
  const platFormName = platforms[origin_text] || 'SSO'
  dialogTitle.value = t('login.redirect_2_auth', [platFormName, timer])

  let rejectPromise: ((reason?: any) => void) | null = null
  let resolvePromise: ((value: boolean | PromiseLike<boolean>) => void) | null = null
  loginDialogVisible.value = true

  const promise = new Promise<boolean>((resolve, reject) => {
    rejectPromise = reject
    resolvePromise = resolve
    dialogInterval.value = setInterval(() => {
      if (timer-- <= 0) {
        clearInterval(dialogInterval.value)
        closeDialog()
        resolve(true)
        return
      }
      dialogTitle.value = t('login.redirect_2_auth', [platFormName, timer])
    }, 1000)
  })
  const sure = (): void => {
    if (dialogInterval.value) {
      clearInterval(dialogInterval.value)
      dialogInterval.value = null
    }
    closeDialog()
    if (resolvePromise) {
      resolvePromise(true)
      resolvePromise = null
    }
  }
  const cancel = (reason: string = '用户取消跳转'): void => {
    if (dialogInterval.value) {
      clearInterval(dialogInterval.value)
      dialogInterval.value = null
    }
    closeDialog()

    if (rejectPromise) {
      rejectPromise(new Error(reason))
      rejectPromise = null
    }
  }
  return {
    promise,
    sure,
    cancel,
  }
}
const closeHandler = () => {
  if (currentCancelHandler.value) {
    currentCancelHandler.value('手动取消')
  }
}
const closeDialog = () => {
  loginDialogVisible.value = false
}
const redirectImmediately = () => {
  if (currentSureHandler.value) {
    currentSureHandler.value()
  }
}
const init = (cb?: () => void) => {
  queryCategoryStatus()
    .then((res) => {
      if (res) {
        const list: any[] = res as any[]
        list.forEach((item: { name: keyof LoginCategory; enable: boolean }) => {
          loginCategory.value[item.name] = item.enable
          if (item.enable) {
            anyEnable.value = true
          }
        })
      }
      wsCache.delete('oidc-error')
      if (!loadClient(loginCategory.value)) {
        // eslint-disable-next-line @typescript-eslint/no-unused-expressions
        cb && cb()
      }
    })
    .catch(() => {
      if (!wsCache.get('oidc-error')) {
        wsCache.set('oidc-error', 1)
        window.location.reload()
      }
    })
}

const qrStatusChange = (activeComponent: string) => {
  qrStatus.value = activeComponent === 'qrcode'
  isLdap.value = false
  if (activeComponent === 'account') {
    emits('switchTab', 'simple')
  } else if (activeComponent === 'ldap') {
    isLdap.value = true
    switcherCategory({ category: 'ldap', proxy: '' })
  }
}

const ssoLogin = (category: any) => {
  const array = [
    { category: 'cas', proxy: '/casbi/#' },
    { category: 'oidc', proxy: '/oidcbi/#' },
    { category: 'ldap', proxy: '' },
    { category: 'oauth2', proxy: '/#' },
    { category: 'saml2', proxy: '/#' },
  ]
  if (category) {
    if (category === 3) {
      qrcodeLdapHandler.value?.setActive('ldap')
    }
    switcherCategory(array[category - 1])
  }
}

const switcherCategory = async (param: Categoryparam) => {
  const { category, proxy } = param
  const curOrigin = window.location.origin
  const curLocation = getCurLocation()
  if (!category || category === 'simple' || category === 'ldap') {
    qrStatus.value = false
    emits('switchTab', category || 'simple')
    return
  }

  const { promise, sure, cancel } = openDialog(category)
  currentCancelHandler.value = cancel
  currentSureHandler.value = sure
  let shouldRedirect = false
  try {
    shouldRedirect = await promise
  } finally {
    currentCancelHandler.value = null
    currentSureHandler.value = null
  }
  if (!shouldRedirect) {
    return
  }

  let pathname = window.location.pathname
  if (pathname) {
    pathname = pathname.substring(0, pathname.length - 1)
  }
  const nextPage = curOrigin + pathname + proxy + curLocation
  if (category === 'oauth2') {
    request.get('/system/authentication/login/4').then((res: any) => {
      window.location.href = res
      window.open(res, '_self')
    })
    return
  }
  if (category === 'oidc') {
    request.get('/system/authentication/login/2').then((res: any) => {
      window.location.href = res
      window.open(res, '_self')
    })
    return
  }
  if (category === 'saml2') {
    saml2Handler?.value?.toLoginPage()
    return
  }
  if (category === 'cas') {
    request.get('/system/authentication/login/1').then((res: any) => {
      window.location.href = res
      window.open(res, '_self')
    })
    return
  }
  window.location.href = nextPage
}

const getCurLocation = () => {
  let queryRedirectPath = '/'
  if (router.currentRoute.value.query.redirect) {
    queryRedirectPath = router.currentRoute.value.query.redirect as string
  }
  return queryRedirectPath
}
const third_party_authentication = (state?: string) => {
  if (!state) {
    return null
  }
  const findKey = Object.keys(origin_mapping)
    .reverse()
    .find((key: any) => state.includes(origin_mapping[key])) as unknown as number | null
  if (!findKey) {
    return null
  }
  const originName = origin_mapping[findKey]
  if (originName === 'saml2' || originName === 'ldap') {
    return null
  }
  const urlParams = getUrlParams()
  const urlFlag = findKey && findKey > 5 ? 'platform' : 'authentication'
  const ssoUrl = `/system/${urlFlag}/sso/${findKey}`
  if (!urlParams?.redirect_uri) {
    urlParams['redirect_uri'] = encodeURIComponent(getSQLBotAddr())
  }
  request
    .post(ssoUrl, urlParams)
    .then((res: any) => {
      const token = res.access_token
      const platform_info = res.platform_info
      if (token && isPlatformClient()) {
        wsCache.set('sqlbot-platform-client', true)
      }
      userStore.setToken(token)
      userStore.setExp(res.exp)
      userStore.setTime(Date.now())
      const platform_info_param = {
        flag: originName,
        origin: findKey,
      } as any
      if (platform_info) {
        platform_info_param['data'] = JSON.stringify(platform_info)
      }
      if (originName === 'cas') {
        const ticket = getQueryString('ticket')
        platform_info_param['data'] = ticket
      }
      userStore.setPlatformInfo(platform_info_param)
      const queryRedirectPath = getCurLocation()
      router.push({ path: queryRedirectPath })
    })
    .catch((e: any) => {
      userStore.setToken('')
      setTimeout(() => {
        platformLoginMsg.value = e?.message || e
        setTimeout(() => {
          window.location.href = getSQLBotAddr() + window.location.hash
        }, 2000)
      }, 1500)
    })
  return findKey
}

const queryCategoryStatus = () => {
  const url = `/system/authentication/platform/status`
  return request.get(url)
}

const callBackType = () => {
  return getQueryString('state')
}
const loginTypeParam = (): number | null => {
  let login_type = getQueryString('login_type')
  if (!login_type) {
    return null
  }
  const mappingArray = ['default', 'cas', 'oidc', 'ldap', 'oauth2', 'saml2']
  const index = mappingArray.indexOf(login_type.toLocaleLowerCase())
  if (index === -1) {
    if (/^[0-5]$/.test(login_type)) {
      return parseInt(login_type)
    }
    return null
  }
  return index
}

const auto2Platform = async () => {
  if (adminLogin.value) {
    updateLoading(false, 100)
    return
  }
  let res: number | null = loginTypeParam()
  if (res === null) {
    const resData = await request.get('/system/parameter/login')

    const resObj = {} as any
    resData.forEach((item: any) => {
      resObj[item.pkey] = item.pval
    })
    res = parseInt(resObj['login.default_login'] || 0)
  }

  const originArray = ['default', 'cas', 'oidc', 'ldap', 'oauth2', 'saml2']
  if (res && !adminLogin.value && loginCategory.value[originArray[res] as keyof LoginCategory]) {
    if (res === 3) {
      qrStatusChange('ldap')
      updateLoading(false)
    }
    nextTick(() => {
      ssoLogin(res)
    })
  } else {
    updateLoading(false)
  }
}

onMounted(() => {
  if (adminLogin.value) {
    updateLoading(false, 100)
    return
  }
  // eslint-disable-next-line no-undef
  const obj = LicenseGenerator.getLicense()
  if (obj?.status !== 'valid') {
    updateLoading(false, 100)
    return
  }
  wsCache.delete('sqlbot-platform-client')
  init(async () => {
    const state = callBackType()
    const originName = third_party_authentication(state as string)
    if (!originName) {
      auto2Platform()
      return
    }
  })
})
</script>

<style lang="less" scoped>
.login-list {
  width: 100%;
  display: flex;
  justify-content: center;
  column-gap: 16px;
}
.de-qr-hidden {
  display: none;
}

.other-login-item {
  margin-bottom: 0;
}
.sqlbot-other-login {
  height: 68px;
  display: flex;
  flex-direction: column;
  row-gap: 16px;
  overflow-y: hidden;
  .de-other-login-divider {
    border-top: 1px solid #1f232926;
    margin: 9px 0 10px 0;
    ::v-deep(.ed-divider__text) {
      color: #8f959e;
      font-size: 12px;
      font-weight: 400;
    }
  }
}
</style>
