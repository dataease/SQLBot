<script setup lang="ts">
import { ref } from 'vue'
import icon_logs_outlined from '@/assets/svg/icon_logs_outlined.svg'
import ExecutionDetails from './ExecutionDetails.vue'
const props = defineProps<{
  recordId?: number
  duration?: number | undefined
  totalTokens?: number | undefined
}>()

const executionDetailsRef = ref()
function getLogList() {
  executionDetailsRef.value.getLogList(props.recordId)
}
</script>

<template>
  <div v-if="recordId && (duration || totalTokens)" class="tool-container">
    <span>{{ $t('parameter.tokens_required') }} {{ totalTokens }}</span>
    <span style="margin-left: 12px">{{ $t('parameter.time_execution') }} {{ duration }} s</span>

    <div @click="getLogList" class="detail">
      <el-icon style="margin-right: 4px" size="16">
        <icon_logs_outlined></icon_logs_outlined>
      </el-icon>
      {{ $t('parameter.execution_details') }}
    </div>
  </div>
  <ExecutionDetails ref="executionDetailsRef"></ExecutionDetails>
</template>

<style scoped lang="less">
.tool-container {
  display: flex;
  align-items: center;
  height: 38px;
  margin: 12px 0;
  background: #f5f6f7;
  border-radius: 6px;
  padding: 0 12px;
  font-family: PingFang SC;
  font-weight: 400;
  font-size: 14px;
  line-height: 22px;
  color: #646a73;

  .detail {
    cursor: pointer;
    margin-left: auto;
    display: flex;
    align-items: center;
    position: relative;
    &:hover {
      &::after {
        content: '';
        background: #1f23291a;
        border-radius: 6px;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 84px;
        height: 26px;
        position: absolute;
      }
    }
  }
}
</style>
