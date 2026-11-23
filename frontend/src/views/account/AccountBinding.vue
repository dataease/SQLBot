<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { isAxiosError } from 'axios'
import { ElMessage } from 'element-plus-secondary'
import { useUserStore } from '@/stores/user'
import { userApi } from '@/api/auth'
import { getSQLBotAddr } from '@/utils/utils'
import {
  bindingApi,
  type BindingCapabilities,
  type Binding,
  type BindingAttempt,
  type BindingStatus,
} from '@/api/account-binding'
import BindingQr from './BindingQr.vue'
import AvatarIcon from '@/assets/img/Default-avatar.svg'
import lockIcon from '@/assets/svg/icon-key_outlined.svg?url'
import casIcon from '@/assets/svg/logo_cas.svg?url'
import oidcIcon from '@/assets/svg/logo_oidc.svg?url'
import oauthIcon from '@/assets/svg/logo_oauth.svg?url'
import wecomIcon from '@/assets/svg/logo_wechat-work.svg?url'
import dingIcon from '@/assets/svg/logo_dingtalk.svg?url'
import larkIcon from '@/assets/svg/logo_lark.svg?url'
const { t } = useI18n()
const user = useUserStore()
const items = ref<Binding[]>([])
const capabilities = ref<BindingCapabilities>()
const tab = ref('bindings')
const workspaceName = ref('')
const selected = ref<Binding>()
const dialog = ref(false)
const step = ref<'password' | 'auth' | 'confirm' | 'unbind' | 'failed'>('password')
const pwd = ref('')
const operationError = ref('')
const loadError = ref('')
const busy = ref(false)
const attempt = ref<BindingAttempt>()
const identity = ref<BindingStatus>()
const qrState = ref<'loading' | 'waiting' | 'verifying' | 'error'>('loading')
const qrCompletionUrl = ref('')
const timedOut = ref(false)
let epoch = 0
let profileEpoch = 0
let timer: ReturnType<typeof setTimeout> | undefined
let clock: ReturnType<typeof setInterval> | undefined
let popup: Window | null = null
const icons: Record<number, string> = {
  1: casIcon,
  2: oidcIcon,
  4: oauthIcon,
  6: wecomIcon,
  7: dingIcon,
  8: larkIcon,
  9: larkIcon,
}
const name = (origin: number) =>
  ({
    1: 'CAS',
    2: 'OIDC',
    4: 'OAuth2',
    6: t('user.wecom'),
    7: t('user.dingtalk'),
    8: t('user.lark'),
    9: t('user.larksuite'),
  })[origin]
const accountType = computed(() =>
  user.getOrigin === 0
    ? t('binding.local')
    : name(user.getOrigin) ||
      ({ 3: 'LDAP', 5: 'SAML2' } as Record<number, string>)[user.getOrigin] ||
      t('binding.third_party')
)
const isQr = computed(() => (selected.value?.origin || 0) > 5)
const localAccount = computed(() => !user.getOrigin)
const available = computed(() => localAccount.value && !!capabilities.value?.show_bindings)
const canBind = computed(() => available.value && !!capabilities.value?.can_bind)
const activeTab = computed(() => (available.value ? tab.value : 'basic'))
const errorText = (e: unknown) =>
  isAxiosError(e) && typeof e.response?.data === 'string' ? e.response.data : t('binding.service')
