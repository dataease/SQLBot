<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { bindingApi } from '@/api/account-binding'
const { t } = useI18n()
const result = ref('binding.waiting')
onMounted(async () => {
  const params = new URLSearchParams(location.search)
  const state = params.get('state') || ''
  // Clear authorization artifacts before any API or script can report an error URL.
  history.replaceState(null, '', location.pathname + '#/account/binding-callback')
  if (!/^sqlbot_bind_[A-Za-z0-9_-]{40,64}$/.test(state)) {
    result.value = 'binding.expired'
    return
  }
  try {
    await bindingApi.callback({
      state,
      code: params.get('code') || params.get('authCode') || '',
      ticket: params.get('ticket') || '',
      error: params.get('error') || '',
    })
    result.value = 'binding.callback_done'
  } catch {
    result.value = 'binding.callback_failed'
  }
  const message = { type: 'sqlbot-binding-updated', state }
  // This is only a wakeup signal. The owner fetches the authoritative server result.
  try {
    window.opener?.postMessage(message, location.origin)
  } catch {
    /* COOP may sever opener. */
  }
  if (window.parent !== window) window.parent.postMessage(message, location.origin)
  if (window.parent === window) window.close()
})
</script>
<template>
  <main class="binding-callback">
    <h2>{{ t(result) }}</h2>
    <p>{{ t('binding.return_original') }}</p>
  </main>
</template>
<style scoped>
.binding-callback {
  padding: 48px;
  text-align: center;
}
</style>
