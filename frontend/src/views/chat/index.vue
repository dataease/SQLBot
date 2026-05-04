<template>
  <el-icon
    v-if="assistantStore.assistant && !assistantStore.pageEmbedded && assistantStore.type != 4"
    class="show-history_icon"
    :class="{ 'embedded-history-hidden': embeddedHistoryHidden }"
    size="20"
    @click="showFloatPopover"
  >
    <icon_sidebar_outlined></icon_sidebar_outlined>
  </el-icon>
  <el-container class="chat-container no-padding">
    <Teleport
      defer
      v-if="useTeleportHistory && (isCompletePage || pageEmbedded) && chatListSideBarShow"
      to="#layout-chat-history"
    >
      <ChatListContainer
        v-model:chat-list="chatList"
        v-model:current-chat-id="currentChatId"
        v-model:current-chat="currentChat"
        v-model:loading="loading"
        :in-popover="false"
        :layout-docked="true"
        :app-name="customName"
        @go-empty="goEmpty"
        @on-chat-created="onChatCreated"
        @on-click-history="onClickHistory"
        @on-chat-deleted="onChatDeleted"
        @on-chat-renamed="onChatRenamed"
        @on-click-side-bar-btn="hideSideBar"
      />
    </Teleport>

    <el-aside
      v-else-if="(isCompletePage || pageEmbedded) && chatListSideBarShow"
      class="chat-container-left"
      :class="{ 'embedded-history-hidden': embeddedHistoryHidden }"
    >
      <ChatListContainer
        v-model:chat-list="chatList"
        v-model:current-chat-id="currentChatId"
        v-model:current-chat="currentChat"
        v-model:loading="loading"
        :in-popover="!chatListSideBarShow"
        :app-name="customName"
        @go-empty="goEmpty"
        @on-chat-created="onChatCreated"
        @on-click-history="onClickHistory"
        @on-chat-deleted="onChatDeleted"
        @on-chat-renamed="onChatRenamed"
        @on-click-side-bar-btn="hideSideBar"
      />
    </el-aside>

    <div
      v-if="(!isCompletePage && !pageEmbedded) || !chatListSideBarShow"
      class="hidden-sidebar-btn"
      :class="{
        'assistant-popover-sidebar': !isCompletePage && !pageEmbedded,
        'embedded-history-hidden': embeddedHistoryHidden,
      }"
    >
      <el-popover
        :width="280"
        placement="bottom-start"
        popper-class="popover-chat_history"
        :popper-style="{ ...defaultFloatPopoverStyle }"
        :disabled="isPhone"
      >
        <template #reference>
          <el-button link type="primary" class="icon-btn" @click="showSideBar">
            <el-icon>
              <icon_sidebar_outlined />
            </el-icon>
          </el-button>
        </template>
        <ChatListContainer
          ref="floatPopoverRef"
          v-model:chat-list="chatList"
          v-model:current-chat-id="currentChatId"
          v-model:current-chat="currentChat"
          v-model:loading="loading"
          :in-popover="!chatListSideBarShow"
          :app-name="customName"
          @go-empty="goEmpty"
          @on-chat-created="onChatCreated"
          @on-click-history="onClickHistory"
          @on-chat-deleted="onChatDeleted"
          @on-chat-renamed="onChatRenamed"
          @on-click-side-bar-btn="hideSideBar"
        />
      </el-popover>

      <el-drawer
        v-model="floatPopoverVisible"
        :with-header="false"
        :modal="false"
        direction="ltr"
        size="278"
        modal-class="assistant-popover_sidebar"
        :before-close="hideSideBar"
      >
        <ChatListContainer
          ref="floatPopoverRef"
          v-model:chat-list="chatList"
          v-model:current-chat-id="currentChatId"
          v-model:current-chat="currentChat"
          v-model:loading="loading"
          :app-name="customName"
          :in-popover="false"
          @go-empty="goEmpty"
          @on-chat-created="onChatCreated"
          @on-click-history="onClickHistory"
          @on-chat-deleted="onChatDeleted"
          @on-chat-renamed="onChatRenamed"
          @on-click-side-bar-btn="hideSideBar"
        />
      </el-drawer>

      <el-tooltip effect="dark" :offset="8" :content="t('qa.new_chat')" placement="bottom">
        <el-button link type="primary" class="icon-btn" @click="createNewChatSimple">
          <el-icon>
            <icon_new_chat_outlined />
          </el-icon>
        </el-button>
      </el-tooltip>
    </div>
    <el-container :loading="loading" class="chat-inner-wrap">
      <el-main
        class="chat-record-list"
        :class="{
          'hide-sidebar': (isCompletePage || pageEmbedded) && !chatListSideBarShow,
          'assistant-chat-main': !isCompletePage && !pageEmbedded,
          'chat-record-list--with-toolbar': isCompletePage,
        }"
      >
        <div v-if="isCompletePage" class="chat-main-top-toolbar">
          <el-tooltip effect="dark" :offset="8" :content="t('qa.new_chat')" placement="bottom">
            <el-button circle type="primary" plain class="chat-main-new-chat-btn" @click="createNewChatSimple">
              <el-icon><icon_new_chat_outlined /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
        <div v-if="computedMessages.length == 0 && !loading" class="welcome-content-block">
          <div class="chat-home-stack">
            <div class="chat-home-stack__top">
              <div class="welcome-content">
                <template v-if="isCompletePage">
                  <div class="greeting">
                    <img v-if="loginBg" height="32" width="32" :src="loginBg" alt="" />
                    <el-icon v-else size="32"
                      ><custom_small></custom_small
                    ></el-icon>
                    {{ appearanceStore.pc_welcome ?? '你好，我是 SQLBot' }}
                  </div>
                  <div class="sub">
                    {{
                      appearanceStore.pc_welcome_desc ??
                      '我可以查询数据、生成图表、检测数据异常、预测数据等赶快开启智能问数吧～'
                    }}
                  </div>
                </template>

                <div v-else class="assistant-desc">
                  <img
                    v-if="logoAssistant"
                    :src="logoAssistant"
                    class="logo"
                    width="30px"
                    height="30px"
                    alt=""
                  />
                  <el-icon v-else size="32">
                    <logo_fold />
                  </el-icon>
                  <div class="i-am">{{ welcome }}</div>
                  <div class="i-can">{{ welcomeDesc }}</div>
                </div>

                <el-button
                  v-if="(isCompletePage || selectAssistantDs) && currentChatId === undefined"
                  size="large"
                  type="primary"
                  class="greeting-btn"
                  @click="createNewChatSimple"
                >
                  <span class="inner-icon">
                    <el-icon>
                      <icon_new_chat_outlined />
                    </el-icon>
                  </span>
                  {{ t('qa.start_sqlbot') }}
                </el-button>
              </div>
            </div>

            <div
              v-if="isCompletePage && currentChatId === undefined && popularQuestionItems.length > 0"
              class="chat-home-stack__bottom"
            >
              <div class="home-quick-cards-title">{{ t('qa.home_quick_cards_title') }}</div>
              <div class="home-quick-cards-grid">
                <button
                  v-for="(item, idx) in popularQuestionItems"
                  :key="`${item.datasource_id}-${item.question}-${idx}`"
                  type="button"
                  class="home-quick-card"
                  :disabled="popularHomeBusy"
                  @click="startPopularChat(item)"
                >
                  <span class="home-quick-card__row home-quick-card__row--stack">
                    <span class="home-quick-card__meta">
                      <span v-if="item.datasource_name" class="home-quick-card__ds">{{
                        item.datasource_name
                      }}</span>
                      <template v-if="item.datasource_name">
                        <span class="home-quick-card__sep">：</span>
                      </template>
                      <span class="home-quick-card__title">{{ item.question }}</span>
                    </span>
                    <span v-if="item.count > 1" class="home-quick-card__count">{{ item.count }}</span>
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="computedMessages.length == 0 && loading" class="welcome-content-block">
          <div style="display: flex; align-items: center; height: 30px">
            <img
              v-if="logoAssistant || loginBg"
              height="30"
              width="30"
              :src="logoAssistant ? logoAssistant : loginBg"
              alt=""
            />
            <el-icon v-else size="30"
              ><custom_small></custom_small
            ></el-icon>
            <span style="margin-left: 12px">{{ appearanceStore.name }}</span>
          </div>
        </div>
        <el-scrollbar
          v-if="computedMessages.length > 0"
          ref="chatListRef"
          class="no-horizontal"
          @scroll="handleScroll"
        >
          <div
            ref="innerRef"
            class="chat-scroll"
            :class="{
              'no-sidebar': isCompletePage && !chatListSideBarShow,
              pad16: !isCompletePage,
              pad8: isPhone,
            }"
          >
            <template v-for="(message, _index) in computedMessages" :key="_index">
              <ChatRow
                :logo-assistant="logoAssistant"
                :current-chat="currentChat"
                :msg="message"
                :hide-avatar="message.first_chat"
              >
                <!--                <RecommendQuestion-->
                <!--                  v-if="message.role === 'assistant' && message.first_chat"-->
                <!--                  ref="recommendQuestionRef"-->
                <!--                  :current-chat="currentChat"-->
                <!--                  :record-id="message.record?.id"-->
                <!--                  :questions="message.recommended_question"-->
                <!--                  :disabled="isTyping"-->
                <!--                  :first-chat="message.first_chat"-->
                <!--                  @click-question="quickAsk"-->
                <!--                  @stop="onChatStop"-->
                <!--                  @loading-over="loadingOver"-->
                <!--                />-->
                <UserChat
                  v-if="message.role === 'user'"
                  :message="message"
                  :all-messages="computedMessages"
                />
                <template v-if="message.role === 'assistant' && !message.first_chat">
                  <ChartAnswer
                    v-if="
                      (message?.record?.analysis_record_id === undefined ||
                        message?.record?.analysis_record_id === null) &&
                      (message?.record?.predict_record_id === undefined ||
                        message?.record?.predict_record_id === null)
                    "
                    ref="chartAnswerRef"
                    :chat-list="chatList"
                    :current-chat="currentChat"
                    :current-chat-id="currentChatId"
                    :record-id="message.record?.id"
                    :loading="isTyping"
                    :message="message"
                    :reasoning-name="['sql_answer', 'chart_answer']"
                    @scroll-bottom="scrollToBottom"
                    @finish="onChartAnswerFinish"
                    @error="onChartAnswerError"
                    @stop="onChatStop"
                  >
                    <ErrorInfo :error="message.record?.error" class="error-container" />
                    <template #tool>
                      <ChatTokenTime
                        :record-id="message.record?.id"
                        :duration="message.record?.duration"
                        :total-tokens="message.record?.total_tokens"
                      />
                      <ChatToolBar v-if="!message.isTyping" :message="message">
                        <div class="tool-btns">
                          <el-tooltip
                            effect="dark"
                            :offset="8"
                            :content="t('qa.ask_again')"
                            placement="top"
                          >
                            <el-button
                              class="tool-btn"
                              text
                              :disabled="isTyping"
                              @click="askAgain(message)"
                            >
                              <el-icon size="18">
                                <icon_replace_outlined />
                              </el-icon>
                            </el-button>
                          </el-tooltip>
                          <template v-if="message.record?.chart">
                            <div class="divider"></div>
                            <div>
                              <el-button
                                class="tool-btn"
                                text
                                :disabled="isTyping"
                                @click="clickAnalysis(message.record?.id)"
                              >
                                <span class="tool-btn-inner">
                                  <el-icon size="18">
                                    <icon_screen_outlined />
                                  </el-icon>
                                  <span class="btn-text">
                                    {{ t('chat.data_analysis') }}
                                  </span>
                                </span>
                              </el-button>
                            </div>
                            <div>
                              <el-button
                                class="tool-btn"
                                text
                                :disabled="isTyping"
                                @click="clickPredict(message.record?.id)"
                              >
                                <span class="tool-btn-inner">
                                  <el-icon size="18">
                                    <icon_start_outlined />
                                  </el-icon>
                                  <span class="btn-text">
                                    {{ t('chat.data_predict') }}
                                  </span>
                                </span>
                              </el-button>
                            </div>
                          </template>
                        </div>
                      </ChatToolBar>
                    </template>
                    <template #footer>
                      <RecommendQuestion
                        ref="recommendQuestionRef"
                        :current-chat="currentChat"
                        :record-id="message.record?.id"
                        :questions="message.recommended_question"
                        :first-chat="message.first_chat"
                        :disabled="isTyping"
                        @click-question="quickAsk"
                        @loading-over="loadingOver"
                        @stop="onChatStop"
                      />
                    </template>
                  </ChartAnswer>
                  <AnalysisAnswer
                    v-if="
                      message?.record?.analysis_record_id !== undefined &&
                      message?.record?.analysis_record_id !== null
                    "
                    ref="analysisAnswerRef"
                    :chat-list="chatList"
                    :current-chat="currentChat"
                    :current-chat-id="currentChatId"
                    :loading="isTyping"
                    :message="message"
                    @finish="onAnalysisAnswerFinish"
                    @error="onAnalysisAnswerError"
                    @stop="onChatStop"
                  >
                    <ErrorInfo :error="message.record?.error" class="error-container" />
                    <template #tool>
                      <ChatTokenTime
                        :record-id="message.record?.id"
                        :duration="message.record?.duration"
                        :total-tokens="message.record?.total_tokens"
                      />
                      <ChatToolBar v-if="!message.isTyping" :message="message" />
                    </template>
                  </AnalysisAnswer>
                  <PredictAnswer
                    v-if="
                      message?.record?.predict_record_id !== undefined &&
                      message?.record?.predict_record_id !== null
                    "
                    ref="predictAnswerRef"
                    :chat-list="chatList"
                    :current-chat="currentChat"
                    :current-chat-id="currentChatId"
                    :record-id="message.record?.id"
                    :loading="isTyping"
                    :message="message"
                    @scroll-bottom="scrollToBottom"
                    @finish="onPredictAnswerFinish"
                    @error="onPredictAnswerError"
                    @stop="onChatStop"
                  >
                    <ErrorInfo :error="message.record?.error" class="error-container" />
                    <template #tool>
                      <ChatTokenTime
                        :record-id="message.record?.id"
                        :duration="message.record?.duration"
                        :total-tokens="message.record?.total_tokens"
                      />
                      <ChatToolBar v-if="!message.isTyping" :message="message" />
                    </template>
                  </PredictAnswer>
                </template>
              </ChatRow>
            </template>
          </div>
        </el-scrollbar>
      </el-main>
      <el-footer
        v-if="
          computedMessages.length > 0 ||
          (!isCompletePage && !selectAssistantDs) ||
          (currentChatId != null && (isCompletePage || selectAssistantDs))
        "
        class="chat-footer"
      >
        <div class="input-wrapper" @click="clickInput">
          <div v-if="isCompletePage || selectAssistantDs" class="datasource">
            <template v-if="currentChat.datasource && currentChat.datasource_name">
              {{ t('qa.selected_datasource') }}:
              <img
                v-if="currentChatEngineType"
                style="margin-left: 4px; margin-right: 4px"
                :src="currentChatEngineType"
                width="16px"
                height="16px"
                alt=""
              />
              <span class="name">
                {{ currentChat.datasource_name }}
              </span>
            </template>
          </div>
          <div v-if="computedMessages.length > 0 && currentChat.datasource" class="quick_question">
            <quick-question
              ref="quickQuestionRef"
              :datasource-id="currentChat.datasource"
              :current-chat="currentChat"
              :record-id="computedMessages[0].record?.id"
              :disabled="isTyping"
              :first-chat="
                currentChat.records.length === 1 && !!computedMessages[0]?.record?.first_chat
              "
              @quick-ask="quickAsk"
              @stop="onChatStop"
              @loading-over="loadingOver"
            ></quick-question>
          </div>
          <el-input
            ref="inputRef"
            v-model="inputMessage"
            :disabled="isTyping"
            clearable
            class="input-area"
            :class="[
              !isCompletePage && !selectAssistantDs && 'is-assistant',
              computedMessages.length > 0 && currentChat.datasource && 'has-quick-question',
              (isCompletePage || selectAssistantDs) &&
                currentChat.datasource &&
                currentChat.datasource_name &&
                'has-datasource',
            ]"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 8.583 }"
            :placeholder="t('qa.question_placeholder')"
            @keydown.enter.exact.prevent="($event: any) => sendMessage(undefined, $event)"
            @keydown.ctrl.enter.exact.prevent="handleCtrlEnter"
          />

          <el-button
            circle
            type="primary"
            class="input-icon"
            :disabled="isTyping"
            @click.stop="($event: any) => sendMessage(undefined, $event)"
          >
            <el-icon size="16">
              <icon_send_filled />
            </el-icon>
          </el-button>
        </div>
      </el-footer>
    </el-container>

    <ChatCreator
      v-if="isCompletePage || selectAssistantDs"
      ref="chatCreatorRef"
      @on-chat-created="onChatCreatedQuick"
    />
    <ChatCreator ref="hiddenChatCreatorRef" hidden @on-chat-created="onChatCreatedQuick" />
  </el-container>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Chat, chatApi, ChatInfo, type ChatMessage, ChatRecord } from '@/api/chat'
