<script setup lang="ts">
import type { ChatMessage } from '@/api/chat.ts'
import icon_copy_outlined from '@/assets/embedded/icon_copy_outlined.svg'
import { useI18n } from 'vue-i18n'
import { useClipboard } from '@vueuse/core'
import { computed } from 'vue'

const props = defineProps<{
  message?: ChatMessage
  allMessages?: ChatMessage[]
}>()
const { t } = useI18n()
const { copy } = useClipboard({ legacy: true })

function clickAnalysis() {
  console.info('analysis_record_id: ' + props.message?.record?.analysis_record_id)
}
function clickPredict() {
  console.info('predict_record_id: ' + props.message?.record?.predict_record_id)
}
function clickRegenerated() {
  console.info('regenerate_record_id: ' + props.message?.record?.regenerate_record_id)
}

const isRegenerated = computed(() => {
  return !!props.message?.record?.regenerate_record_id
})

const copyCode = () => {
  const str = props.message?.content || ''
  copy(str as string)
    .then(function () {
      ElMessage.success(t('embedded.copy_successful'))
    })
    .catch(function () {
      ElMessage.error(t('embedded.copy_failed'))
    })
}
</script>

<template>
  <div class="question">
    <span v-if="message?.record?.analysis_record_id" class="prefix-title" @click="clickAnalysis">
      {{ t('qa.data_analysis') }}
    </span>
    <span v-else-if="message?.record?.predict_record_id" class="prefix-title" @click="clickPredict">
      {{ t('qa.data_predict') }}
    </span>
    <span v-else-if="isRegenerated" class="prefix-title" @click="clickRegenerated">
      {{ t('qa.data_regenerated') }}
    </span>
    <span style="width: 100%">{{ message?.content }}</span>
    <div style="position: absolute; right: 12px; bottom: -24px">
      <el-tooltip :offset="12" effect="dark" :content="t('datasource.copy')" placement="top">
        <el-icon style="cursor: pointer" size="16" @click="copyCode">
          <icon_copy_outlined></icon_copy_outlined>
        </el-icon>
      </el-tooltip>
    </div>
  </div>
</template>

<style scoped lang="less">
.question {
  display: flex;
  flex-direction: row;
  gap: 8px;
  border-radius: var(--radius-lg);
  min-height: 44px;
  line-height: 1.47;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.02em;
  padding: 11px 20px;
  color: var(--chat-bubble-user-text);
  background: var(--chat-bubble-user-bg);
  border: 1px solid var(--color-hairline-soft);
  position: relative;

  word-wrap: break-word;
  white-space: pre-wrap;

  .prefix-title {
    color: var(--color-primary);
    white-space: nowrap;
    font-weight: 600;
  }
}
</style>