const stop = () => {
  clearTimeout(timer)
  clearInterval(clock)
}
const loadWorkspace = async () => {
  try {
    const options: { id: string | number; name: string }[] = await userApi.ws_options()
    workspaceName.value =
      options.find((option) => String(option.id) === String(user.getOid))?.name || ''
  } catch {
    // The profile remains readable when workspace metadata is temporarily unavailable.
  }
}
const load = async () => {
  const version = ++profileEpoch
  loadError.value = ''
  if (!localAccount.value) return
  try {
    const result = await bindingApi.capabilities()
    if (version !== profileEpoch || !localAccount.value) return
    capabilities.value = result
    if (!result.show_bindings) {
      items.value = []
      return
    }
    const bindings = await bindingApi.list()
    if (version === profileEpoch && localAccount.value) items.value = bindings
  } catch (e) {
    if (version === profileEpoch && localAccount.value) loadError.value = errorText(e)
  }
}
const closePopup = () => {
  try {
    popup?.close()
  } catch {
    /* Browser policy may prevent closing. */
  }
  popup = null
}
const cancel = async () => {
  epoch++
  stop()
  closePopup()
  dialog.value = false
  operationError.value = ''
  busy.value = false
  pwd.value = ''
  selected.value = undefined
  identity.value = undefined
  timedOut.value = false
  qrCompletionUrl.value = ''
  const state = attempt.value?.state
  attempt.value = undefined
  if (state) {
    try {
      await bindingApi.cancel(state)
    } catch {
      /* Server expiry is the final fallback. */
    }
  }
}
const choose = (item: Binding) => {
  if (!available.value || (!item.bound && !canBind.value)) return
  epoch++
  timedOut.value = false
  selected.value = item
  attempt.value = undefined
  identity.value = undefined
  pwd.value = ''
  operationError.value = ''
  step.value = item.bound ? 'unbind' : 'password'
  dialog.value = true
}
const expire = () => {
  const state = attempt.value?.state
  epoch++
  stop()
  closePopup()
  step.value = 'failed'
  busy.value = false
  timedOut.value = true
  operationError.value = t('binding.timeout')
  if (state)
    void bindingApi.cancel(state).catch(() => {
      /* Server expiry also rejects old callbacks. */
    })
}
const hasExpired = () => {
  if (attempt.value && Date.now() >= attempt.value.expires_at * 1000) {
    expire()
    return true
  }
  return false
}
const poll = async (version: number) => {
  const a = attempt.value
  if (!a || version !== epoch || step.value !== 'auth') return
  if (hasExpired()) return
  try {
    const result = await bindingApi.status(a.state)
    if (version !== epoch || attempt.value?.state !== a.state || step.value !== 'auth') return
    if (hasExpired()) return
    if (result.status === 'exchanging') qrState.value = 'verifying'
    if (result.status === 'verified') {
      stop()
      closePopup()
      identity.value = result
      step.value = 'confirm'
      return
    }
    if (['failed', 'conflict', 'cancelled'].includes(result.status)) {
      stop()
      closePopup()
      step.value = 'failed'
      operationError.value = t(
        result.status === 'conflict' ? 'binding.conflict' : 'binding.service'
      )
      return
    }
  } catch (e) {
    if (version !== epoch || step.value !== 'auth') return
    stop()
    step.value = 'failed'
    operationError.value = errorText(e)
    return
  }
  timer = setTimeout(() => {
    void poll(version)
  }, 1500)
}
const waitFor = (a: BindingAttempt) => {
  stop()
  attempt.value = a
  step.value = 'auth'
  qrState.value = 'loading'
  qrCompletionUrl.value = ''
  timedOut.value = false
  if (hasExpired()) return
  clock = setInterval(hasExpired, 1000)
  void poll(epoch)
}
const verify = async () => {
  if (!pwd.value || busy.value || !selected.value) return
  const version = ++epoch
  busy.value = true
  operationError.value = ''
  try {
    const a = await bindingApi.start(selected.value.origin, pwd.value, getSQLBotAddr())
    if (version !== epoch) {
      await bindingApi.cancel(a.state)
      return
    }
    pwd.value = ''
    waitFor(a)
  } catch (e) {
    if (version === epoch) operationError.value = errorText(e)
  } finally {
    if (version === epoch) busy.value = false
  }
}
const openAuth = (url?: string) => {
  if (!attempt.value || step.value !== 'auth' || hasExpired()) return
  popup = window.open(
    url || attempt.value.url,
    'sqlbot-account-binding',
    'popup,width=640,height=760'
  )
  if (!popup) operationError.value = t('binding.popup_blocked')
}
const refresh = async () => {
  const a = attempt.value
  if (!a || busy.value || qrState.value === 'verifying' || hasExpired()) return
  busy.value = true
  operationError.value = ''
  stop()
  const version = ++epoch
  try {
    const next = await bindingApi.refresh(a.state)
    if (version === epoch) waitFor(next)
    else await bindingApi.cancel(next.state)
  } catch (e) {
    if (version === epoch) {
      operationError.value = errorText(e)
      step.value = 'failed'
    }
  } finally {
    if (version === epoch) busy.value = false
  }
}
const qrCode = async (code: string) => {
  const a = attempt.value
  const version = epoch
  if (!a || step.value !== 'auth' || qrState.value === 'verifying' || hasExpired()) return
  qrState.value = 'verifying'
  try {
    await bindingApi.callback({ state: a.state, code, ticket: '', error: '' })
    if (version === epoch && step.value === 'auth') {
      clearTimeout(timer)
      await poll(version)
    }
  } catch (e) {
    if (version === epoch) {
      stop()
      operationError.value = errorText(e)
      step.value = 'failed'
    }
  }
}
const confirm = async () => {
  if (!attempt.value || busy.value) return
  const version = ++epoch
  busy.value = true
  operationError.value = ''
  try {
    await bindingApi.confirm(attempt.value.state)
    if (version !== epoch) return
    ElMessage.success(t('binding.bound_success'))
    // End the UI operation immediately; server cancellation must not delay the refresh.
    void cancel()
    await load()
  } catch (e) {
    if (version === epoch) operationError.value = errorText(e)
  } finally {
    if (version === epoch) busy.value = false
  }
}
const unbind = async () => {
  if (!selected.value || !pwd.value || busy.value) return
  const version = ++epoch
  busy.value = true
  operationError.value = ''
  try {
    await bindingApi.unbind(selected.value.origin, pwd.value)
    if (version !== epoch) return
    ElMessage.success(t('binding.unbound_success'))
    // End the UI operation immediately; server cancellation must not delay the refresh.
    void cancel()
    await load()
  } catch (e) {
    if (version === epoch) operationError.value = errorText(e)
  } finally {
    if (version === epoch) busy.value = false
  }
}
const retry = () => {
  const item = selected.value
  void cancel()
  if (item) choose({ ...item, bound: false })
}
const onMessage = (event: MessageEvent) => {
  if (
    event.origin !== location.origin ||
    event.data?.type !== 'sqlbot-binding-updated' ||
    event.data.state !== attempt.value?.state
  )
    return
  const qrFrame = document.querySelector<HTMLIFrameElement>('.binding-completion')
  if (!event.source || (event.source !== popup && event.source !== qrFrame?.contentWindow)) return
  clearTimeout(timer)
  void poll(epoch)
}
watch(
  activeTab,
  (value, previous) => {
    if (previous === 'bindings' && value !== 'bindings') void cancel()
  },
  { flush: 'sync' }
)
watch(localAccount, (allowed) => {
  loadError.value = ''
  profileEpoch++
  capabilities.value = undefined
  tab.value = 'basic'
  if (allowed) void load()
  else {
    void cancel()
    items.value = []
    operationError.value = ''
  }
})
onMounted(() => {
  void loadWorkspace()
  if (localAccount.value) void load()
  window.addEventListener('message', onMessage)
})
onBeforeUnmount(() => {
  profileEpoch++
  void cancel()
  window.removeEventListener('message', onMessage)
})
</script>
<template>
  <main class="account-page no-padding">
    <header class="account-header">
      <h1>{{ t('binding.personal') }}</h1>
    </header>
    <div class="account-tabs" role="tablist" :aria-label="t('binding.personal')">
      <button
        type="button"
        role="tab"
        :aria-selected="activeTab === 'basic'"
        @click="tab = 'basic'"
      >
        {{ t('binding.basic') }}
      </button>
      <button
        v-if="available"
        type="button"
        role="tab"
        :aria-selected="activeTab === 'bindings'"
        @click="tab = 'bindings'"
      >
        {{ t('binding.title') }}
      </button>
    </div>
    <div class="account-content">
      <section class="account-summary">
        <AvatarIcon class="user-avatar" aria-hidden="true" />
        <div>
          <h2>
            {{ user.getName }} <span class="account-tag">{{ accountType }}</span>
          </h2>
          <p>
            {{ user.getAccount
            }}<template v-if="workspaceName"
              ><span class="workspace-separator" aria-hidden="true">{{ ' · ' }}</span
              >{{ workspaceName }}</template
            >
          </p>
        </div>
      </section>
      <el-alert
        v-if="loadError && !dialog && (activeTab === 'bindings' || !capabilities)"
        :title="loadError"
        type="error"
        :closable="false"
      />
      <section
        v-if="activeTab === 'basic'"
        class="basic-details"
        :aria-label="t('binding.account_info')"
      >
        <h2>{{ t('binding.account_info') }}</h2>
        <dl>
          <dt>{{ t('binding.user_name') }}</dt>
          <dd>{{ user.getName }}</dd>
          <dt>{{ t('user.account') }}</dt>
          <dd>{{ user.getAccount }}</dd>
          <dt>{{ t('user.email') }}</dt>
          <dd>{{ user.getEmail || '—' }}</dd>
          <dt>{{ t('binding.account_type') }}</dt>
          <dd>{{ accountType }}</dd>
        </dl>
      </section>
      <template v-else-if="available">
        <div class="section-heading">
          <h2>{{ t('binding.third_party') }}</h2>
          <p>{{ t(canBind ? 'binding.description' : 'binding.manage_existing') }}</p>
        </div>
        <div v-for="item in items" :key="item.origin" class="binding-row">
          <img :src="icons[item.origin]" alt="" />
          <div class="binding-info">
            <h3>{{ name(item.origin) }}</h3>
            <p class="muted">
              {{
                item.bound
                  ? `${item.display_name || item.account} · ${item.account}`
                  : item.enabled
                    ? t(item.origin > 5 ? 'binding.scan' : 'binding.provider_auth')
                    : t('binding.disabled')
              }}
            </p>
            <p v-if="item.stale" class="muted">{{ t('binding.stale') }}</p>
          </div>
          <span class="binding-status" :class="{ bound: item.bound }"
            ><span v-if="item.bound" aria-hidden="true">✓</span
            >{{
              t(
                item.bound ? 'binding.bound' : item.enabled ? 'binding.unbound' : 'binding.disabled'
              )
            }}</span
          >
          <el-button :disabled="!item.bound && (!item.enabled || !canBind)" @click="choose(item)">{{
            t(item.bound ? 'binding.unbind' : 'binding.bind')
          }}</el-button>
        </div>
        <p class="binding-footnote"><img :src="lockIcon" alt="" />{{ t('binding.preserve') }}</p>
      </template>
    </div>
    <el-dialog
      v-if="available"
      v-model="dialog"
      :title="
        t(
          step === 'password'
            ? 'binding.verify_title'
            : step === 'unbind'
              ? 'binding.unbind'
              : step === 'confirm'
                ? 'binding.confirm'
                : 'binding.bind'
        )
      "
      width="520"
      class="binding-dialog"
      :close-on-click-modal="false"
      :close-on-press-escape="!busy"
      :show-close="!busy"
      :before-close="() => cancel()"
    >
      <div
        v-if="['password', 'auth', 'confirm'].includes(step) || (timedOut && isQr)"
        class="binding-steps"
        :aria-label="t('binding.steps')"
      >
        <span :class="{ current: step === 'password' }">1 {{ t('binding.verify_identity') }}</span
        ><i />
        <span :class="{ current: step === 'auth' || (timedOut && isQr) }"
          >2 {{ t('binding.platform_auth') }}</span
        ><i />
        <span :class="{ current: step === 'confirm' }">3 {{ t('binding.confirm') }}</span>
      </div>
      <template v-if="step === 'password' || step === 'unbind'">
        <p class="dialog-description">
          {{ t(step === 'unbind' ? 'binding.unbind_hint' : 'binding.password_hint') }}
        </p>
        <el-form label-position="top" @submit.prevent="step === 'unbind' ? unbind() : verify()">
          <el-form-item :label="t('user.account')"
            ><el-input :model-value="user.getAccount" disabled
          /></el-form-item>
          <el-form-item :label="t('binding.password')"
            ><el-input
              v-model="pwd"
              type="password"
              show-password
              autocomplete="current-password"
              @keyup.enter="step === 'unbind' ? unbind() : verify()"
          /></el-form-item>
        </el-form>
      </template>
      <template v-if="attempt && (step === 'auth' || (timedOut && isQr))">
        <div v-if="isQr" class="qr-auth">
          <div class="provider-heading">
            <img :src="icons[selected!.origin]" alt="" />{{ name(selected!.origin) }}
          </div>
          <div class="qr-stage" :aria-busy="qrState === 'loading' || qrState === 'verifying'">
            <BindingQr
              v-if="!timedOut"
              :key="attempt.state"
              :attempt="attempt"
              @ready="qrState = 'waiting'"
              @code="qrCode"
              @scanned="qrCompletionUrl = $event"
              @error="qrState = 'error'"
            />
            <div v-if="timedOut || qrState !== 'waiting'" class="qr-overlay" role="status">
              <span>{{ t(timedOut ? 'binding.timeout' : 'binding.qr_' + qrState) }}</span>
              <el-button v-if="!timedOut && qrState === 'error'" :loading="busy" @click="refresh">
                {{ t('binding.refresh') }}
              </el-button>
            </div>
          </div>
          <div class="qr-assistance">
            <p v-if="!timedOut" class="qr-instruction">
              {{ t('binding.scan_with', { platform: name(selected!.origin) }) }}
            </p>
            <p v-if="!timedOut && qrCompletionUrl && qrState === 'waiting'" role="status">
              {{ t('binding.scan_complete') }}
              <el-button link type="primary" @click="openAuth(qrCompletionUrl)">{{
                t('binding.complete_auth')
              }}</el-button>
            </p>
            <el-button
              v-if="!timedOut && qrState !== 'error'"
              link
              type="primary"
              :loading="busy"
              :disabled="qrState !== 'waiting'"
              @click="refresh"
              >{{ t('binding.refresh') }}</el-button
            >
          </div>
        </div>
        <div v-else class="auth-waiting">
          <img :src="icons[selected!.origin]" alt="" />
          <p>{{ t('binding.waiting') }}</p>
          <p>{{ t('binding.window_hint') }}</p>
          <el-button type="primary" @click="openAuth()">{{ t('binding.open_auth') }}</el-button>
        </div>
      </template>
      <div v-if="step === 'confirm' && identity" class="binding-confirm">
        <p>{{ t('binding.confirm_hint') }}</p>
        <div class="identity-summary">
          <div>
            <AvatarIcon class="user-avatar" aria-hidden="true" />
            <div>
              <strong>{{ user.getName }}</strong
              ><small>SQLBot · {{ user.getAccount }}</small>
            </div>
          </div>
          <span class="identity-arrow" aria-hidden="true">↓</span>
          <div>
            <img :src="icons[selected!.origin]" alt="" />
            <div>
              <strong>{{ identity.display_name || identity.account }}</strong
              ><small>{{ name(selected!.origin) }} · {{ identity.account }}</small>
            </div>
          </div>
        </div>
        <p class="binding-footnote">{{ t('binding.preserve') }}</p>
      </div>
      <el-alert
        v-if="operationError && !(timedOut && isQr)"
        :title="operationError"
        type="error"
        :closable="false"
      />
      <template #footer>
        <el-button :disabled="busy" @click="cancel">{{ t('common.cancel') }}</el-button>
        <el-button
          v-if="step === 'password'"
          type="primary"
          :loading="busy"
          :disabled="!pwd"
          @click="verify"
          >{{ t('binding.next') }}</el-button
        >
        <el-button v-if="step === 'confirm'" type="primary" :loading="busy" @click="confirm">{{
          t('binding.confirm')
        }}</el-button>
        <el-button
          v-if="step === 'unbind'"
          type="danger"
          :loading="busy"
          :disabled="!pwd"
          @click="unbind"
          >{{ t('binding.confirm_unbind') }}</el-button
        >
        <el-button v-if="step === 'failed'" @click="retry">{{ t('binding.retry') }}</el-button>
      </template>
    </el-dialog>
  </main>