import ChatRow from './ChatRow.vue'
import ChartAnswer from './answer/ChartAnswer.vue'
import AnalysisAnswer from './answer/AnalysisAnswer.vue'
import PredictAnswer from './answer/PredictAnswer.vue'
import UserChat from './chat-block/UserChat.vue'
import RecommendQuestion from './RecommendQuestion.vue'
import ChatListContainer from './ChatListContainer.vue'
import ChatCreator from '@/views/chat/ChatCreator.vue'
import ChatTokenTime from '@/views/chat/ChatTokenTime.vue'
import ErrorInfo from './ErrorInfo.vue'
import ChatToolBar from './ChatToolBar.vue'
import { runQuestionStream } from '@/views/chat/answer/runQuestionStream.ts'
import { dsTypeWithImg } from '@/views/ds/js/ds-type'
import { useI18n } from 'vue-i18n'
import { find, forEach } from 'lodash-es'
import custom_small from '@/assets/svg/logo-custom_small.svg'
import icon_new_chat_outlined from '@/assets/svg/icon_new_chat_outlined.svg'
import icon_sidebar_outlined from '@/assets/svg/icon_sidebar_outlined.svg'
import icon_replace_outlined from '@/assets/svg/icon_replace_outlined.svg'
import icon_screen_outlined from '@/assets/svg/icon_screen_outlined.svg'
import icon_start_outlined from '@/assets/svg/icon_start_outlined.svg'
import logo_fold from '@/assets/svg/logo-custom_small.svg'
import icon_send_filled from '@/assets/svg/icon_send_filled.svg'
import { useAssistantStore } from '@/stores/assistant'
import { onClickOutside } from '@vueuse/core'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import { useUserStore } from '@/stores/user'
import { debounce } from 'lodash-es'
import { isMobile } from '@/utils/utils'
import router from '@/router'
import QuickQuestion from '@/views/chat/QuickQuestion.vue'
import { useChatConfigStore } from '@/stores/chatConfig.ts'
const userStore = useUserStore()
const props = defineProps<{
  startChatDsId?: number
  welcomeDesc?: string
  logoAssistant?: string
  welcome?: string
  appName?: string
  pageEmbedded?: boolean
}>()
const floatPopoverRef = ref()
const floatPopoverVisible = ref(false)
const assistantStore = useAssistantStore()
const defaultFloatPopoverStyle = ref({
  padding: '0',
  height: '654px',
  border: '1px solid rgba(222, 224, 227, 1)',
  borderRadius: '6px',
})

