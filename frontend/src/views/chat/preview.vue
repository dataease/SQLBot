<template>
  <div v-loading="divLoading" class="sqlbot-embedded-assistant-page">
    <error-page v-if="inIframe" :title="t('embedded.preview_error')" />
    <chat-component
      v-else
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
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import ErrorPage from '@/views/error/index.vue'
import { isInIframe } from '@/utils/utils'
const { t } = useI18n()
//const chatRef = ref()

const customSet = reactive({
  name: '',
  welcome: t('embedded.i_am_sqlbot'),
  welcome_desc: t('embedded.data_analysis_now'),
  theme: '#1CBA90',
  header_font_color: '#1F2329',
}) as { [key: string]: any }
const logo = ref()
const divLoading = ref(true)

const inIframe = computed(() => isInIframe())

onMounted(() => {
  nextTick(() => {
    setTimeout(() => {
      divLoading.value = false
    }, 1500)
  })
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
