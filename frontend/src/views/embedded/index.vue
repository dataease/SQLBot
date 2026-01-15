<template>
  <div class="sqlbot-assistant-container">
    <div class="header" :style="{ color: customSet.header_font_color }">
      <el-icon size="20"> </el-icon>
      <el-icon v-if="!logo" class="logo" size="30">
        <LOGO></LOGO>
      </el-icon>
      <img v-else :src="logo" class="logo" width="30px" height="30px" alt="" />
      <span
        :title="appName || $t('embedded.intelligent_customer_service')"
        class="title ellipsis"
        >{{ appName || $t('embedded.intelligent_customer_service') }}</span
      >

      <el-tooltip effect="dark" :content="$t('embedded.new_conversation')" placement="top">
        <el-icon class="new-chat" size="20" @click="createChat">
          <icon_new_chat_outlined></icon_new_chat_outlined>
        </el-icon>
      </el-tooltip>
    </div>
    <div class="sqlbot-chat-container">
      <chat-component
        v-if="!loading"
        ref="chatRef"
        :welcome="customSet.welcome"
        :welcome-desc="customSet.welcome_desc"
        :logo-assistant="logo"
      />
    </div>
    <div class="drawer-assistant" @click="openHistory"></div>
  </div>
</template>
<script setup lang="ts">
import { onBeforeMount, nextTick, onBeforeUnmount, ref, onMounted, reactive } from 'vue'
import ChatComponent from '@/views/chat/index.vue'
import { request } from '@/utils/request'
import LOGO from '@/assets/svg/logo-custom_small.svg'
import icon_new_chat_outlined from '@/assets/svg/icon_new_chat_outlined.svg'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import { useRoute } from 'vue-router'
import { assistantApi } from '@/api/assistant'
import { useAssistantStore } from '@/stores/assistant'
import { setCurrentColor } from '@/utils/utils'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const assistantStore = useAssistantStore()
const appearanceStore = useAppearanceStoreWithOut()
const route = useRoute()
const chatRef = ref()

const createChat = () => {
  chatRef.value?.createNewChat()
}
const openHistory = () => {
  chatRef.value?.showFloatPopover()
}

const validator = ref({
  id: '',
  valid: false,
  id_match: false,
  token: '',
})
const appName = ref('')
const loading = ref(true)
const eventName = 'sqlbot_assistant_event'
const communicationCb = async (event: any) => {
  if (event.data?.eventName === eventName) {
    if (event.data?.messageId !== route.query.id) {
      return
    }
    if (event.data?.busi == 'certificate') {
      const certificate = event.data['certificate']
      assistantStore.setType(1)
      assistantStore.setCertificate(certificate)
      assistantStore.resolveCertificate(certificate)
    }
    if (event.data?.hostOrigin) {
      assistantStore.setHostOrigin(event.data?.hostOrigin)
    }
    if (event.data?.busi == 'setOnline') {
      setFormatOnline(event.data.online)
    }
    if (event.data?.busi == 'setHistory') {
      assistantStore.setHistory(event.data.show ?? true)
    }
    if (event.data?.busi == 'createConversation') {
      createChat()
    }
  }
}
const setFormatOnline = (text?: any) => {
  if (text === null || typeof text === 'undefined') {
    assistantStore.setOnline(false)
    return
  }
  if (typeof text === 'boolean') {
    assistantStore.setOnline(text)
    return
  }
  if (typeof text === 'string') {
    assistantStore.setOnline(text.toLowerCase() === 'true')
    return
  }
  assistantStore.setOnline(false)
}

onMounted(() => {
  const style = document.createElement('style')
  style.innerHTML = `.ed-overlay-dialog {
        margin-top: 50px;
      }
      .ed-drawer {
        margin-top: 50px;
        height: calc(100vh - 50px) !important;
      }`
  document.querySelector('head')?.appendChild(style)
})
const customSet = reactive({
  name: '',
  welcome: t('embedded.i_am_sqlbot'),
  welcome_desc: t('embedded.data_analysis_now'),
  theme: '#1CBA90',
  header_font_color: '#1F2329',
}) as { [key: string]: any }
const logo = ref()
const basePath = import.meta.env.VITE_API_BASE_URL
const baseUrl = basePath + '/system/assistant/picture/'
const setPageCustomColor = (val: any) => {
  const ele = document.querySelector('body') as HTMLElement
  setCurrentColor(val, ele)
}