const isCompletePage = computed(() => !assistantStore.getAssistant || assistantStore.getEmbedded)
const embeddedHistoryHidden = computed(
  () => assistantStore.getAssistant && !assistantStore.getHistory
)
// const autoDs = computed(() => assistantStore.getAssistant && assistantStore.getAutoDs)
const selectAssistantDs = computed(() => {
  return assistantStore.getAssistant && !assistantStore.getAutoDs
})
const customName = computed(() => {
  if (!isCompletePage.value && props.pageEmbedded) return props.appName
  return ''
})
const { t } = useI18n()

const chatConfig = useChatConfigStore()

const isPhone = computed(() => {
  return isMobile()
})
const inputMessage = ref('')

const chatListRef = ref()
const innerRef = ref()
const chatCreatorRef = ref()

const scrollToBottom = debounce(() => {
  if (scrolling) return
  nextTick(() => {
    chatListRef.value?.scrollTo({
      top: chatListRef.value.wrapRef.scrollHeight,
      behavior: 'smooth',
    })
  })
}, 300)

const loading = ref<boolean>(false)
const chatList = ref<Array<ChatInfo>>([])
const appearanceStore = useAppearanceStoreWithOut()

const currentChatId = ref<number | undefined>()
const currentChat = ref<ChatInfo>(new ChatInfo())
const isTyping = ref<boolean>(false)
const loginBg = computed(() => {
  return appearanceStore.getLogin
})
const computedMessages = computed<Array<ChatMessage>>(() => {
  const messages: Array<ChatMessage> = []
  if (currentChatId.value === undefined) {
    return messages
  }
  for (let i = 0; i < currentChat.value.records.length; i++) {
    const record = currentChat.value.records[i]
    if (record.question !== undefined && !record.first_chat) {
      messages.push({
        role: 'user',
        create_time: record.create_time,
        record: record,
        content: record.question,
        index: i,
      })
    }
    messages.push({
      role: 'assistant',
      create_time: record.create_time,
      record: record,
      isTyping: i === currentChat.value.records.length - 1 && isTyping.value,
      first_chat: record.first_chat,
      recommended_question: record.recommended_question,
      index: i,
    })
  }

  return messages
})

