<template>
  <div
    v-loading="divLoading"
    :class="dynamicType === 4 ? 'sqlbot--embedded-page' : 'sqlbot-embedded-assistant-page'"
  >
    <chat-component
      v-if="!loading"
      ref="chatRef"
      :welcome="customSet.welcome"
      :welcome-desc="customSet.welcome_desc"
      :logo-assistant="logo"
      :page-embedded="true"
      :app-name="customSet.name"
    />
  </div>
</template>
<script setup lang="ts">
import ChatComponent from '@/views/chat/index.vue'
import { nextTick, onBeforeMount, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { assistantApi } from '@/api/assistant'
import { useAssistantStore } from '@/stores/assistant'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import { useI18n } from 'vue-i18n'
import { request } from '@/utils/request'
import { setCurrentColor } from '@/utils/utils'
import { useUserStore } from '@/stores/user'
const userStore = useUserStore()
const { t } = useI18n()
const chatRef = ref()
const appearanceStore = useAppearanceStoreWithOut()
const assistantStore = useAssistantStore()
assistantStore.setPageEmbedded(true)
const route = useRoute()
const assistantName = ref('')
const dynamicType = ref(0)
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
const validator = ref({
  id: '',
  valid: false,
  id_match: false,
  token: '',
})
const loading = ref(true)
const divLoading = ref(true)
const eventName = 'sqlbot_embedded_event'
const communicationCb = async (event: any) => {
  if (event.data?.eventName === eventName) {
    if (event.data?.messageId !== route.query.id) {
      return
    }
    if (event.data?.busi == 'certificate') {
      const type = parseInt(event.data['type'])
      const certificate = event.data['certificate']
      assistantStore.setType(type)
      if (type === 4) {
        assistantStore.setToken(certificate)
        assistantStore.setAssistant(true)
        await userStore.info()
        loading.value = false
        return
      }
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

watch(
  () => loading.value,
  (val) => {
    nextTick(() => {
      setTimeout(() => {
        divLoading.value = val
      }, 1000)
    })
  }
)
const createChat = () => {
  chatRef.value?.createNewChat()
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

const registerReady = (assistantId: any) => {
  window.addEventListener('message', communicationCb)
  const readyData = {
    eventName: 'sqlbot_embedded_event',
    busi: 'ready',
    ready: true,
    messageId: assistantId,
  }
  window.parent.postMessage(readyData, '*')
}

const setPageCustomColor = (val: any) => {
  const ele = document.querySelector('body') as HTMLElement
  setCurrentColor(val, ele)
}

onBeforeMount(async () => {
  const assistantId = route.query.id
  if (!assistantId) {
    ElMessage.error('Miss embedded id, please check embedded url')
    return
  }
  const typeParam = route.query.type
  let assistantType = 2
  if (typeParam) {
    assistantType = parseInt(typeParam.toString())
    assistantStore.setType(assistantType)
  }
  dynamicType.value = assistantType
  const online = route.query.online
  setFormatOnline(online)

  const history: boolean = route.query.history !== 'false'
  assistantStore.setHistory(history)

  let name = route.query.name
  if (name) {
    assistantName.value = decodeURIComponent(name.toString())
  }
  let userFlag = route.query.userFlag
  if (userFlag && userFlag === '1') {
    userFlag = '100001'
  }
  const now = Date.now()
  assistantStore.setFlag(now)
  assistantStore.setId(assistantId?.toString() || '')
  if (assistantType === 4) {
    assistantStore.setAssistant(true)
    registerReady(assistantId)
    return
  }
  const param = {
    id: assistantId,
    virtual: userFlag || assistantStore.getFlag,
    online,
  }
  validator.value = await assistantApi.validate(param)
  assistantStore.setToken(validator.value.token)
  assistantStore.setAssistant(true)
  loading.value = false

  registerReady(assistantId)

  request.get(`/system/assistant/${assistantId}`).then((res) => {
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
      })
    }
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('message', communicationCb)
})
</script>

<style lang="less" scoped>
.sqlbot--embedded-page {
  width: 100%;
  height: 100vh;
  position: relative;
  background: #fff;
}
.sqlbot-embedded-assistant-page {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  background: #f7f8fa;
  box-sizing: border-box;
  overflow: auto;
  padding-bottom: 48px;
}
</style>
