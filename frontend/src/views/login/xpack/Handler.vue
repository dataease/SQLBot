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
      <Oauth2 v-if="loginCategory.oauth2" ref="oauth2Handler" @switch-category="switcherCategory" />
      <Cas v-if="loginCategory.cas" @switch-category="switcherCategory" />
      <!-- <Saml2 v-if="loginCategory.saml2" ref="saml2Handler" @switch-category="switcherCategory" /> -->
    </div>
  </el-form-item>

  <!-- <mfa-step v-if="showMfa" :mfa-data="state.mfaData" @close="showMfa = false" />
  <platform-error v-if="platformLoginMsg" :msg="platformLoginMsg" /> -->
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
import { getQueryString, getUrlParams, isPlatformClient } from '@/utils/utils'
import { loadClient, type LoginCategory } from './PlatformClient'
// import MfaStep from './MfaStep.vue'
// import { logoutHandler } from '@/utils/logout'
import { useI18n } from 'vue-i18n'
// import PlatformError from './PlatformError.vue'
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
const oauth2Handler = ref()
const saml2Handler = ref()
/* const state = reactive({
  mfaData: {
    enabled: false,
    ready: false,
  },
}) */

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
  /* if (loginDialogVisible.value) {
    clearInterval(dialogInterval.value)
    dialogInterval.value = null
  } */
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
        /* list.push({ name: 'qrcode', enable: true })
        list.push({ name: 'wecom', enable: true }) */
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
/* const showMfa = ref(false)
const toMfa = (mfa) => {
  state.mfaData = mfa
  showMfa.value = true
  if (document.getElementsByClassName('preheat-container')?.length) {
    document.getElementsByClassName('preheat-container')[0].setAttribute('style', 'display: none;')
  }
} */
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

