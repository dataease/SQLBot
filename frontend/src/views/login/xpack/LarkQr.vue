<template>
  <div id="de2-lark-qr" :class="{ 'de2-lark-qr': !isBind }" />
</template>

<script lang="ts" setup>
import { loadScript } from '@/utils/RemoteJs'
import { propTypes } from '@/utils/propTypes'
import { queryClientInfo } from './platformUtils'
import { getSQLBotAddr } from '@/utils/utils'
import { ref } from 'vue'
interface LarkQrInfo {
  client_id?: string
  state?: string
  redirect_uri?: string
}

const props = defineProps({
  isBind: propTypes.bool.def(false),
})
const origin = ref(8)
const remoteJsUrl =
  'https://lf-package-cn.feishucdn.com/obj/feishu-static/lark/passport/qrcode/LarkSSOSDKWebQRCode-1.0.3.js'
const jsId = 'de-lark-qr-id'
const init = () => {
  loadScript(remoteJsUrl, jsId).then(() => {
    queryClientInfo(origin.value).then((res: any) => {
      const data = formatQrResult(res) as any
      loadQr(data.client_id, data.state, data.redirect_uri)
    })
  })
}

const formatQrResult = (data: any): LarkQrInfo => {
  const result = { client_id: null, state: null, redirect_uri: null } as unknown as LarkQrInfo
  result.client_id = data.client_id
  result.state = 'fit2cloud-lark-qr'
  result.redirect_uri = data.redirect_uri || getSQLBotAddr()
  if (props.isBind) {
    result.state += '_de_bind'
  }
  return result
}

const loadQr = (CLIENT_ID: string, STATE: string, REDIRECT_URI: string) => {
  let url = `https://passport.feishu.cn/suite/passport/oauth/authorize?client_id=${CLIENT_ID}&response_type=code&state=${STATE}&redirect_uri=${REDIRECT_URI}`
  // eslint-disable-next-line
  // @ts-ignore
  const QRLoginObj = window['QRLogin']({
    id: 'de2-lark-qr',
    goto: url,
    style: 'border:none;background-color:#FFFFFF;width: 266px;height: 266px;',
  })
  const handleMessage = function (event: any) {
    const origin = event.origin
    if (QRLoginObj.matchOrigin(origin)) {
      const loginTmpCode = event.data
      url += '&tmp_code=' + loginTmpCode.tmp_code
      window.location.href = url
    }
  }
  if (typeof window.addEventListener != 'undefined') {
    window.addEventListener('message', handleMessage, false)
    // eslint-disable-next-line
    // @ts-ignore
  } else if (typeof window['attachEvent'] != 'undefined') {
    // eslint-disable-next-line
    // @ts-ignore
    window['attachEvent']('onmessage', handleMessage)
  }
}
init()
</script>
<style lang="less" scoped>
.de2-lark-qr {
  margin-top: -15px;
}
</style>