const setPageHeaderFontColor = (val: any) => {
  const ele = document.querySelector('body') as HTMLElement
  ele.style.setProperty('--ed-text-color-primary', val)
}
onBeforeMount(async () => {
  const assistantId = route.query.id
  if (!assistantId) {
    ElMessage.error('Miss assistant id, please check assistant url')
    return
  }

  const online = route.query.online
  setFormatOnline(online)

  let userFlag = route.query.userFlag
  if (userFlag && userFlag === '1') {
    userFlag = '100001'
  }

  const history: boolean = route.query.history !== 'false'
  assistantStore.setHistory(history)

  const now = Date.now()
  assistantStore.setFlag(now)
  assistantStore.setId(assistantId?.toString() || '')
  const param = {
    id: assistantId,
    virtual: userFlag || assistantStore.getFlag,
    online,
  }
  validator.value = await assistantApi.validate(param)
  assistantStore.setToken(validator.value.token)
  assistantStore.setAssistant(true)
  loading.value = false

  window.addEventListener('message', communicationCb)
  const readyData = {
    eventName: 'sqlbot_assistant_event',
    busi: 'ready',
    ready: true,
    messageId: assistantId,
  }
  window.parent.postMessage(readyData, '*')

  request.get(`/system/assistant/${assistantId}`).then((res) => {
    if (res.name) {
      appName.value = res.name
    }
    if (res?.configuration) {
      const rawData = JSON.parse(res?.configuration)
      assistantStore.setAutoDs(rawData?.auto_ds)
      if (rawData.logo) {
        logo.value = baseUrl + rawData.logo
      }

      for (const key in customSet) {
        if (
          Object.prototype.hasOwnProperty.call(customSet, key) &&
          ![null, undefined].includes(rawData[key])
        ) {
          customSet[key] = rawData[key]
        }
      }

      if (!rawData.theme) {
        const { customColor, themeColor } = appearanceStore
        const currentColor =
          themeColor === 'custom' && customColor
            ? customColor
            : themeColor === 'blue'
              ? '#3370ff'
              : '#1CBA90'
        customSet.theme = currentColor || customSet.theme
      }

      nextTick(() => {
        setPageCustomColor(customSet.theme)
        setPageHeaderFontColor(customSet.header_font_color)
      })
    }
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('message', communicationCb)
})
</script>

<style lang="less" scoped>
.sqlbot-assistant-container {
  height: 100vh;
  width: 100%;
  color: rgb(31, 35, 41);
  .header {
    width: 100%;
    left: 0;
    top: 0;
    z-index: 100;
    height: 56px;
    line-height: 56px;
    background: var(--ed-color-primary-1a, #1cba901a);
    height: 56px;
    padding: 0 16px;
    display: flex;
    align-items: center;
    position: fixed;
    .logo {
      margin: 0 8px 0 16px;
    }

    .title {
      font-weight: 500;
      font-size: 16px;
      line-height: 24px;
      color: var(--ed-text-color-primary);
      max-width: calc(100% - 172px);
    }

    .ed-icon:not(.logo) {
      cursor: pointer;

      &::after {
        content: '';
        background-color: #1f23291a;
        position: absolute;
        border-radius: 6px;
        width: 28px;
        height: 28px;
        transform: translate(-50%, -50%);
        top: 50%;
        left: 50%;
        display: none;
      }

      &:hover {
        &::after {
          display: block;
        }
      }
    }

    .new-chat {
      position: absolute;
      right: 88px;
      top: 17px;
    }
  }
  .sqlbot-chat-container {
    padding-top: 56px;
    height: 100%;
    :deep(.ed-aside) {
      display: none;
    }
  }
  .drawer-assistant {
    height: 100%;
    position: absolute;
    left: 0;
    top: 0;
    width: 50%;
    background: #f5f6f7;
    box-shadow: 0px 6px 24px 0px #1f232914;
    padding: 16px;
    border-right: 1px solid #dee0e3;
    display: none;
  }
}
</style>
