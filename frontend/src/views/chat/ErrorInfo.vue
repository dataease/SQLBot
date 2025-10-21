<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAssistantStore } from '@/stores/assistant.ts'

const props = defineProps<{
  error?: string
}>()

const { t } = useI18n()

const assistantStore = useAssistantStore()
const isCompletePage = computed(() => !assistantStore.getAssistant || assistantStore.getEmbedded)

const showBlock = computed(() => {
  return props.error && props.error?.trim().length > 0
})

const errorMessage = computed(() => {
  const obj = { message: props.error, showMore: false, traceback: '', type: undefined }
  if (showBlock.value && props.error?.trim().startsWith('{') && props.error?.trim().endsWith('}')) {
    try {
      const json = JSON.parse(props.error?.trim())
      obj.message = json['message']
      obj.traceback = json['traceback']
      obj.type = json['type']
      if (obj.traceback?.trim().length > 0) {
        obj.showMore = true
      }
    } catch (e) {
      console.error(e)
    }
  }
  return obj
})

const show = ref(false)

function showTraceBack() {
  show.value = true
}
</script>

<template>
  <div v-if="showBlock">
    <div
      v-if="!errorMessage.showMore && errorMessage.type == undefined"
      v-dompurify-html="errorMessage.message"
      class="error-container"
    ></div>
    <div v-else class="error-container row">
      <template v-if="errorMessage.type === 'db-connection-err'">
        {{ t('chat.ds_is_invalid') }}
      </template>
      <template v-else-if="errorMessage.type === 'exec-sql-err'">
        {{ t('chat.exec-sql-err') }}
      </template>
      <template v-else>
        {{ t('chat.error') }}
      </template>
      <el-button v-if="errorMessage.showMore" text @click="showTraceBack">
        {{ t('chat.show_error_detail') }}
      </el-button>
    </div>

    <el-drawer
      v-model="show"
      :size="!isCompletePage ? '100%' : '600px'"
      :title="t('chat.error')"
      direction="rtl"
      body-class="chart-sql-error-body"
    >
      <el-main>
        <div v-dompurify-html="errorMessage.traceback" class="error-container open"></div>
      </el-main>
    </el-drawer>
  </div>
</template>

<style lang="less">
.chart-sql-error-body {
  padding: 0;
}
</style>
<style scoped lang="less">
.error-container {
  font-weight: 400;
  font-size: 16px;
  line-height: 24px;
  color: rgba(31, 35, 41, 1);
  white-space: pre-wrap;
  word-break: break-word;

  &.row {
    display: flex;
    flex-direction: row;
    align-items: center;
  }
  &.open {
    font-size: 14px;
    line-height: 20px;
  }
}
</style>