const goEmpty = (func?: (...p: any[]) => void, ...param: any[]) => {
  inputMessage.value = ''
  stop(func, ...param)
}

let scrollTime: any
let scrollingTime: any
let scrollTopVal = 0
let scrolling = false
let userScrolledAway = false // 用户是否主动滚动离开底部

const scrollBottom = () => {
  if (scrolling) return
  if (!isTyping.value && !getRecommendQuestionsLoading.value) {
    clearInterval(scrollTime)
  }
  if (!chatListRef.value) {
    clearInterval(scrollTime)
    return
  }
  chatListRef.value!.setScrollTop(innerRef.value!.clientHeight)
}

const handleScroll = (val: any) => {
  scrollTopVal = val.scrollTop
  scrolling = true
  clearTimeout(scrollingTime)
  scrollingTime = setTimeout(() => {
    scrolling = false
  }, 400)

  const threshold =
    innerRef.value!.clientHeight - (document.querySelector('.chat-record-list')!.clientHeight - 20)
  const isNearBottom = scrollTopVal + 50 >= threshold

  // 用户滚动离开底部时，标记并停止自动滚动
  if (!isNearBottom) {
    userScrolledAway = true
    clearInterval(scrollTime)
    scrollTime = null
    return
  }

  // 用户滚回底部时，重置标记
  userScrolledAway = false

  // 只有用户在底部、没有主动滚走、且正在输入时才启动自动滚动
  if (!scrollTime && isTyping.value && !userScrolledAway) {
    scrollTime = setInterval(() => {
      scrollBottom()
    }, 300)
  }
}

const createNewChatSimple = async () => {
  currentChat.value = new ChatInfo()
  currentChatId.value = undefined
  await createNewChat()
}

const createNewChat = async () => {
  try {
    await chatApi.checkLLMModel()
  } catch (error: any) {
    console.error(error)
    let errorMsg = t('model.default_miss')
    let confirm_text = t('datasource.got_it')
    if (userStore.isAdmin) {
      errorMsg = t('model.default_miss_admin')
      confirm_text = t('model.to_config')
    }
    ElMessageBox.confirm(t('qa.ask_failed'), {
      confirmButtonType: 'primary',
      tip: errorMsg,
      showCancelButton: userStore.isAdmin,
      confirmButtonText: confirm_text,
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
      showClose: false,
      callback: (val: string) => {
        if (userStore.isAdmin && val === 'confirm') {
          router.push('/system/model')
        }
      },
    })
    return
  }
  goEmpty()
  if (!isCompletePage.value && !selectAssistantDs.value) {
    currentChat.value = new ChatInfo()
    currentChatId.value = undefined
    return
  }
  chatCreatorRef.value?.showDs()
}

function getChatList(callback?: () => void) {
  loading.value = true
  chatApi
    .list()
    .then((res) => {
      chatList.value = chatApi.toChatInfoList(res)
    })
    .catch((e) => {
      console.error('getChatList failed', e)
    })
    .finally(() => {
      loading.value = false
      if (callback && typeof callback === 'function') {
        callback()
      }
    })
}

function onClickHistory(chat: ChatInfo) {
  scrollToBottom()
  forEach(chat?.records, (record: ChatRecord) => {
    // getChatData(record.id)
    if (record.predict_record_id) {
      // getChatPredictData(record.id)
    }
  })
}

const currentChatEngineType = computed(() => {
  return (dsTypeWithImg.find((ele) => currentChat.value.ds_type === ele.type) || {}).img
})

function onChatDeleted(id: number) {
  console.info('deleted', id)
}

function onChatRenamed(chat: Chat) {
  console.info('renamed', chat)
}

const chatListSideBarShow = ref<boolean>(true)

/** 会话列表 Teleport 到 Layout 左侧槽位，形成「导航 + 历史」单列 */
const useTeleportHistory = computed(
  () => isCompletePage.value && !props.pageEmbedded && chatListSideBarShow.value
)

const popularQuestionItems = ref<
  Array<{ datasource_id: number; datasource_name: string; question: string; count: number }>
>([])
/** 首页热门卡片创建会话中：勿占用全局 loading，否则 .finally 会与 sendMessage 争抢 loading 导致首轮问数无响应 */
const popularHomeBusy = ref(false)

async function loadPopularQuestions() {
  if (!isCompletePage.value) {
    return
  }
  try {
    popularQuestionItems.value = await chatApi.popularQuestions(8)
  } catch (e) {
    console.error(e)
    popularQuestionItems.value = []
  }
}

