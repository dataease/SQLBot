<script setup lang="ts">
import { reactive, ref } from 'vue'
import { recommendedApi } from '@/api/recommendedApi.ts'

interface RecommendedProblem {
  id?: number
  question: string
  datasourceId?: any | undefined
  sort: number
}

const dialogShow = ref(false)

const state = reactive({
  dsId: null,
  recommended: {
    recommendedConfig: 1,
    recommendedProblemList: [] as RecommendedProblem[],
  },
})

const init = (params: any) => {
  dialogShow.value = true
  state.recommended.recommendedConfig = params.recommendedConfig
  state.dsId = params.id
  recommendedApi.get_recommended_problem(state.dsId).then((res: any) => {
    state.recommended.recommendedProblemList = res
  })
}

const addRecommendedProblem = (): void => {
  state.recommended.recommendedProblemList.push({
    question: '',
    datasourceId: state.dsId,
  } as RecommendedProblem)
}

const closeDialog = () => {
  dialogShow.value = false
  state.recommended = {
    recommendedConfig: 1,
    recommendedProblemList: [] as RecommendedProblem[],
  }
}
const save = () => {
  recommendedApi.save_recommended_problem(state.recommended.recommendedProblemList)
  closeDialog()
}

const form = ref<any>({
  id: null,
  question: '',
  sort: null,
})

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
      <el-radio-group v-model="form.mode">
        <el-radio value="1">{{ $t('datasource.ai_automatic_generation') }}</el-radio>
        <el-radio value="2">{{ $t('datasource.user_defined') }}</el-radio>
      </el-radio-group>
    </el-form-item>
    <el-form-item
      v-for="(recommendedItem, index) in state.recommended.recommendedProblemList"
      :key="index"
      prop="mode"
    >
      <el-input
        v-model="recommendedItem.question"
        clearable
        :placeholder="$t('datasource.question_tips')"
      >
      </el-input>
    </el-form-item>
    <div>
      <el-button text @click="addRecommendedProblem">
        {{ $t('datasource.add_question') }}</el-button
      >
    </div>
    <div style="display: flex; justify-content: flex-end; margin-top: 20px">
      <el-button secondary @click="closeDialog">{{ $t('common.cancel') }}</el-button>
      <el-button type="primary" @click="save">{{ $t('model.add') }}</el-button>
    </div>
  </el-dialog>
</template>

<style scoped lang="less">
.add-question_dialog {
  .ed-input-group__append {
    background-color: #fff;
    padding: 0 12px;
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
