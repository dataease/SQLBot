import { loadScript } from '@/utils/RemoteJs'
import { getQueryString } from '@/utils/utils'
import { ElMessage, ElMessageBox } from 'element-plus-secondary'

// import { useI18n } from 'vue-i18n'
import { i18n } from '@/i18n'
import { queryClientInfo } from './platformUtils'
declare global {
  interface Window {
    tt: any
    h5sdk: any
    dd: any
  }
}
export interface LoginCategory {
  oidc?: boolean
  cas?: boolean
  ldap?: boolean
  oauth2?: boolean
  saml2?: boolean
  qrcode?: boolean
  lark?: boolean
  dingtalk?: boolean
  wecom?: boolean
  larksuite?: boolean
}
const t = i18n.global.t
const flagArray = ['dingtalk', 'lark', 'larksuite']
const urlArray = [
  'https://g.alicdn.com/dingding/dingtalk-jsapi/3.1.0/dingtalk.open.js',
  'https://lf1-cdn-tos.bytegoofy.com/goofy/lark/op/h5-js-sdk-1.5.26.js',
  'https://lf1-cdn-tos.bytegoofy.com/goofy/lark/op/h5-js-sdk-1.5.16.js',
]
export const loadClient = (category: LoginCategory) => {
  const type = getQueryString('client')
  const corpid = getQueryString('corpid')
  if (type && !category[type as keyof LoginCategory]) {
    ElMessageBox.confirm(t('login.platform_disable', [t(`threshold.${type}`)]), {
      confirmButtonType: 'danger',
      type: 'warning',
      showCancelButton: false,
      confirmButtonText: t('commons.refresh'),
      cancelButtonText: t('dataset.cancel'),
      autofocus: false,
      showClose: false,
    })
      .then(() => {
        window.location.reload()
      })
      .catch(() => {})
    return false
  }
  if (!type || !flagArray.includes(type) || !category[type as keyof LoginCategory]) {
    return false
  }
  const index = flagArray.indexOf(type)
  const jsId = `fit2cloud-dataease-v2-platform-client-${type}`
  const awaitMethod = loadScript(urlArray[index], jsId)
  awaitMethod
    .then(() => {
      if (index === 0) {
        dingtalkClientRequest(corpid)
      }
      if (index === 1) {
        larkClientRequest()
      }
      if (index === 2) {
        larksuiteClientRequest()
      }
    })
    .catch(() => {
      ElMessage.error('加载失败')
    })
  return true
}

const dingtalkClientRequest = async (id: string | null) => {
  if (!id) {
    const clientInfoRes = await queryClientInfo(7)
    id = clientInfoRes['corpid']
  }
  const dd = window['dd']
  dd.ready(function () {
    dd.runtime.permission.requestAuthCode({
      corpId: id,
      onSuccess: function (info: any) {
        const code = info.code
        const state = `fit2cloud-dingtalk-client`
        toUrl(`?code=${code}&state=${state}`)
      },
      onFail: function (err: any) {
        ElMessage.error(err)
      },
    })
  })
}

const larkClientRequest = async () => {
  if (!window['tt']) {
    ElMessage.error('load remote lark js error')
    return
  }
  const res = await queryClientInfo(8)
  if (!res?.appId) {
    ElMessage.error('get appId error')
    return
  }
  const appId = res.data.appId
  const callRequestAuthCode = () => {
    window['tt'].requestAuthCode({
      appId: appId,
      success: (res: any) => {
        const { code } = res
        const state = `fit2cloud-lark-client`
        toUrl(`?code=${code}&state=${state}`)
      },
      fail: (error: any) => {
        const { errno, errString } = error
        ElMessage.error(`error code: ${errno}, error msg: ${errString}`)
      },
    })
  }
  if (window['tt'].requestAccess) {
    window['tt'].requestAccess({
      appID: appId,
      scopeList: [],
      success: (res: any) => {
        const { code } = res
        const state = `fit2cloud-lark-client`
        toUrl(`?code=${code}&state=${state}`)
      },
      fail: (error: any) => {
        const { errno, errString } = error
        if (errno === 103) {
          callRequestAuthCode()
        } else {
          ElMessage.error(`error code: ${errno}, error msg: ${errString}`)
        }
      },
    })
  } else {
    callRequestAuthCode()
  }
}

const larksuiteClientRequest = async () => {
  if (!window['tt'] || !window['h5sdk']) {
    ElMessage.error('load remote lark js error')
    return
  }
  const res = await queryClientInfo(9)
  if (!res?.data?.appId) {
    ElMessage.error('get appId error')
    return
  }
  const appId = res.data.appId

  window['h5sdk'].ready(() => {
    window['tt'].requestAuthCode({
      appId: appId,
      success(res: any) {
        const code = res?.code || res
        const state = `fit2cloud-larksuite-client`
        toUrl(`?code=${code}&state=${state}`)
      },
      fail(error: any) {
        const { errno, errString } = error
        ElMessage.error(`error code: ${errno}, error msg: ${errString}`)
      },
    })
  })
}

const toUrl = (url: string) => {
  const { origin, pathname } = window.location
  window.location.href = origin + pathname + url
}