const casLogin = () => {
  const urlParams = getUrlParams()
  const ticket = getQueryString('ticket')
  request
    .post('/system/authentication/sso/1', urlParams)
    .then((res: any) => {
      const token = res.access_token
      if (token && isPlatformClient()) {
        wsCache.set('sqlbot-platform-client', true)
      }
      userStore.setToken(token)
      userStore.setExp(res.exp)
      userStore.setTime(Date.now())
      userStore.setPlatformInfo({
        flag: 'cas',
        data: ticket,
        origin: 1,
      })
      const queryRedirectPath = getCurLocation()
      router.push({ path: queryRedirectPath })
    })
    .catch((e: any) => {
      userStore.setToken('')
      setTimeout(() => {
        // logoutHandler(true, true)
        platformLoginMsg.value = e?.message || e
        setTimeout(() => {
          window.location.href =
            window.location.origin + window.location.pathname + window.location.hash
        }, 2000)
      }, 1500)
    })
}
const oauth2Login = () => {
  const urlParams = getUrlParams()
  request
    .post('/system/authentication/sso/4', urlParams)
    .then((res: any) => {
      const token = res.access_token
      const platform_info = res.platform_info
      if (token && isPlatformClient()) {
        wsCache.set('sqlbot-platform-client', true)
      }
      userStore.setToken(token)
      userStore.setExp(res.exp)
      userStore.setTime(Date.now())
      userStore.setPlatformInfo({
        flag: 'oauth2',
        data: platform_info ? JSON.stringify(platform_info) : '',
        origin: 4,
      })
      const queryRedirectPath = getCurLocation()
      router.push({ path: queryRedirectPath })
    })
    .catch((e: any) => {
      userStore.setToken('')
      setTimeout(() => {
        // logoutHandler(true, true)
        platformLoginMsg.value = e?.message || e
        setTimeout(() => {
          window.location.href =
            window.location.origin + window.location.pathname + window.location.hash
        }, 2000)
      }, 1500)
    })
}
const oidcLogin = () => {
  const urlParams = getUrlParams()
  request
    .post('/system/authentication/sso/2', urlParams)
    .then((res: any) => {
      const token = res.access_token
      const platform_info = res.platform_info
      if (token && isPlatformClient()) {
        wsCache.set('sqlbot-platform-client', true)
      }
      userStore.setToken(token)
      userStore.setExp(res.exp)
      userStore.setTime(Date.now())
      userStore.setPlatformInfo({
        flag: 'oidc',
        data: platform_info ? JSON.stringify(platform_info) : '',
        origin: 2,
      })
      const queryRedirectPath = getCurLocation()
      router.push({ path: queryRedirectPath })
    })
    .catch((e: any) => {
      userStore.setToken('')
      setTimeout(() => {
        // logoutHandler(true, true)
        platformLoginMsg.value = e?.message || e
        setTimeout(() => {
          window.location.href =
            window.location.origin + window.location.pathname + window.location.hash
        }, 2000)
      }, 1500)
    })
}
const wecomLogin = () => {
  const urlParams = getUrlParams()
  request
    .post('/system/platform/sso/6', urlParams)
    .then((res: any) => {
      const token = res.access_token
      // const platform_info = res.platform_info
      if (token && isPlatformClient()) {
        wsCache.set('sqlbot-platform-client', true)
      }
      userStore.setToken(token)
      userStore.setExp(res.exp)
      userStore.setTime(Date.now())
      userStore.setPlatformInfo({
        flag: 'wecom',
        // data: platform_info ? JSON.stringify(platform_info) : '',
        origin: 6,
      })
      const queryRedirectPath = getCurLocation()
      router.push({ path: queryRedirectPath })
    })
    .catch((e: any) => {
      userStore.setToken('')
      setTimeout(() => {
        // logoutHandler(true, true)
        platformLoginMsg.value = e?.message || e
        setTimeout(() => {
          window.location.href =
            window.location.origin + window.location.pathname + window.location.hash
        }, 2000)
      }, 1500)
    })
}
const dingtalkLogin = () => {
  const urlParams = getUrlParams()
  request
    .post('/system/platform/sso/7', urlParams)
    .then((res: any) => {
      const token = res.access_token
      // const platform_info = res.platform_info
      if (token && isPlatformClient()) {
        wsCache.set('sqlbot-platform-client', true)
      }
      userStore.setToken(token)
      userStore.setExp(res.exp)
      userStore.setTime(Date.now())
      userStore.setPlatformInfo({
        flag: 'dingtalk',
        // data: platform_info ? JSON.stringify(platform_info) : '',
        origin: 7,
      })
      const queryRedirectPath = getCurLocation()
      router.push({ path: queryRedirectPath })
    })
    .catch((e: any) => {
      userStore.setToken('')
      setTimeout(() => {
        // logoutHandler(true, true)
        platformLoginMsg.value = e?.message || e
        setTimeout(() => {
          window.location.href =
            window.location.origin + window.location.pathname + window.location.hash
        }, 2000)
      }, 1500)
    })
}
/* const platformLogin = (origin: number) => {
  const url = '/system/authentication/sso/cas'
  request
    .get(url)
    .then((res: any) => {
      const mfa = res?.mfa
      if (mfa?.enabled) {
        mfa['origin'] = origin
        // toMfa(mfa)
        return
      }
      const token = res.token
      if (token && isPlatformClient()) {
        wsCache.set('sqlbot-platform-client', true)
      }
      userStore.setToken(token)
      userStore.setExp(res.exp)
      userStore.setTime(Date.now())
      if (origin === 10 || isLarkPlatform()) {
        window.location.href =
          window.location.origin + window.location.pathname + window.location.hash
      } else {
        const queryRedirectPath = getCurLocation()
        router.push({ path: queryRedirectPath })
      }
    })
    .catch((e: any) => {
      userStore.setToken('')
      if (isLarkPlatform()) {
        setTimeout(() => {
          window.location.href =
            window.location.origin + window.location.pathname + window.location.hash
        }, 2000)
      } else {
        setTimeout(() => {
          // logoutHandler(true, true)
          platformLoginMsg.value = e?.message || e
        }, 1500)
      }
    })
}
 */
const queryCategoryStatus = () => {
  const url = `/system/authentication/platform/status`
  return request.get(url)
}

