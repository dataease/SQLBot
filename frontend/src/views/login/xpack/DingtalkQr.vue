<template>
  <div class="dingtalk-qr-div">
    <div id="de2-dingtalk-qr" :class="{ 'de2-dingtalk-qr': !isBind }" />
  </div>
</template>

<script lang="ts" setup>
import { loadScript } from '@/utils/RemoteJs'
import { propTypes } from '@/utils/propTypes'
import { getSQLBotAddr } from '@/utils/utils'
import { ref } from 'vue'
import { queryClientInfo } from './platformUtils'
interface DingtalkQrInfo {
  client_id: string
  state: string
  redirect_uri: string
}

const props = defineProps({
  isBind: propTypes.bool.def(false),
})
const origin = ref(7)
const remoteJsUrl = 'https://g.alicdn.com/dingding/h5-dingtalk-login/0.21.0/ddlogin.js'
const jsId = 'de-dingtalk-qr-id'
const init = () => {
  loadScript(remoteJsUrl, jsId).then(() => {
    queryClientInfo(origin.value).then((res: any) => {
      const data = formatQrResult(res)
      loadQr(data.client_id, data.state, data.redirect_uri)
    })
  })
}

const formatQrResult = (data: any): DingtalkQrInfo => {
  const result = { client_id: null, state: null, redirect_uri: null } as unknown as DingtalkQrInfo
  result.client_id = data.client_id
  result.state = 'fit2cloud-dingtalk-qr'
  result.redirect_uri = data.redirect_uri || getSQLBotAddr()
  if (props.isBind) {
    result.state += '_de_bind'
  }
  return result
}

const loadQr = (client_id: string, STATE: string, REDIRECT_URI: string) => {
  // eslint-disable-next-line
  // @ts-ignore
  window.DTFrameLogin(
    {
      id: 'de2-dingtalk-qr',
    },
    {
      redirect_uri: encodeURIComponent(REDIRECT_URI),
      client_id: client_id,
      scope: 'openid',
      response_type: 'code',
      state: STATE,
      prompt: 'consent',
    },
    (loginResult: any) => {
      const { redirectUrl, authCode } = loginResult
      // 这里可以直接进行重定向
      window.location.href = redirectUrl
      // 也可以在不跳转页面的情况下，使用code进行授权
      console.log(authCode)
    },
    (errorMsg: any) => {
      // 这里一般需要展示登录失败的具体原因,可以使用toast等轻提示
      console.error(`errorMsg of errorCbk: ${errorMsg}`)
    }
  )
}
init()
</script>
<style lang="less" scoped>
.dingtalk-qr-div {
  // margin-top: -36px;
  width: 234px;
  height: 234px;
  .de2-dingtalk-qr {
    transform: scale(1.3);
    transform-origin: top left;
    width: 234px;
    height: 234px;
    margin: -80px;
  }
}
</style>
