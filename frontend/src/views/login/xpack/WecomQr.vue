<template>
  <div id="sqlbot-wecom-qr" :class="isBind ? 'sqlbot-wecom-bind-qr' : 'sqlbot-wecom-qr'" />
</template>

<script lang="ts" setup>
import { loadScript } from '@/utils/RemoteJs'
import { propTypes } from '@/utils/propTypes'
import { onUnmounted, ref } from 'vue'
import { getLocale, getSQLBotAddr } from '@/utils/utils'
import { queryClientInfo } from './platformUtils'
interface WecomInfo {
  corp_id: string
  agent_id: string
  state: string
  redirect_uri: string
}

const props = defineProps({
  isBind: propTypes.bool.def(false),
})
const origin = ref(6)
// const emit = defineEmits(['finish'])
let wwLogin = null as any
const remoteJsUrl = 'https://wwcdn.weixin.qq.com/node/open/js/wecom-jssdk-2.3.3.js'
const jsId = 'sqlbot-wecom-qr-id'
const init = () => {
  loadScript(remoteJsUrl, jsId).then(() => {
    queryClientInfo(origin.value).then((res) => {
      const data = formatQrResult(res)
      loadQr(data.corp_id, data.agent_id, data.state, data.redirect_uri)
    })
  })
}

const formatQrResult = (data: any): WecomInfo => {
  const result = {
    corp_id: null,
    agent_id: null,
    state: null,
    redirect_uri: null,
  } as unknown as WecomInfo
  result.corp_id = data.corpid
  result.agent_id = data.agent_id
  result.state = data.state || 'fit2cloud-wecom-qr'
  result.redirect_uri = data.redirect_uri || getSQLBotAddr()
  if (props.isBind) {
    result.state += '_sqlbot_bind'
  }
  return result
}

const loadQr = (CORP_ID: string, AGENT_ID: string, STATE: string, REDIRECT_URI: string) => {
  // eslint-disable-next-line
  // @ts-ignore
  // eslint-disable-next-line no-undef
  wwLogin = ww.createWWLoginPanel({
    el: '#sqlbot-wecom-qr',
    params: {
      login_type: 'CorpApp',
      appid: CORP_ID,
      agentid: AGENT_ID,
      redirect_uri: REDIRECT_URI,
      state: STATE,
      redirect_type: 'callback',
      lang: getLocale() === 'en' ? 'en' : 'zh',
    },
    onCheckWeComLogin({ isWeComLogin }: { isWeComLogin: boolean }) {
      console.log(isWeComLogin)
    },
    onLoginSuccess({ code }: { code: string }) {
      window.location.href = REDIRECT_URI + `?code=${code}&state=${STATE}`
    },
    onLoginFail(err: any) {
      console.log(err)
    },
  })
}

onUnmounted(() => {
  if (wwLogin) {
    wwLogin.unmount()
  }
})
init()
</script>
<style lang="less" scoped>
.sqlbot-wecom-qr {
  margin-top: -55px;
}
.sqlbot-wecom-bind-qr {
  margin-top: -20px;
}
</style>
