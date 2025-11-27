<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { chatApi } from '@/api/chat.ts'

const props = withDefaults(
  defineProps<{
    datasourceId?: number
  }>(),
  {
    datasourceId: undefined,
  }
)

const emits = defineEmits(['clickQuestion'])

const loading = ref(false)

const computedQuestions = ref([])

function clickQuestion(question: string): void {
  emits('clickQuestion', question)
}

onMounted(() => {
  getRecentQuestions()
})
async function getRecentQuestions() {
  chatApi.recentQuestions(props.datasourceId).then((res) => {
    computedQuestions.value = res
  })
}
</script>

<template>
  <div v-if="computedQuestions.length > 0 || loading" class="recent-questions">
    <div class="question-grid-input">
      <div
        v-for="(question, index) in computedQuestions"
        :key="index"
        class="question"
        @click="clickQuestion(question)"
      >
        {{ question }}
      </div>
    </div>
  </div>
</template>

<style scoped lang="less">
.recent-questions {
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
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
    grid-gap: 12px;
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
    background: rgba(245, 246, 247, 1);
    min-height: 32px;
    border-radius: 6px;
    padding: 5px 12px;
    line-height: 22px;
    &:hover {
      background: rgba(31, 35, 41, 0.1);
    }
    &.disabled {
      cursor: not-allowed;
      background: rgba(245, 246, 247, 1);
    }
  }
}
</style>
