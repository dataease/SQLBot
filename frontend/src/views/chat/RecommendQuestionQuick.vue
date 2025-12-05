<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { endsWith, startsWith } from 'lodash-es'
import { chatApi } from '@/api/chat.ts'
import { recommendedApi } from '@/api/recommendedApi.ts'

const props = withDefaults(
  defineProps<{
    recordId?: number
    disabled?: boolean
    datasource?: number
  }>(),
  {
    recordId: undefined,
    disabled: false,
    datasource: undefined,
  }
)

const emits = defineEmits(['clickQuestion', 'stop', 'loadingOver'])

const loading = ref(false)

const questions = ref('[]')

const computedQuestions = computed<string>(() => {
  if (
    questions.value &&
    questions.value.length > 0 &&
    startsWith(questions.value.trim(), '[') &&
    endsWith(questions.value.trim(), ']')
  ) {
    return JSON.parse(questions.value)
  }
  return []
})

function clickQuestion(question: string): void {
  if (!props.disabled) {
    emits('clickQuestion', question)
  }
}

const stopFlag = ref(false)

async function getRecommendQuestions(articles_number: number) {
  recommendedApi.get_datasource_recommended_base(props.datasource).then((res) => {
    if (res.recommended_config === 2) {
      questions.value = res.questions
    } else {
      getRecommendQuestionsLLM(articles_number)
    }
  })
}

async function getRecommendQuestionsLLM(articles_number: number) {
  stopFlag.value = false
  loading.value = true
  try {
    const controller: AbortController = new AbortController()
    const params = articles_number ? '?articles_number=' + articles_number : ''
    const response = await chatApi.recommendQuestions(props.recordId, controller, params)
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')

    let tempResult = ''

    while (true) {
      if (stopFlag.value) {
        controller.abort()
        loading.value = false
        break
      }

      const { done, value } = await reader.read()
      if (done) {
        break
      }

      let chunk = decoder.decode(value, { stream: true })
      tempResult += chunk
      const split = tempResult.match(/data:.*}\n\n/g)
      if (split) {
        chunk = split.join('')
        tempResult = tempResult.replace(chunk, '')
      } else {
        continue
      }

      if (chunk && chunk.startsWith('data:{')) {
        if (split) {
          for (const str of split) {
            let data
            try {
              data = JSON.parse(str.replace('data:{', '{'))
            } catch (err) {
              console.error('JSON string:', str)
              throw err
            }

            if (data.code && data.code !== 200) {
              ElMessage({
                message: data.msg,
                type: 'error',
                showClose: true,
              })
              return
            }

            switch (data.type) {
              case 'recommended_question':
                if (
                  data.content &&
                  data.content.length > 0 &&
                  startsWith(data.content.trim(), '[') &&
                  endsWith(data.content.trim(), ']')
                ) {
                  questions.value = data.content
                  await nextTick()
                }
            }
          }
        }
      }
    }
  } finally {
    loading.value = false
    emits('loadingOver')
  }
}

function stop() {
  stopFlag.value = true
  loading.value = false
  emits('stop')
}

onBeforeUnmount(() => {
  stop()
})

defineExpose({ getRecommendQuestions, id: () => props.recordId, stop })
</script>

<template>
  <div style="width: 100%; height: 100%">
    <div v-if="computedQuestions.length > 0 || loading" class="recommend-questions">
      <div v-if="loading">
        <el-button style="min-width: unset" type="primary" link loading />
      </div>
      <div v-else class="question-grid-input">
        <div
          v-for="(question, index) in computedQuestions"
          :key="index"
          class="question"
          :class="{ disabled: disabled }"
          :title="question"
          @click="clickQuestion(question)"
        >
          {{ question }}
        </div>
      </div>
    </div>
    <div v-else class="recommend-questions-error">
      {{ $t('qa.retrieve_error') }}
    </div>
  </div>
</template>

<style scoped lang="less">
.recommend-questions {
  width: 100%;
  font-size: 14px;
  font-weight: 500;
  line-height: 22px;
  display: flex;
  flex-direction: column;
  gap: 4px;

  .continue-ask {
    color: rgba(100, 106, 115, 1);
    font-weight: 400;
  }

  .question-grid-input {
    display: grid;
    grid-gap: 1px;
    grid-template-columns: repeat(1, calc(100% - 6px));
  }

  .question-grid {
    display: grid;
    grid-gap: 12px;
    grid-template-columns: repeat(2, calc(50% - 6px));
  }

  .question {
    font-weight: 400;
    cursor: pointer;
    height: 32px;
    border-radius: 4px;
    padding: 5px 8px;
    line-height: 22px;
    white-space: nowrap; /* 禁止换行 */
    overflow: hidden; /* 隐藏溢出内容 */
    text-overflow: ellipsis; /* 显示省略号 */
    &:hover {
      background: rgba(31, 35, 41, 0.1);
    }
    &.disabled {
      cursor: not-allowed;
      background: rgba(245, 246, 247, 1);
    }
  }
}

.recommend-questions-error {
  font-size: 14px;
  font-weight: 400;
  color: rgba(100, 106, 115, 1);
  margin-top: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}
</style>
