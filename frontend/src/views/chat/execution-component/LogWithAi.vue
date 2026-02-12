<script setup lang="ts">
import BaseContent from './BaseContent.vue'
import { type ChatLogHistoryItem } from '@/api/chat.ts'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import SQLComponent from '@/views/chat/component/SQLComponent.vue'
import { find, findLastIndex } from 'lodash-es'

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

const { t } = useI18n()

const data = computed(() => {
  return (props.item?.message as Array<any>) ?? []
})

// 1. 获取 role 为 system 的一条记录
const systemRecord = computed(() => find(data.value, { type: 'system' }))

// 2. 获取最后一个 role 为 human 的记录
const lastHumanIndex = computed(() => findLastIndex(data.value, { type: 'human' }))
const lastHumanRecord = computed(() => data.value[lastHumanIndex.value])

// 3. 获取最后一个 role 为 ai 且在当前对话提问后出现的记录
// 使用原生 filter 和 pop
const aiRecordsAfterHuman = computed(() =>
  data.value.slice(lastHumanIndex.value + 1).filter((item) => item.type === 'ai')
)
const lastAiAfterHuman = computed(() =>
  aiRecordsAfterHuman.value.length > 0
    ? aiRecordsAfterHuman.value[aiRecordsAfterHuman.value.length - 1]
    : undefined
)
// 4. 获取除 system 以外，当前对话提问前的所有记录
const recordsBeforeCurrentQuestion = computed(() =>
  data.value.slice(0, lastHumanIndex.value).filter((item) => item.type !== 'system')
)
</script>

<template>
  <BaseContent class="base-container">
    <template v-if="item.error">
      {{ error }}
    </template>
    <template v-else>
      <div class="item-list">
        <div class="inner-title">{{ t('chat.log_system') }}</div>
        <div class="inner-item">
          <div class="inner-item-title">
            {{ systemRecord.type }}
          </div>
          <div class="inner-item-description">
            <SQLComponent :sql="systemRecord.content" />
          </div>
        </div>
        <template v-if="recordsBeforeCurrentQuestion.length > 0">
          <div class="inner-title">{{ t('chat.log_history') }}</div>
          <div class="inner-item">
            <div v-for="(ele, index) in recordsBeforeCurrentQuestion" :key="index">
              <div class="inner-item-title">
                {{ ele.type }}
              </div>
              <div class="inner-item-description">
                <SQLComponent :sql="ele.content" />
              </div>
            </div>
          </div>
        </template>
        <div class="inner-title">{{ t('chat.log_question') }}</div>
        <div class="inner-item">
          <div class="inner-item-description">
            <SQLComponent :sql="lastHumanRecord.content" />
          </div>
        </div>
        <template v-if="lastAiAfterHuman">
          <div class="inner-title">{{ t('chat.log_answer') }}</div>
          <div class="inner-item">
            <div class="inner-item-description">
              <SQLComponent :sql="lastAiAfterHuman.content" />
            </div>
          </div>
        </template>
      </div>
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

      .hljs {
        padding: 0 1rem;
      }
    }
  }
}
</style>