async function startPopularChat(item: {
  datasource_id: number
  datasource_name: string
  question: string
}) {
  if (popularHomeBusy.value) {
    return
  }
  try {
    await chatApi.checkLLMModel()
  } catch (error: any) {
    console.error(error)
    let errorMsg = t('model.default_miss')
    let confirm_text = t('datasource.got_it')
    if (userStore.isAdmin) {
      errorMsg = t('model.default_miss_admin')
      confirm_text = t('model.to_config')
    }
    ElMessageBox.confirm(t('qa.ask_failed'), {
      confirmButtonType: 'primary',
      tip: errorMsg,
      showCancelButton: userStore.isAdmin,
      confirmButtonText: confirm_text,
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
      showClose: false,
      callback: (val: string) => {
        if (userStore.isAdmin && val === 'confirm') {
          router.push('/system/model')
        }
      },
    })
    return
  }
  const param: Record<string, unknown> = { datasource: item.datasource_id }
  let method = chatApi.startChat
  if (assistantStore.getAssistant) {
    param['origin'] = 2
    method = chatApi.startAssistantChat
  }
  popularHomeBusy.value = true
  method(param as any)
    .then(async (res) => {
      const chat = chatApi.toChatInfo(res)
      if (!chat || chat.id == null) {
        ElMessage.warning(t('qa.ask_failed'))
        return
      }
      onChatCreatedQuick(chat)
      inputMessage.value = item.question
      await nextTick()
      await sendMessage()
    })
    .catch((e: any) => {
      console.error(e)
      const detail = e?.response?.data?.detail ?? e?.response?.data?.message ?? e?.message
      ElMessage.error(typeof detail === 'string' ? detail : t('qa.ask_failed'))
    })
    .finally(() => {
      popularHomeBusy.value = false
    })
}

function hideSideBar() {
  if ((!isCompletePage.value && !props.pageEmbedded) || isPhone.value) {
    floatPopoverVisible.value = false
    return
  }
  chatListSideBarShow.value = false
}

function showSideBar() {
  if (isPhone.value) {
    showFloatPopover()
    return
  }
  chatListSideBarShow.value = true
}

/** 使用 layout 左侧槽位 Teleport 时，等目标节点与 defer 完成后再拉列表，避免首屏左侧空白 */
watch(
  useTeleportHistory,
  (ok) => {
    if (ok) {
      nextTick(() => {
        getChatList()
      })
    }
  },
  { flush: 'post', immediate: true }
)

function onChatCreatedQuick(chat: ChatInfo) {
  chatList.value.unshift(chat)
  currentChatId.value = chat.id
  currentChat.value = chat
  onChatCreated(chat)
}

const recommendQuestionRef = ref()
const quickQuestionRef = ref()

function onChatCreated(chat: ChatInfo) {
  if (chat.records.length === 1 && !chat.records[0].recommended_question) {
    // do nothing
  }
}

function getRecommendQuestions(id?: number) {
  nextTick(() => {
    if (recommendQuestionRef.value) {
      if (recommendQuestionRef.value instanceof Array) {
        for (let i = 0; i < recommendQuestionRef.value.length; i++) {
          const _id = recommendQuestionRef.value[i].id()
          if (_id === id) {
            recommendQuestionRef.value[i].getRecommendQuestions()
            break
          }
        }
      } else {
        recommendQuestionRef.value.getRecommendQuestions()
      }
    }
  })
}

function quickAsk(question: string) {
  inputMessage.value = question
  nextTick(() => {
    sendMessage()
  })
}

const chartAnswerRef = ref()
/** 完整页由 index 直接跑 runQuestionStream 时，与全局 stop() 联动中止 fetch */
const questionStreamUserAbort = ref(false)
const getRecommendQuestionsLoading = ref(false)
async function onChartAnswerFinish(id: number) {
  getRecommendQuestionsLoading.value = true
  loading.value = false
  isTyping.value = false
  getRecordUsage(id)
  getRecommendQuestions(id)
}

const loadingOver = () => {
  getRecommendQuestionsLoading.value = false
}

function onChartAnswerError(id: number) {
  loading.value = false
  isTyping.value = false
  getRecordUsage(id)
}

function onChatStop() {
  questionStreamUserAbort.value = true
  loading.value = false
  isTyping.value = false
  console.debug('onChatStop')
}
const assistantPrepareSend = async () => {
  if (
    !isCompletePage.value &&
    !selectAssistantDs.value &&
    (currentChatId.value == null || typeof currentChatId.value == 'undefined')
  ) {
    const assistantChat = await assistantStore.setChat()
    if (assistantChat) {
      onChatCreatedQuick(assistantChat as any)
    }
  }
}

const sendMessage = async (
  regenerate_record_id: number | undefined = undefined,
  $event: any = {}
) => {
  if ($event?.isComposing) {
    return
  }
  if (!inputMessage.value.trim()) return

  loading.value = true
  isTyping.value = true
  if (isCompletePage.value && innerRef.value) {
    scrollTopVal = innerRef.value!.clientHeight
    scrollTime = setInterval(() => {
      scrollBottom()
    }, 300)
  }
  await assistantPrepareSend()
  const currentRecord = new ChatRecord()
  currentRecord.create_time = new Date()
  currentRecord.chat_id = currentChatId.value
  currentRecord.question = inputMessage.value
  currentRecord.regenerate_record_id = regenerate_record_id
  currentRecord.sql_answer = ''
  currentRecord.sql = ''
  currentRecord.chart_answer = ''
  currentRecord.chart = ''

  currentChat.value.records.push(currentRecord)
  inputMessage.value = ''

  await nextTick()

  if (!isCompletePage.value && innerRef.value) {
    scrollTopVal = innerRef.value!.clientHeight
    scrollTime = setInterval(() => {
      scrollBottom()
    }, 300)
  }
  const recordIndex = currentChat.value.records.length - 1
  if (isCompletePage.value) {
    questionStreamUserAbort.value = false
    const chatId = currentChatId.value
    if (chatId == null) {
      loading.value = false
      isTyping.value = false
      ElMessage.error(t('qa.ask_failed'))
      return
    }
    try {
      await runQuestionStream({
        currentChat: currentChat.value,
        chatList: chatList.value,
        chatId,
        recordIndex,
        shouldAbort: () => questionStreamUserAbort.value,
        scrollBottom: () => scrollToBottom(),
        onFinish: (id) => {
          if (id != null) onChartAnswerFinish(id)
        },
        onError: (id) => {
          if (id != null) onChartAnswerError(id)
          else {
            loading.value = false
            isTyping.value = false
          }
        },
      })
    } catch (e: any) {
      loading.value = false
      isTyping.value = false
      const msg = e?.message
      if (msg && String(msg).length > 0) {
        try {
          ElMessage({
            message: msg,
            type: 'error',
            showClose: true,
          })
        } catch {
          /* ignore */
        }
      } else {
        ElMessage.error(t('qa.ask_failed'))
      }
    }
  } else {
    const cref = chartAnswerRef.value
    if (cref) {
      if (cref instanceof Array) {
        for (let i = 0; i < cref.length; i++) {
          const _index = cref[i].index()
          if (recordIndex === _index) {
            await cref[i].sendMessage()
            break
          }
        }
      } else {
        await cref.sendMessage()
      }
    }
  }
}

