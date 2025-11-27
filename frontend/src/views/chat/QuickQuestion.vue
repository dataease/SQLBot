<script lang="ts" setup>
import { ref } from 'vue'
import icon_quick_question from '@/assets/svg/icon_quick_question.svg'
import { Close } from '@element-plus/icons-vue'
import RecommendQuestion from '@/views/chat/RecommendQuestion.vue'
import { ChatInfo } from '@/api/chat.ts'
import RecentQuestion from '@/views/chat/RecentQuestion.vue'
const visible = ref(false)
const activeName = ref('recommend')
const recommendQuestionRef = ref()

const getRecommendQuestions = () => {
  recommendQuestionRef.value.getRecommendQuestions()
}
const quickAsk = (question: string) => {
  emits('quickAsk', question)
  visible.value = false
}

const onChatStop = () => {
  emits('stop')
}

const loadingOver = () => {
  emits('loadingOver')
}

const emits = defineEmits(['quickAsk', 'loadingOver', 'stop'])
defineExpose({ getRecommendQuestions, id: () => props.recordId, stop })

const props = withDefaults(
  defineProps<{
    recordId?: number
    datasourceId?: number
    currentChat?: ChatInfo
    questions?: string
    firstChat?: boolean
    disabled?: boolean
  }>(),
  {
    recordId: undefined,
    datasourceId: undefined,
    currentChat: () => new ChatInfo(),
    questions: '[]',
    firstChat: false,
    disabled: false,
  }
)
</script>

<template>
  <el-popover
    :title="$t('qa.quick_question')"
    :visible="visible"
    popper-class="quick_question_popover"
    placement="top-start"
    :width="320"
  >
    <el-icon class="close_icon"><Close @click="visible = false" /></el-icon>
    <el-tabs v-model="activeName" class="quick_question_tab">
      <el-tab-pane :label="$t('qa.recommend')" name="recommend">
        <RecommendQuestion
          ref="recommendQuestionRef"
          :current-chat="currentChat"
          :record-id="recordId"
          :questions="questions"
          :disabled="disabled"
          :first-chat="firstChat"
          position="input"
          @click-question="quickAsk"
          @stop="onChatStop"
          @loading-over="loadingOver"
        />
      </el-tab-pane>
      <el-tab-pane v-if="datasourceId" :label="$t('qa.recently')" name="recently">
        <RecentQuestion v-if="visible" :datasource-id="datasourceId" @click-question="quickAsk">
        </RecentQuestion>
      </el-tab-pane>
    </el-tabs>
    <template #reference>
      <el-button plain size="small" @click="visible = true">
        <el-icon size="16" class="el-icon--left">
          <icon_quick_question />
        </el-icon>
        {{ $t('qa.quick_question') }}
      </el-button>
    </template>
  </el-popover>
</template>

<style lang="less">
.quick_question_popover {
  .quick_question_tab {
    height: 230px;
  }
  .ed-tabs__content {
    overflow: auto;
  }
  .ed-popover__title {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 0;
  }
  .close_icon {
    position: absolute;
    cursor: pointer;
    top: 12px;
    right: 12px;
  }
  .ed-tabs__item {
    font-size: 14px;
    height: 38px;
  }
  .ed-tabs__active-bar {
    height: 2px;
  }
  .ed-tabs__nav-wrap:after {
    height: 0;
  }
  .ed-tabs__content {
    padding-top: 12px;
  }
}
</style>
