<script setup lang="ts">
import { type ChatMessage } from '@/api/chat.ts'
import { computed, onMounted, ref } from 'vue'
import MdComponent from '@/views/chat/component/MdComponent.vue'
import icon_up_outlined from '@/assets/svg/icon_up_outlined.svg'
import icon_down_outlined from '@/assets/svg/icon_down_outlined.svg'
import { useI18n } from 'vue-i18n'
import { useChatConfigStore } from '@/stores/chatConfig.ts'

const props = withDefaults(
  defineProps<{
    message: ChatMessage
    loading?: boolean
    reasoningName:
      | 'sql_answer'
      | 'chart_answer'
      | 'analysis_thinking'
      | 'predict'
      | Array<'sql_answer' | 'chart_answer' | 'analysis_thinking' | 'predict'>
  }>(),
  {
    loading: false,
  }
)

const { t } = useI18n()

const chatConfig = useChatConfigStore()

const show = ref<boolean>(false)

const reasoningContent = computed<Array<string>>(() => {
  const names: Array<'sql_answer' | 'chart_answer' | 'analysis_thinking' | 'predict'> = []
  if (typeof props.reasoningName === 'string') {
    names.push(props.reasoningName)
  } else {
    props.reasoningName.forEach((item) => {
      names.push(item)
    })
  }
  const result: Array<string> = []
  names.forEach((item) => {
    if (props.message?.record) {
      if (props.message?.record[item]) {
        result.push(props.message?.record[item] ?? '')
      }
    }
  })
  return result
})

const hasReasoning = computed<boolean>(() => {
  if (reasoningContent.value.length > 0) {
    for (let i = 0; i < reasoningContent.value.length; i++) {
      if (reasoningContent.value[i] && reasoningContent.value[i].trim() !== '') {
        return true
      }
    }
  }
  return false
})

function clickShow() {
  show.value = !show.value
}

onMounted(() => {
  if (props.message.isTyping) {
    // 根据配置项是否默认展开
    show.value = chatConfig.getExpandThinkingBlock
  }
})
</script>

<template>
  <div class="base-answer-block">
    <el-button v-if="message.isTyping || hasReasoning" class="thinking-btn" @click="clickShow">
      <div class="thinking-btn-inner">
        <span v-if="message.isTyping">{{ t('qa.thinking') }}</span>
        <span v-else>{{ t('qa.thinking_step') }}</span>
        <span class="btn-icon">
          <el-icon v-if="show">
            <icon_up_outlined />
          </el-icon>
          <el-icon v-else>
            <icon_down_outlined />
          </el-icon>
        </span>
      </div>
    </el-button>
    <div v-if="hasReasoning && show" class="reasoning-content">
      <div v-for="(reason, _index) in reasoningContent" :key="_index" class="reasoning">
        <MdComponent :message="reason" />
      </div>
    </div>
    <div class="answer-container">
      <slot></slot>
      <el-button v-if="message.isTyping" style="min-width: unset" type="primary" link loading />
      <slot name="tool"></slot>
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<style scoped lang="less">
.base-answer-block {
  .thinking-btn {
    height: 32px;
    padding: 5px 12px;
    border-radius: 9999px;
    background: var(--chat-bubble-assistant-bg);
    border: 1px solid var(--color-hairline);

    --ed-button-text-color: var(--color-muted);
    --ed-button-hover-text-color: var(--color-ink);
    --ed-button-active-text-color: var(--color-ink);
    --ed-button-bg-color: var(--chat-bubble-assistant-bg);
    --ed-button-hover-bg-color: var(--overlay-hover);
    --ed-button-active-bg-color: var(--overlay-pressed);
    --ed-button-border-color: var(--color-hairline);
    --ed-button-hover-border-color: var(--color-hairline);
    --ed-button-active-border-color: var(--color-hairline);

    --ed-button-font-weight: 400;

    .thinking-btn-inner {
      display: flex;
      flex-direction: row;
      align-items: center;

      line-height: 1.29;
      font-weight: 400;
      font-size: 14px;
      letter-spacing: -0.224px;
    }
    .btn-icon {
      margin-left: 4px;
    }
  }

  .reasoning-content {
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    padding-left: 9px;
    border-left: 1px solid var(--color-hairline);
    gap: 8px;

    .reasoning {
      width: 100%;
      line-height: 1.43;
      font-weight: 400;
      font-size: 14px;
      color: var(--color-muted) !important;

      .markdown-body {
        color: var(--color-muted) !important;
        line-height: 1.43;
        font-weight: 400;
        font-size: 14px;
        letter-spacing: -0.224px;
      }

      padding-bottom: 8px;
      border-bottom: 1px solid var(--color-hairline-soft);

      &:last-child {
        padding-bottom: unset;
        border-bottom: unset;
      }
    }
  }

  .answer-container {
    width: 100%;

    line-height: 1.47;
    font-size: 17px;
    font-weight: 400;
    letter-spacing: -0.374px;
    color: var(--color-body);
  }
}
</style>
