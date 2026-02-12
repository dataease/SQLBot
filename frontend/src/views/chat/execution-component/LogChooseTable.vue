<script setup lang="ts">
import BaseContent from './BaseContent.vue'
import { type ChatLogHistoryItem } from '@/api/chat.ts'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    item?: ChatLogHistoryItem
    error?: string
  }>(),
  {
    item: undefined,
    error: '',
  }
)

const schema = computed(() => {
  return (props.item?.message as string) ?? ''
})
</script>

<template>
  <BaseContent class="base-container">
    <template v-if="item.error">
      {{ error }}
    </template>
    <template v-else>
      <div v-dompurify-html="schema" class="inner-title"></div>
    </template>
  </BaseContent>
</template>

<style scoped lang="less">
.inner-title {
  color: #646a73;
  font-size: 12px;
  line-height: 20px;
  font-weight: 500;
  vertical-align: middle;
  white-space: pre-wrap;
}
.item-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: stretch;
  flex-wrap: nowrap;
  .inner-item {
    border: 1px solid #dee0e3;
    display: flex;
    flex-direction: column;
    gap: 8px;
    border-radius: 12px;
    padding: 16px;
    background: #ffffff;

    .inner-item-title {
      color: #1f2329;
      font-weight: 500;
      line-height: 22px;
      font-size: 14px;
      vertical-align: middle;
    }
    .inner-item-description {
      color: #646a73;
      font-weight: 400;
      line-height: 22px;
      font-size: 14px;
      vertical-align: middle;
    }
  }
}
</style>