</template>
<style scoped lang="less">
.account-page {
  width: 100%;
  height: 100%;
  overflow: auto;
  color: #1f2329;
  font-family:
    var(--de-custom_font, -apple-system), BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
    'Microsoft YaHei', sans-serif;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
  letter-spacing: 0;
  background: #fff;
}
.account-header {
  height: 74px;
  padding: 26px 32px 20px;
  border-bottom: 1px solid #eff0f1;
  h1 {
    font-size: 20px;
    font-weight: 500;
    line-height: 30px;
    margin: 0;
  }
}
.account-tabs {
  display: flex;
  gap: 30px;
  padding: 0 32px;
  height: 54px;
  border-bottom: 1px solid #dee0e3;
  button {
    border: 0;
    border-bottom: 2px solid transparent;
    background: transparent;
    padding: 0 2px;
    font: inherit;
    color: inherit;
    cursor: pointer;
  }
  button[aria-selected='true'] {
    color: #159b78;
    border-bottom-color: #1cba90;
  }
}
.account-content {
  max-width: 1060px;
  padding: 32px 40px 48px;
}
.account-summary {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 30px;
  border-bottom: 1px solid #eff0f1;
  > .user-avatar {
    width: 56px;
    height: 56px;
    flex-shrink: 0;
  }
  h2 {
    font-size: 18px;
    font-weight: 500;
    line-height: 1.5;
    margin: 0;
  }
  p {
    color: #646a73;
    font-size: 13px;
    margin-top: 6px;
  }
}
.workspace-separator {
  margin: 0 9px;
}
.basic-details {
  padding-top: 28px;
  h2 {
    font-size: 16px;
    font-weight: 500;
    line-height: 24px;
    margin: 0;
  }
  dl {
    display: grid;
    grid-template-columns: 120px minmax(0, 1fr);
    gap: 24px;
    margin: 14px 0;
  }
  dt {
    color: #646a73;
  }
  dt,
  dd {
    font-size: 14px;
    font-weight: 400;
    line-height: 21px;
    margin: 0;
  }
  dd {
    overflow-wrap: anywhere;
  }
}
.account-tag {
  font-size: 12px;
  font-weight: 400;
  background: #f2f4f6;
  border: 1px solid #e3e6e9;
  padding: 2px 7px;
  border-radius: 4px;
  margin-left: 8px;
  vertical-align: middle;
  color: #646a73;
}
.section-heading {
  padding: 26px 0 10px;
  h2 {
    font-size: 16px;
    font-weight: 500;
    margin: 0;
  }
  p {
    color: #646a73;
    font-size: 13px;
    margin-top: 7px;
  }
}
.binding-row {
  min-height: 91px;
  display: flex;
  align-items: center;
  gap: 18px;
  border-bottom: 1px solid #eff0f1;
  padding: 18px 0;
  > img {
    width: 36px;
    height: 36px;
    flex-shrink: 0;
  }
  h3 {
    font-size: 14px;
    font-weight: 500;
    margin: 0;
  }
  .ed-button {
    min-width: 88px;
    height: 34px;
    padding: 0 16px;
  }
}
.binding-info {
  flex: 1;
  min-width: 0;
  p {
    color: #8a9099;
    font-size: 12px;
    margin-top: 5px;
    overflow-wrap: anywhere;
  }
}
.binding-status {
  color: #8a9099;
  font-size: 12px;
  width: 86px;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  &.bound {
    color: #159b78;
  }
}
.binding-footnote {
  font-size: 12px;
  color: #8a9099;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 22px;
  img {
    width: 14px;
    height: 14px;
  }
}
.binding-steps {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #a5a9af;
  font-size: 12px;
  margin: 26px 0;
  i {
    height: 1px;
    background: #dee0e3;
    flex: 1;
  }
  .current {
    color: #159b78;
  }
}
.dialog-description {
  color: #646a73;
  line-height: 1.8;
  margin: 18px 0 22px;
}
.qr-auth {
  text-align: center;
  > p {
    color: #8a9099;
    font-size: 12px;
    margin: 18px 0;
  }
}
.qr-assistance {
  min-height: 88px;
  color: #8a9099;
  font-size: 12px;
  p {
    margin: 18px 0;
  }
}
.qr-stage {
  position: relative;
  width: 300px;
  height: 300px;
  margin: auto;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}
