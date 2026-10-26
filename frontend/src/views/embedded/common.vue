<template>
  <div v-loading="divLoading" class="sqlbot--embedded-page">
    <div
      v-if="!loading && isWsAdmin && busiFlag === 'ds'"
      v-show="!startChatDsId"
      class="embedded-datasource"
    >
      <ds-component ref="dsRef" :page-embedded="true" @start-chat="startChatDsId = $event" />
    </div>
    <div v-if="!loading && isWsAdmin && busiFlag === 'ds' && startChatDsId" class="embedded-chat">
      <div class="embedded-chat-header">
        <el-button text @click="startChatDsId = undefined">{{ t('common.back') }}</el-button>
      </div>
      <chat-component :start-chat-ds-id="startChatDsId" :page-embedded="true" />
    </div>
    <page-401
      v-if="!loading && !isWsAdmin && busiFlag === 'ds'"
      :title="t('login.permission_invalid')"
    />
  </div>
</template>
<script setup lang="ts">
import DsComponent from '@/views/ds/Datasource.vue'
import ChatComponent from '@/views/chat/index.vue'
import Page401 from '@/views/error/index.vue'
import { computed, nextTick, onBeforeMount, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAssistantStore } from '@/stores/assistant'
import { useUserStore } from '@/stores/user'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
const userStore = useUserStore()
const assistantStore = useAssistantStore()
assistantStore.setPageEmbedded(true)
const route = useRoute()

const loading = ref(true)
const divLoading = ref(true)
const eventName = 'sqlbot_embedded_event'
const busiFlag = ref('ds')
const startChatDsId = ref<string>()

const setParamLanguage = () => {
  const lang = route.query.lang
  if (lang) {
    userStore.setLanguage(lang as string)
  }
}

const isWsAdmin = computed(() => {
  return userStore.isAdmin || userStore.isSpaceAdmin
})
const communicationCb = async (event: any) => {
  if (event.data?.eventName === eventName) {
    if (event.data?.messageId !== route.query.id) {
      return
    }
    if (!event.data?.busiFlag) {
      busiFlag.value = ''
      return
    }
    busiFlag.value = event.data.busiFlag
    if (event.data?.busi == 'certificate') {
      const type = parseInt(event.data['type'])
      const certificate = event.data['certificate']
      assistantStore.setType(type)
      assistantStore.setToken(certificate)
      assistantStore.setAssistant(true)
      try {
        await userStore.info()
      } catch (e) {
        console.error('Failed to fetch user info in common embedded:', e)
      }
      setParamLanguage()
      loading.value = false
      return
    }
    if (event.data?.hostOrigin) {
      assistantStore.setHostOrigin(event.data?.hostOrigin)
    }
    if (event.data?.busi == 'setLang') {
      userStore.setLanguage(event.data.lang)
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

onBeforeMount(async () => {
  setParamLanguage()
  const assistantId = route.query.id
  if (!assistantId) {
    ElMessage.error('Miss embedded id, please check embedded url')
    return
  }
  assistantStore.setType(4)
  assistantStore.setId(assistantId?.toString() || '')
  assistantStore.setAssistant(true)
  registerReady(assistantId)
  return
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
.embedded-datasource,
.embedded-chat {
  height: 100%;
}
.embedded-chat {
  display: flex;
  flex-direction: column;

  .embedded-chat-header {
    padding: 8px 16px;
    border-bottom: 1px solid var(--ed-border-color);
  }

  :deep(.chat-container) {
    flex: 1;
    min-height: 0;
  }
}
</style>