/* const wecomToken = async () => {
  const code = getQueryString('code')
  const state = getQueryString('state')
  if (!code || !state) {
    return null
  }
  const res = await request.post({ url: '/wecom/token', data: { code, state } })
  userStore.setToken(res.data)
  return res.data
}

const larkToken = async () => {
  const code = getQueryString('code')
  const state = getQueryString('state')
  if (!code || !state) {
    return null
  }
  const res = await request.post({ url: '/lark/token', data: { code, state } })
  userStore.setToken(res.data)
  return res.data
}

const saml2Token = (cb) => {
  const token = getQueryString('saml2Token')
  if (!token) {
    return
  }
  userStore.setToken(token)
  // eslint-disable-next-line @typescript-eslint/no-unused-expressions
  cb && cb()
}

const oauth2Token = (cb) => {
  const localCodeKey = localStorage.getItem('DE_OAUTH2_CODE_KEY') || 'code'
  const code = getQueryString(localCodeKey)
  const state = getQueryString('state')
  if (!code || !state) {
    throw Error('no code or state')
    return null
  }
  request
    .post({ url: '/oauth2/token', data: { code, state } })
    .then((res) => {
      userStore.setToken(res.data.token)
      // eslint-disable-next-line @typescript-eslint/no-unused-expressions
      cb && cb()
    })
    .catch(() => {
      setTimeout(() => {
        window.location.href =
          window.location.origin + window.location.pathname + window.location.hash
      }, 2000)
    })
}

const larksuiteToken = async () => {
  const code = getQueryString('code')
  const state = getQueryString('state')
  if (!code || !state) {
    return null
  }
  const res = await request.post({ url: '/larksuite/token', data: { code, state } })
  userStore.setToken(res.data)
  return res.data
}

const dingtalkToken = async () => {
  const code = getQueryString('code')
  const state = getQueryString('state')
  if (!code || !state) {
    return null
  }
  const res = await request.post({ url: '/dingtalk/token', data: { code, state } })
  userStore.setToken(res.data)
  return res.data
} */

const callBackType = () => {
  return getQueryString('state')
}

const auto2Platform = async () => {
  if (adminLogin.value) {
    updateLoading(false, 100)
    return
  }
  const resData = await request.get('/system/parameter/login')
  let res = 0
  const resObj = {} as any
  resData.forEach((item: any) => {
    resObj[item.pkey] = item.pval
  })
  res = parseInt(resObj['login.default_login'] || 0)
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
    if (state?.includes('cas') && getQueryString('ticket')) {
      // platformLogin(1)
      casLogin()
    } else if (state?.includes('oauth2')) {
      oauth2Login()
    } else if (state?.includes('oidc')) {
      oidcLogin()
    } else if (state?.includes('wecom')) {
      wecomLogin()
    } else if (state?.includes('dingtalk')) {
      dingtalkLogin()
    } else {
      auto2Platform()
    }
    /*  else if (window.location.pathname.includes('/oidcbi/')) {
      platformLogin(2)
    } else if (state?.includes('dingtalk')) {
      await dingtalkToken()
      platformLogin(5)
    } else if (state?.includes('larksuite')) {
      await larksuiteToken()
      platformLogin(7)
    } else if (state?.includes('wecom')) {
      await wecomToken()
      platformLogin(6)
    } else if (state?.includes('lark')) {
      await larkToken()
      platformLogin(4)
    } else if (state?.includes('oauth2')) {
      oauth2Token(() => {
        platformLogin(9)
      })
    } else if (state?.includes('saml2')) {
      saml2Token(() => {
        platformLogin(10)
      })
    } else {
      auto2Platform()
    } */
  })
})

/* defineExpose({
  ssoLogin,
  toMfa,
}) */
</script>

<style lang="less" scoped>
.login-list {
  margin-top: 2px;
  width: 100%;
  display: flex;
  justify-content: center;
  column-gap: 16px;
}
.de-qr-hidden {
  display: none;
}
.de-other-login-divider {
  border-top: 1px solid #1f232926;
}
.other-login-item {
  margin-bottom: 0;
}
</style>
