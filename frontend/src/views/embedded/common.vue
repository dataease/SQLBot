<template>
  <div v-loading="divLoading" class="sqlbot--embedded-page">
    <ds-component
      v-if="!loading && isWsAdmin && busiFlag === 'ds'"
      ref="dsRef"
      :page-embedded="true"
    />
    <page-401
      v-if="!loading && !isWsAdmin && busiFlag === 'ds'"
      :title="t('login.permission_invalid')"
    />
  </div>
</template>
<script setup lang="ts">
import DsComponent from '@/views/ds/Datasource.vue'
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
      await userStore.info()
      loading.value = false
      return
    }
    if (event.data?.hostOrigin) {
      assistantStore.setHostOrigin(event.data?.hostOrigin)
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
  const assistantId = route.query.id
  if (!assistantId) {
    ElMessage.error('Miss embedded id, please check embedded url')
    return
  }
  assistantStore.setType(4)
  const now = Date.now()
  assistantStore.setFlag(now)
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
</style>