const analysisAnswerRef = ref()

async function onAnalysisAnswerFinish(id: number) {
  loading.value = false
  isTyping.value = false
  getRecordUsage(id)
  //await getRecommendQuestions(id)
}
function onAnalysisAnswerError(id: number) {
  loading.value = false
  isTyping.value = false
  getRecordUsage(id)
}

function askAgain(message: ChatMessage) {
  if (message.record?.question?.trim() === '') {
    return
  }
  // regenerate
  inputMessage.value = '/regenerate'
  let regenerate_record_id = message.record?.id
  if (message.record?.id == undefined && message.record?.regenerate_record_id) {
    //只有当前对话内，上一次执行失败的重试会进这里
    regenerate_record_id = message.record?.regenerate_record_id
  }
  if (regenerate_record_id) {
    inputMessage.value = inputMessage.value + ' ' + regenerate_record_id
  }
  nextTick(() => {
    sendMessage(regenerate_record_id)
  })
}

async function clickAnalysis(id?: number) {
  const baseRecord = find(currentChat.value.records, (value) => id === value.id)
  if (baseRecord == undefined) {
    return
  }

  loading.value = true
  isTyping.value = true

  const currentRecord = new ChatRecord()
  currentRecord.create_time = new Date()
  currentRecord.chat_id = baseRecord.chat_id
  currentRecord.question = baseRecord.question
  currentRecord.chart = baseRecord.chart
  currentRecord.data = baseRecord.data
  currentRecord.analysis_record_id = id
  currentRecord.analysis = ''

  currentChat.value.records.push(currentRecord)

  nextTick(async () => {
    const index = currentChat.value.records.length - 1
    if (analysisAnswerRef.value) {
      if (analysisAnswerRef.value instanceof Array) {
        for (let i = 0; i < analysisAnswerRef.value.length; i++) {
          const _index = analysisAnswerRef.value[i].index()
          if (index === _index) {
            await analysisAnswerRef.value[i].sendMessage()
            break
          }
        }
      } else {
        await analysisAnswerRef.value.sendMessage()
      }
    }
  })

  return
}

function getRecordUsage(recordId: any) {
  console.debug('getRecordUsage id: ', recordId)
  nextTick(() => {
    chatApi
      .get_chart_usage(recordId)
      .then((res) => {
        const logHistory = chatApi.toChatLogHistory(res)
        if (logHistory) {
          currentChat.value.records.forEach((record) => {
            if (record.id === recordId) {
              record.duration = logHistory.duration
              record.finish_time = logHistory.finish_time
              record.total_tokens = logHistory.total_tokens
            }
          })
        }
      })
      .catch((e) => {
        console.error(e)
      })
  })
}

const predictAnswerRef = ref()

async function onPredictAnswerFinish(id: number) {
  loading.value = false
  isTyping.value = false
  // console.debug('onPredictAnswerFinish: ', id)
  getRecordUsage(id)
  //await getRecommendQuestions(id)
}
function onPredictAnswerError(id: number) {
  loading.value = false
  isTyping.value = false
  getRecordUsage(id)
}

async function clickPredict(id?: number) {
  const baseRecord = find(currentChat.value.records, (value) => id === value.id)
  if (baseRecord == undefined) {
    return
  }

  loading.value = true
  isTyping.value = true

  const currentRecord = new ChatRecord()
  currentRecord.create_time = new Date()
  currentRecord.chat_id = baseRecord.chat_id
  currentRecord.question = baseRecord.question
  currentRecord.chart = baseRecord.chart
  currentRecord.data = baseRecord.data
  currentRecord.predict_record_id = id
  currentRecord.predict = ''
  currentRecord.predict_data = ''

  currentChat.value.records.push(currentRecord)

  nextTick(async () => {
    const index = currentChat.value.records.length - 1
    if (predictAnswerRef.value) {
      if (predictAnswerRef.value instanceof Array) {
        for (let i = 0; i < predictAnswerRef.value.length; i++) {
          const _index = predictAnswerRef.value[i].index()
          if (index === _index) {
            await predictAnswerRef.value[i].sendMessage()
            break
          }
        }
      } else {
        await predictAnswerRef.value.sendMessage()
      }
    }
  })

  return
}

const handleCtrlEnter = (e: KeyboardEvent) => {
  const textarea = e.target as HTMLTextAreaElement
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const value = textarea.value

  inputMessage.value = value.substring(0, start) + '\n' + value.substring(end)

  nextTick(() => {
    textarea.selectionStart = textarea.selectionEnd = start + 1
  })
}

const inputRef = ref()

function clickInput() {
  inputRef.value?.focus()
}

function stop(func?: (...p: any[]) => void, ...param: any[]) {
  questionStreamUserAbort.value = true
  if (recommendQuestionRef.value) {
    if (recommendQuestionRef.value instanceof Array) {
      for (let i = 0; i < recommendQuestionRef.value.length; i++) {
        recommendQuestionRef.value[i].stop()
      }
    } else {
      recommendQuestionRef.value.stop()
    }
  }
  if (chartAnswerRef.value) {
    if (chartAnswerRef.value instanceof Array) {
      for (let i = 0; i < chartAnswerRef.value.length; i++) {
        chartAnswerRef.value[i].stop()
      }
    } else {
      chartAnswerRef.value.stop()
    }
  }
  if (analysisAnswerRef.value) {
    if (analysisAnswerRef.value instanceof Array) {
      for (let i = 0; i < analysisAnswerRef.value.length; i++) {
        analysisAnswerRef.value[i].stop()
      }
    } else {
      analysisAnswerRef.value.stop()
    }
  }
  if (predictAnswerRef.value) {
    if (predictAnswerRef.value instanceof Array) {
      for (let i = 0; i < predictAnswerRef.value.length; i++) {
        predictAnswerRef.value[i].stop()
      }
    } else {
      predictAnswerRef.value.stop()
    }
  }
  if (func && typeof func === 'function') {
    func(...param)
  }
}
const showFloatPopover = () => {
  if ((!isCompletePage.value || isPhone.value) && !floatPopoverVisible.value) {
    floatPopoverVisible.value = true
  }
}
const registerClickOutside = () => {
  onClickOutside(floatPopoverRef, (event: any) => {
    if (floatPopoverVisible.value) {
      let parentElement: any = event.target
      let isEdOverlay = false
      while (parentElement) {
        if (parentElement.className.includes('ed-overlay')) {
          isEdOverlay = true
          break
        } else {
          parentElement = parentElement.parentElement
        }
      }
      if (isEdOverlay) return
      floatPopoverVisible.value = false
    }
  })
}
const assistantPrepareInit = () => {
  if (isCompletePage.value || props.pageEmbedded) {
    return
  }
  Object.assign(defaultFloatPopoverStyle.value, {
    height: '100% !important',
    inset: '0px auto auto 0px',
  })
  goEmpty()
  registerClickOutside()
}
defineExpose({
  createNewChat,
  showFloatPopover,
})

