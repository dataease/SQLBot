<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { loadScript } from '@/utils/RemoteJs'
import type { BindingAttempt } from '@/api/account-binding'
const props = defineProps<{ attempt: BindingAttempt }>()
const emit = defineEmits<{ ready: []; scanned: [url: string]; code: [code: string]; error: [] }>()
const { t } = useI18n()
const container = ref<HTMLElement>()
const completionUrl = ref('')
let disposed = false
let cleanup: (() => void) | undefined
// SDK interfaces are confined to this provider adapter; never exposed to account state.
type WecomSdk = { createWWLoginPanel: (options: unknown) => { unmount: () => void } }
type QrSdk = { matchOrigin: (origin: string) => boolean; matchData?: (data: unknown) => boolean }
const sdkWindow = window as unknown as {
  ww: WecomSdk
  DTFrameLogin: (
    target: unknown,
    params: unknown,
    success: (result: { authCode?: string }) => void,
    error: () => void
  ) => void
  QRLogin: (options: unknown) => QrSdk
}
const id = 'binding-qr-' + props.attempt.origin
onMounted(async () => {
  const a = props.attempt
  try {
    if (a.origin === 6) {
      await loadScript(
        'https://wwcdn.weixin.qq.com/node/open/js/wecom-jssdk-2.3.3.js',
        'binding-wecom-sdk'
      )
      if (disposed) return
      const panel = sdkWindow.ww.createWWLoginPanel({
        el: '#' + id,
        params: {
          login_type: 'CorpApp',
          appid: a.client.corpid,
          agentid: a.client.agent_id,
          redirect_uri: a.callback_url,
          state: a.state,
          redirect_type: 'callback',
          panel_size: 'small',
        },
        onLoginSuccess: ({ code }: { code: string }) => {
          if (!disposed) emit('code', code)
        },
        onLoginFail: () => {
          if (!disposed) emit('error')
        },
      })
      cleanup = () => panel.unmount()
    } else if (a.origin === 7) {
      await loadScript(
        'https://g.alicdn.com/dingding/h5-dingtalk-login/0.21.0/ddlogin.js',
        'binding-dingtalk-sdk'
      )
      if (disposed) return
      sdkWindow.DTFrameLogin(
        { id },
        {
          client_id: a.client.client_id,
          redirect_uri: encodeURIComponent(a.callback_url),
          response_type: 'code',
          scope: 'openid',
          state: a.state,
          prompt: 'consent',
        },
        ({ authCode }) => {
          if (!disposed && authCode) emit('code', authCode)
        },
        () => {
          if (!disposed) emit('error')
        }
      )
    } else {
      const url =
        a.origin === 8
          ? 'https://lf-package-cn.feishucdn.com/obj/feishu-static/lark/passport/qrcode/LarkSSOSDKWebQRCode-1.0.3.js'
          : 'https://lf-package-us.larksuitecdn.com/obj/lark-static-us/lark/passport/qrcode/LarkSSOSDKWebQRCode-1.0.3.js'
      await loadScript(url, 'binding-lark-sdk')
      if (disposed) return
      const sdk = sdkWindow.QRLogin({
        id,
        goto: a.url,
        style: 'border:none;width:280px;height:280px;',
      })
      const listener = (event: MessageEvent) => {
        const frame = container.value?.querySelector('iframe')
        if (
          disposed ||
          !frame ||
          event.source !== frame.contentWindow ||
          !sdk.matchOrigin(event.origin) ||
          (sdk.matchData && !sdk.matchData(event.data))
        )
          return
        const code = event.data?.tmp_code
        if (typeof code !== 'string' || !code || code.length > 4096) return
        // Provider redirects this separate frame to our callback; the binding page stays put.
        const target = new URL(a.url)
        target.searchParams.set('tmp_code', code)
        completionUrl.value = target.href
        emit('scanned', completionUrl.value)
      }
      window.addEventListener('message', listener)
      cleanup = () => window.removeEventListener('message', listener)
    }
    if (!disposed) emit('ready')
  } catch {
    if (!disposed) emit('error')
  }
})
onBeforeUnmount(() => {
  disposed = true
  cleanup?.()
})
</script>
<template>
  <div ref="container" class="binding-qr"><div :id="id" /></div>
  <iframe
    v-if="completionUrl"
    :src="completionUrl"
    class="binding-completion"
    :title="t('binding.provider_auth')"
  />
</template>
<style scoped>
.binding-qr {
  width: 100%;
  min-height: 280px;
  margin: auto;
  overflow: hidden;
}
.binding-completion {
  width: 1px;
  height: 1px;
  border: 0;
  position: absolute;
  visibility: hidden;
}
</style>