.qr-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: #fff;
  color: #646a73;
  font-size: 14px;
  padding: 24px;
  line-height: 1.6;
}
.provider-heading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 18px;
  img {
    width: 24px;
    height: 24px;
  }
}
.auth-waiting {
  text-align: center;
  padding: 8px 0;
  > img {
    width: 36px;
    height: 36px;
  }
  > p {
    color: #646a73;
    margin: 16px 0;
  }
}
.binding-confirm > p:first-child {
  color: #646a73;
  margin: 18px 0 22px;
}
.identity-summary {
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: #f7f9f8;
  padding: 20px;
  border-radius: 6px;
  > div {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }
  img,
  .user-avatar {
    width: 32px;
    height: 32px;
    flex-shrink: 0;
  }
  strong {
    display: block;
    font-weight: 500;
    overflow-wrap: anywhere;
  }
  small {
    display: block;
    color: #646a73;
    margin-top: 2px;
    overflow-wrap: anywhere;
  }
  .identity-arrow {
    margin-left: 7px;
    color: #99a3a7;
  }
}
@media (max-width: 1000px) {
  .account-content {
    padding: 28px;
  }
}
@media (max-width: 600px) {
  .account-header {
    height: 66px;
    padding: 20px;
  }
  .account-tabs {
    padding: 0 20px;
    gap: 24px;
  }
  .account-content {
    padding: 24px 18px 48px;
  }
  .account-summary {
    gap: 10px;
    > .user-avatar {
      width: 40px;
      height: 40px;
    }
    h2 {
      font-size: 16px;
    }
    p {
      font-size: 11px;
    }
    .workspace-separator {
      margin: 0 4px;
    }
    .account-tag {
      margin-left: 3px;
      font-size: 10px;
    }
  }
  .binding-info {
    flex-basis: calc(100% - 40px);
  }
  .binding-row {
    gap: 10px;
    flex-wrap: wrap;
    > img {
      width: 28px;
      height: 28px;
    }
    .ed-button {
      min-width: 72px;
      height: 30px;
      font-size: 12px;
    }
  }
  .binding-status {
    margin-left: 38px;
    flex: 1;
  }
  .binding-steps {
    gap: 6px;
    font-size: 11px;
  }
}
</style>
<style lang="less">
.binding-dialog.ed-dialog {
  padding: 24px;
  max-width: calc(100vw - 32px);
  border-radius: 12px;
}
.binding-dialog .ed-dialog__title {
  font-size: 18px;
  font-weight: 500;
}
.binding-dialog .ed-dialog__body {
  padding: 0;
  color: #1f2329;
  font-size: 14px;
}
.binding-dialog .ed-dialog__footer {
  padding: 0;
  margin-top: 26px;
}
.binding-dialog .ed-form-item {
  margin-bottom: 20px;
}
.binding-dialog .ed-form-item__label {
  font-size: 13px;
  margin-bottom: 8px;
}
.binding-dialog .ed-input__wrapper {
  min-height: 40px;
}
.binding-dialog .ed-button {
  height: 34px;
  padding: 0 16px;
}
</style>