const hiddenChatCreatorRef = ref()

function jumpCreatChat() {
  if (props.startChatDsId) {
    const _id = props.startChatDsId
    nextTick(() => {
      hiddenChatCreatorRef.value?.createChat(_id)
    })
    const newUrl = window.location.hash.replace(/\?.*$/, '')
    history.replaceState({}, '', newUrl)
  }
}

onMounted(() => {
  chatConfig.fetchGlobalConfig()
  if (isPhone.value) {
    chatListSideBarShow.value = false
    if (props.pageEmbedded) {
      registerClickOutside()
    }
  }
  getChatList(jumpCreatChat)
  nextTick(() => {
    loadPopularQuestions()
  })
  assistantPrepareInit()
})
</script>

<style lang="less" scoped>
.chat-container {
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;

  border-radius: 12px;

  .chat-inner-wrap {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .chat-record-list--with-toolbar {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .chat-main-top-toolbar {
    flex-shrink: 0;
    padding: 12px 16px 4px;
    display: flex;
    justify-content: flex-start;
    align-items: center;
  }

  .chat-main-new-chat-btn {
    border-radius: 8px;
    border: none !important;
    --ed-button-border-color: transparent;
    --ed-button-hover-border-color: transparent;

    &:focus,
    &:focus-visible,
    &:hover,
    &:active {
      border: none !important;
    }
  }

  .welcome-content-block {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    padding-top: 0;
    padding-bottom: 24px;
  }

  .chat-home-stack {
    width: 100%;
    max-width: 880px;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    align-items: stretch;
  }

  .chat-home-stack__top {
    flex: 1 1 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }

  .chat-home-stack__bottom {
    position: relative;
    z-index: 2;
    margin-top: auto;
    width: 100%;
    padding-top: 24px;
    padding-bottom: 8px;
  }

  .home-quick-cards-wrap {
    margin-top: 28px;
    width: 100%;
    max-width: 880px;
    padding: 0 16px 24px;
  }

  .home-quick-cards-title {
    font-size: 13px;
    font-weight: 500;
    color: rgba(100, 106, 115, 1);
    margin-bottom: 14px;
    text-align: center;
    letter-spacing: 0.02em;
  }

  .home-quick-cards-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  @media (max-width: 640px) {
    .home-quick-cards-grid {
      grid-template-columns: 1fr;
    }
  }

  .home-quick-card {
    text-align: left;
    padding: 17px 16px;
    border-radius: 18px;
    border: 1px solid #e0e0e0;
    background: #ffffff;
    cursor: pointer;
    transition:
      border-color 0.15s,
      background 0.15s;

    &:hover {
      border-color: #0066cc;
      background: #ffffff;
    }

    &__row {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 8px;
      width: 100%;
    }

    &__row--stack {
      align-items: flex-start;
    }

    &__meta {
      flex: 1;
      min-width: 0;
      word-break: break-word;
      text-align: left;
      line-height: 1.43;
    }

    &__ds {
      color: #0066cc;
      font-weight: 600;
      font-size: 17px;
    }

    &__sep {
      color: #86868b;
      font-weight: 400;
    }

    &__title {
      font-size: 17px;
      font-weight: 400;
      color: #1d1d1f;
      line-height: 1.43;
      flex: 1;
      min-width: 0;
      word-break: break-word;
      text-align: left;
      letter-spacing: -0.374px;
    }

    &__count {
      flex-shrink: 0;
      font-size: 12px;
      font-weight: 400;
      line-height: 1.43;
      color: #86868b;
      padding: 0 8px;
      border-radius: 10px;
      background: rgba(0, 0, 0, 0.04);
    }

    &__desc {
      font-size: 12px;
      color: #86868b;
      line-height: 20px;
    }
  }
  .assistant-popover-sidebar {
    button {
      display: none;
    }
  }
  .hidden-sidebar-btn {
    z-index: 11;
    position: absolute;
    padding: 16px;
    top: 0;
    left: 0;
  }

  .icon-btn {
    min-width: unset;
    width: 26px;
    height: 26px;
    font-size: 18px;

    --ed-button-text-color: rgba(31, 35, 41, 1);
    --ed-button-hover-text-color: var(--ed-button-text-color);
    --ed-button-active-text-color: var(--ed-button-text-color);
    --ed-button-hover-link-text-color: var(--ed-button-text-color);
    &:hover {
      background: rgba(31, 35, 41, 0.1);
    }
  }

  .chat-container-left {
    --ed-aside-width: 280px;
    border-radius: 12px 0 0 12px;

    background: rgba(245, 246, 247, 1);
  }

  :deep(.chat-record-list) {
    padding: 0 0 20px 0;
    border-radius: 0 12px 12px 0;

    .no-horizontal.ed-scrollbar {
      position: relative;
      z-index: 10;
      .ed-scrollbar__bar.is-horizontal {
        display: none;
      }
    }

    &.hide-sidebar {
      border-radius: 12px;
    }
  }
  .assistant-chat-main {
    padding: 0 0 20px 0;
  }

  .chat-scroll {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-left: 56px;
    padding-right: 56px;

    &.no-sidebar {
      padding-left: 96px;
    }
    &.pad8 {
      padding: 8px;
    }

    &.pad16 {
      padding-left: 16px;
      padding-right: 16px;
    }
  }

  .chat-footer {
    min-height: calc(120px + 16px);
    max-height: calc(300px + 16px);
    height: fit-content;
    position: relative;
    z-index: 1;

    padding-bottom: 16px;

    display: flex;
    flex-direction: column;
    align-items: center;

    .input-wrapper {
      width: 100%;
      position: relative;
      max-width: 800px;

      .datasource {
        width: calc(100% - 2px);
        position: absolute;
        margin-left: 1px;
        margin-top: 1px;
        left: 0;
        top: 0;
        padding-top: 12px;
        padding-left: 12px;
        z-index: 10;
        background: transparent;
        line-height: 22px;
        font-size: 14px;
        font-weight: 400;
        border-top-right-radius: 16px;
        border-top-left-radius: 16px;
        color: rgba(100, 106, 115, 1);
        display: flex;
        align-items: center;

        .name {
          color: rgba(31, 35, 41, 1);
        }
      }

      .quick_question {
        min-width: 100px;
        position: absolute;
        margin-left: 1px;
        margin-top: 1px;
        left: 0;
        bottom: 0;
        padding-bottom: 12px;
        padding-left: 12px;
        z-index: 10;
        background: transparent;
        line-height: 22px;
        font-size: 14px;
        font-weight: 400;
        border-top-right-radius: 16px;
        border-top-left-radius: 16px;
        color: rgba(100, 106, 115, 1);
        display: flex;
        align-items: center;

        .name {
          color: rgba(31, 35, 41, 1);
        }
      }

      .input-area {
        border-color: var(--color-hairline);

        :deep(.ed-textarea__inner) {
          padding: 12px 60px 12px 20px;
          background: var(--color-canvas);
          border-radius: var(--radius-xl);
          line-height: 1.47;
          font-size: 16px;
          border: 1px solid var(--color-hairline);

          &::placeholder {
            color: var(--color-muted-soft);
            font-size: 13px;
            font-weight: 400;
            letter-spacing: 0;
            opacity: 0.75;
          }
        }

        &.has-datasource :deep(.ed-textarea__inner) {
          padding-top: 36px;
        }

        &.has-quick-question :deep(.ed-textarea__inner) {
          padding-bottom: 64px;
        }

        &.is-assistant {
          :deep(.ed-textarea__inner) {
            font-weight: 400;
            font-size: 16px;
            line-height: 1.47;
            border-radius: var(--radius-xl);
            letter-spacing: -0.01em;
          }
        }
      }

      .input-icon {
        min-width: unset;
        position: absolute;
        bottom: 12px;
        right: 12px;

        border-color: unset;

        &.is-disabled {
          background: rgba(187, 191, 196, 1);
          border-color: unset;
        }
      }
    }
  }

  .send-btn {
    min-width: 0;
  }
}

.error-container {
  margin-top: 12px;
}

.tool-btns {
  display: flex;
  flex-direction: row;
  align-items: center;
  flex-wrap: wrap;

  column-gap: 16px;
  row-gap: 8px;

  .tool-btn {
    font-size: 14px;
    font-weight: 400;
    letter-spacing: -0.224px;
    line-height: 1.29;
    color: #86868b;

    .tool-btn-inner {
      display: flex;
      flex-direction: row;
      align-items: center;
    }

    &:hover {
      background: rgba(0, 0, 0, 0.04);
      color: #1d1d1f;
    }
    &:active {
      background: rgba(0, 0, 0, 0.08);
      color: #1d1d1f;
    }
  }

  .btn-text {
    margin-left: 4px;
  }

  .divider {
    width: 1px;
    height: 16px;
    border-left: 1px solid rgba(0, 0, 0, 0.1);
  }
}

.welcome-content-block {
  height: 100%;
  width: 100%;

  display: flex;
  justify-content: center;
  align-items: center;

  .welcome-content {
    width: 100%;
    max-width: 800px;
    display: flex;
    gap: 16px;
    padding: 0 16px;
    align-items: center;
    flex-direction: column;

    .assistant-desc {
      width: 100%;
      display: flex;
      align-items: center;
      flex-direction: column;

      .i-am {
        font-weight: 600;
        font-size: 24px;
        line-height: 32px;
        margin: 16px 0;
        max-width: 100%;
        word-break: break-all;
        padding: 0 20px;
      }

      .i-can {
        margin-bottom: 4px;
        max-width: 350px;
        text-align: center;
        font-weight: 400;
        font-size: 14px;
        line-height: 24px;
        color: #646a73;
        max-width: 88%;
        word-break: break-all;
        padding: 0 20px;
      }
    }

    .greeting {
      display: flex;
      align-items: center;
      gap: 16px;
      line-height: 32px;
      font-size: 24px;
      font-weight: 600;
      color: rgba(31, 35, 41, 1);
    }

    .sub {
      color: grey;
      font-size: 16px;
      line-height: 24px;
    }

    .greeting-btn {
      width: 100%;
      height: 88px;
      border-radius: 18px;
      background: #ffffff;
      border: 1px solid #e0e0e0;

      .inner-icon {
        display: flex;
        flex-direction: row;
        align-items: center;

        margin-right: 6px;
      }

      font-size: 17px;
      line-height: 1.47;
      font-weight: 400;
      letter-spacing: -0.374px;
      color: #1d1d1f;

      --ed-button-text-color: #0066cc;
      --ed-button-hover-text-color: #0066cc;
      --ed-button-active-text-color: #0066cc;
      --ed-button-bg-color: #ffffff;
      --ed-button-hover-bg-color: rgba(0, 102, 204, 0.06);
      --ed-button-border-color: #e0e0e0;
      --ed-button-hover-border-color: #0066cc;
      --ed-button-active-bg-color: rgba(0, 102, 204, 0.1);
      --ed-button-active-border-color: #0066cc;
    }
  }
}
</style>

<style lang="less">
.assistant-popover_sidebar {
  .ed-drawer {
    height: 100% !important;
    margin-top: 0 !important;
  }
  .ed-drawer__body {
    padding: 0;
  }
}

.popover-chat_history {
  border: 1px solid #e0e0e0;
  border-radius: 18px !important;
  overflow: hidden;
  box-shadow: none !important;
}

.popover-chat_history_small {
  height: calc(100% - 54px);
  padding: 0 !important;
  border: 1px solid rgba(222, 224, 227, 1);
  border-radius: 6px;
}
.embedded-history-hidden {
  display: none !important;
}
.show-history_icon {
  cursor: pointer;
  position: absolute;
  top: 18px;
  left: 16px;
  z-index: 199;
  &::after {
    content: '';
    background-color: #1f23291a;
    position: absolute;
    border-radius: 6px;
    width: 28px;
    height: 28px;
    transform: translate(-50%, -50%);
    top: 50%;
    left: 50%;
    display: none;
  }

  &:hover {
    &::after {
      display: block;
    }
  }
}
</style>
