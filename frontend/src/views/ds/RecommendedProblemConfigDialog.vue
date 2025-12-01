<script setup lang="ts">
import { reactive, ref } from 'vue'
import { recommendedApi } from '@/api/recommendedApi.ts'
import { Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus-secondary'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

interface RecommendedProblem {
  id?: number
  question: string
  datasource_id?: any | undefined
  sort: number
}

const emits = defineEmits(['recommendedProblemChange'])

const dialogShow = ref(false)

const state = reactive({
  datasource_id: null,
  recommended: {
    recommended_config: 1,
    recommendedProblemList: [] as RecommendedProblem[],
  },
})

const init = (params: any) => {
  dialogShow.value = true
  state.recommended.recommended_config = params.recommended_config || 1
  state.datasource_id = params.id
  recommendedApi.get_recommended_problem(state.datasource_id).then((res: any) => {
    state.recommended.recommendedProblemList = res
  })
}

const addRecommendedProblem = (): void => {
  state.recommended.recommendedProblemList.push({
    question: '',
    datasource_id: state.datasource_id,
  } as RecommendedProblem)
}

const closeDialog = () => {
  dialogShow.value = false
  state.recommended = {
    recommended_config: 1,
    recommendedProblemList: [] as RecommendedProblem[],
  }
}
const save = () => {
  if (state.recommended.recommended_config == 2) {
    let checkProblem = false
    let repetitiveQuestion = false
    if (state.recommended.recommendedProblemList.length === 0) {
      checkProblem = true
    }
    const questions = new Set<string>()
    state.recommended.recommendedProblemList.forEach((problem: RecommendedProblem): void => {
      if (problem.question.length > 200 || problem.question.length < 2) {
        checkProblem = true
      }
      if (questions.has(problem.question)) {
        repetitiveQuestion = true
      }
      questions.add(problem.question)
    })
    if (checkProblem) {
      ElMessage.error(t('datasource.recommended_problem_tips'))
      return
    }

    if (repetitiveQuestion) {
      ElMessage.error(t('datasource.recommended_repetitive_tips'))
      return
    }
  }
  recommendedApi
    .save_recommended_problem({
      recommended_config: state.recommended.recommended_config,
      datasource_id: state.datasource_id,
      problemInfo: state.recommended.recommendedProblemList,
    })
    .then(() => {
      emits('recommendedProblemChange')
      closeDialog()
    })
}
const deleteRecommendedProblem = (index: number): void => {
  state.recommended.recommendedProblemList.splice(index, 1)
}

defineExpose({
  init,
})
</script>

<template>
  <el-dialog
    v-model="dialogShow"
    :title="$t('datasource.recommended_problem_configuration')"
    width="600"
    modal-class="add-question_dialog"
    destroy-on-close
    :close-on-click-modal="false"
    @before-closed="closeDialog"
  >
    <el-form-item :label="$t('datasource.problem_generation_method')" prop="mode">
      <el-radio-group v-model="state.recommended.recommended_config">
        <el-radio :value="1">{{ $t('datasource.ai_automatic_generation') }}</el-radio>
        <el-radio :value="2">{{ $t('datasource.user_defined') }}</el-radio>
      </el-radio-group>
    </el-form-item>
    <template v-if="state.recommended.recommended_config === 2">
      <el-form-item
        v-for="(recommendedItem, index) in state.recommended.recommendedProblemList"
        :key="index"
        prop="mode"
      >
        <el-row class="question-item">
          <el-input
            v-model="recommendedItem.question"
            max="200"
            min="2"
            class="input-item"
            clearable
            :placeholder="$t('datasource.question_tips')"
          >
          </el-input>
          <el-icon class="delete-item"><Delete @click="deleteRecommendedProblem(index)" /></el-icon>
        </el-row>
      </el-form-item>
      <div v-if="state.recommended.recommendedProblemList.length < 10">
        <el-button text @click="addRecommendedProblem">
          {{ $t('datasource.add_question') }}</el-button
        >
      </div>
    </template>

    <div style="display: flex; justify-content: flex-end; margin-top: 20px">
      <el-button secondary @click="closeDialog">{{ $t('common.cancel') }}</el-button>
      <el-button type="primary" @click="save">{{ $t('common.save') }}</el-button>
    </div>
  </el-dialog>
</template>

<style scoped lang="less">
.add-question_dialog {
  .ed-input-group__append {
    background-color: #fff;
    padding: 0 12px;
  }
  .question-item {
    width: 100%;
    display: flex;
    align-items: center;
    .input-item {
      width: calc(100% - 40px);
    }
    .delete-item {
      margin-left: 8px;
      cursor: pointer;
      &:hover {
        color: red;
      }
    }
  }

  .value-input {
    .ed-input-group__append {
      color: #1f2329;
      position: relative;
      &:hover {
        &::after {
          content: '';
          position: absolute;
          left: -1px;
          top: 0;
          width: calc(100% - 1px);
          height: calc(100% - 2px);
          background: var(--ed-color-primary-1a, #1cba901a);
          border: 1px solid var(--ed-color-primary);
          border-bottom-right-radius: 6px;
          border-top-right-radius: 6px;
          pointer-events: none;
        }
      }
    }
  }
}
</style>
