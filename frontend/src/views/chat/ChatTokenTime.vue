<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { chatApi, type ChatLogHistory } from '@/api/chat.ts'

const props = defineProps<{
  recordId?: number
  duration?: number | undefined
  totalTokens?: number | undefined
}>()

const logHistory = ref<ChatLogHistory>()

function getLogList() {
  chatApi.get_chart_log_history(props.recordId).then((res) => {
    logHistory.value = chatApi.toChatLogHistory(res)
    console.log(logHistory.value)
  })
}

onMounted(() => {})
</script>

<template>
  <div v-if="recordId && (duration || totalTokens)" class="tool-container">
    <span>token: {{ totalTokens }}</span>
    <span>duration: {{ duration }}</span>
    <el-button @click="getLogList">log</el-button>
  </div>
</template>

<style scoped lang="less">
.tool-container {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;

  row-gap: 8px;

  min-height: 22px;

  margin-top: 12px;
  margin-bottom: 12px;

  .tool-times {
    flex: 1;
    font-size: 14px;
    font-weight: 400;
    line-height: 22px;
    color: rgba(100, 106, 115, 1);

    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;

    .time {
      white-space: nowrap;
    }
  }
}
</style>
