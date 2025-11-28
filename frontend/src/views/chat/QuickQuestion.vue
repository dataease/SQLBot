<script lang="ts" setup>
import { ref } from 'vue'
import icon_quick_question from '@/assets/svg/icon_quick_question.svg'
import icon_close from '@/assets/svg/operate/ope-close.svg'
import icon_replace_outlined from '@/assets/svg/icon_replace_outlined.svg'
import RecommendQuestion from '@/views/chat/RecommendQuestion.vue'
import { ChatInfo } from '@/api/chat.ts'
import RecentQuestion from '@/views/chat/RecentQuestion.vue'
const activeName = ref('recommend')
const recommendQuestionRef = ref()
const recentQuestionRef = ref()
const popoverRef = ref()
const getRecommendQuestions = () => {
  recommendQuestionRef.value.getRecommendQuestions()
}

const retrieveQuestions = () => {
  getRecommendQuestions()
  recentQuestionRef.value.getRecentQuestions()
}
const quickAsk = (question: string) => {
  emits('quickAsk', question)
  hiddenProps()
}

const hiddenProps = () => {
  popoverRef.value.hide()
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
    ref="popoverRef"
    :title="$t('qa.quick_question')"
    popper-class="quick_question_popover"
    placement="top-start"
    trigger="click"
    :width="320"
  >
    <el-button class="tool-btn close_icon" text @click="hiddenProps">
      <el-icon size="18">
        <icon_close />
      </el-icon>
    </el-button>
    <el-tooltip effect="dark" :offset="8" :content="$t('qa.retrieve_again')" placement="top">
      <el-button class="tool-btn refresh_icon" text :disabled="disabled" @click="retrieveQuestions">
        <el-icon size="18">
          <icon_replace_outlined />
        </el-icon>
      </el-button>
    </el-tooltip>
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
        <RecentQuestion
          ref="recentQuestionRef"
          :disabled="disabled"
          :datasource-id="datasourceId"
          @click-question="quickAsk"
        >
        </RecentQuestion>
      </el-tab-pane>
    </el-tabs>
    <template #reference>
      <el-button plain size="small">
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
  .ed-tab-pane {
    display: flex;
    align-items: normal;
    width: 100%;
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
    top: 4px;
    right: 4px;
  }

  .refresh_icon {
    position: absolute;
    cursor: pointer;
    top: 30px;
    right: 4px;
    z-index: 1;
  }

  .tool-btn {
    font-size: 14px;
    font-weight: 400;
    line-height: 22px;
    color: rgba(100, 106, 115, 1);

    .tool-btn-inner {
      display: flex;
      flex-direction: row;
      align-items: center;
    }

    &:hover {
      background: rgba(31, 35, 41, 0.1);
    }
    &:active {
      background: rgba(31, 35, 41, 0.1);
    }
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
