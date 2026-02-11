<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import icon_quick_question from '@/assets/svg/icon_quick_question.svg'
import icon_replace_outlined from '@/assets/svg/icon_replace_outlined.svg'
import { ChatInfo } from '@/api/chat.ts'
import RecentQuestion from '@/views/chat/RecentQuestion.vue'
import RecommendQuestionQuick from '@/views/chat/RecommendQuestionQuick.vue'
const activeName = ref('recommend')
const recommendQuestionRef = ref()
const recentQuestionRef = ref()
const popoverRef = ref()
const getRecommendQuestions = () => {
  recommendQuestionRef.value.getRecommendQuestions(10)
}

const questions = '[]'
const retrieveQuestions = () => {
  recommendQuestionRef.value.getRecommendQuestions(10, true)
  recentQuestionRef.value.getRecentQuestions()
}
const quickAsk = (question: string) => {
  if (props.disabled) {
    return
  }
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

const onTitleChange = (title: string) => {
  activeName.value = title
}
onMounted(() => {
  getRecommendQuestions()
})

const emits = defineEmits(['quickAsk', 'loadingOver', 'stop'])
defineExpose({ getRecommendQuestions, id: () => props.recordId, stop })

const props = withDefaults(
  defineProps<{
    recordId?: number
    datasourceId?: number
    currentChat?: ChatInfo
    firstChat?: boolean
    disabled?: boolean
  }>(),
  {
    recordId: undefined,
    datasourceId: undefined,
    currentChat: () => new ChatInfo(),
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
    :width="240"
  >
    <el-tooltip effect="dark" :offset="8" :content="$t('qa.retrieve_again')" placement="top">
      <el-button class="tool-btn refresh_icon" text :disabled="disabled" @click="retrieveQuestions">
        <el-icon size="18">
          <icon_replace_outlined />
        </el-icon>
      </el-button>
    </el-tooltip>
    <div style="display: flex">
      <div
        class="quick_question_title"
        :class="{ 'title-active': activeName == 'recommend' }"
        @click="onTitleChange('recommend')"
      >
        {{ $t('qa.recommend') }}
      </div>
      <div
        class="quick_question_title"
        :class="{ 'title-active': activeName == 'recently' }"
        @click="onTitleChange('recently')"
      >
        {{ $t('qa.recently') }}
      </div>
    </div>
    <div class="quick_question_content">
      <RecommendQuestionQuick
        v-show="activeName === 'recommend'"
        ref="recommendQuestionRef"
        :current-chat="currentChat"
        :record-id="recordId"
        :questions="questions"
        :datasource="datasourceId"
        :disabled="disabled"
        :first-chat="firstChat"
        position="input"
        @click-question="quickAsk"
        @stop="onChatStop"
        @loading-over="loadingOver"
      />
      <RecentQuestion
        v-show="activeName == 'recently'"
        ref="recentQuestionRef"
        :disabled="disabled"
        :datasource-id="datasourceId"
        @click-question="quickAsk"
      >
      </RecentQuestion>
    </div>
    <template #reference>
      <el-button plain size="small">
        <el-icon size="16" style="margin-right: 4px">
          <icon_quick_question />
        </el-icon>
        {{ $t('qa.quick_question') }}
      </el-button>
    </template>
  </el-popover>
</template>

<style lang="less">
.quick_question_popover {
  padding: 4px !important;
  .quick_question_title {
    min-width: 40px;
    height: 24px;
    border-radius: 6px;
    opacity: 1;
    padding: 2px 8px;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(31, 35, 41, 0.1);
    cursor: pointer;
    margin-left: 8px;
    &:hover {
      color: var(--ed-color-primary-15-d, #189e7a);
      background: #1f23291a;
    }
  }
  .title-active {
    color: rgba(24, 158, 122, 1);
    background: rgba(28, 186, 144, 0.2);
  }
  .quick_question_content {
    height: 168px;
    margin-top: 4px;
    padding: 4px 4px 4px 4px;
    overflow-y: auto;
  }
  .ed-popover__title {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 0;
    height: 32px;
    display: flex;
    align-items: center;
    padding: 0 8px;
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
    &:hover {
      background-color: #1f23291a !important;
    }
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
