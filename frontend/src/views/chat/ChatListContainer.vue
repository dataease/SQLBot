<script setup lang="ts">
import { Search } from '@element-plus/icons-vue'
import ChatList from '@/views/chat/ChatList.vue'
import { useI18n } from 'vue-i18n'
import { computed, nextTick, ref } from 'vue'
import { Chat, chatApi, ChatInfo } from '@/api/chat.ts'
import { filter, includes } from 'lodash-es'
import ChatCreator from '@/views/chat/ChatCreator.vue'
import { useAssistantStore } from '@/stores/assistant'
import icon_sidebar_outlined from '@/assets/svg/icon_sidebar_outlined.svg'
import icon_new_chat_outlined from '@/assets/svg/icon_new_chat_outlined.svg'
import { useUserStore } from '@/stores/user'
import router from '@/router'
const userStore = useUserStore()
const props = withDefaults(
  defineProps<{
    inPopover?: boolean
    chatList?: Array<ChatInfo>
    currentChatId?: number
    currentChat?: ChatInfo
    loading?: boolean
    appName?: string
  }>(),
  {
    chatList: () => [],
    currentChatId: undefined,
    currentChat: () => new ChatInfo(),
    loading: false,
    inPopover: false,
    appName: '',
  }
)

const emits = defineEmits([
  'goEmpty',
  'onChatCreated',
  'onClickHistory',
  'onChatDeleted',
  'onChatRenamed',
  'onClickSideBarBtn',
  'update:loading',
  'update:chatList',
  'update:currentChat',
  'update:currentChatId',
])

const assistantStore = useAssistantStore()
const isCompletePage = computed(() => !assistantStore.getAssistant || assistantStore.getEmbedded)

const search = ref<string>()

const _currentChatId = computed({
  get() {
    return props.currentChatId
  },
  set(v) {
    emits('update:currentChatId', v)
  },
})
const _currentChat = computed({
  get() {
    return props.currentChat
  },
  set(v) {
    emits('update:currentChat', v)
  },
})

const _chatList = computed({
  get() {
    return props.chatList
  },
  set(v) {
    emits('update:chatList', v)
  },
})

const computedChatList = computed<Array<ChatInfo>>(() => {
  if (search.value && search.value.length > 0) {
    return filter(_chatList.value, (c) =>
      includes(c.brief?.toLowerCase(), search.value?.toLowerCase())
    )
  } else {
    return _chatList.value
  }
})

const _loading = computed({
  get() {
    return props.loading
  },
  set(v) {
    emits('update:loading', v)
  },
})

const { t } = useI18n()

function onClickSideBarBtn() {
  emits('onClickSideBarBtn')
}

function onChatCreated(chat: ChatInfo) {
  _chatList.value.unshift(chat)
  _currentChatId.value = chat.id
  _currentChat.value = chat
  emits('onChatCreated', chat)
}

const chatCreatorRef = ref()

function goEmpty(func?: (...p: any[]) => void, ...params: any[]) {
  _currentChat.value = new ChatInfo()
  _currentChatId.value = undefined
  emits('goEmpty', func, ...params)
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
  goEmpty(doCreateNewChat)
}

async function doCreateNewChat() {
  if (!isCompletePage.value) {
    return
  }
  chatCreatorRef.value?.showDs()
}

function onClickHistory(chat: Chat) {
  if (chat !== undefined && chat.id !== undefined) {
    if (_currentChatId.value === chat.id) {
      return
    }
    goEmpty(goHistory, chat)
  }
}

function goHistory(chat: Chat) {
  nextTick(() => {
    if (chat !== undefined && chat.id !== undefined) {
      _currentChat.value = new ChatInfo(chat)
      _currentChatId.value = chat.id
      _loading.value = true
      chatApi
        .get(chat.id)
        .then((res) => {
          const info = chatApi.toChatInfo(res)
          if (info && info.id === _currentChatId.value) {
            _currentChat.value = info

            // scrollToBottom()
            emits('onClickHistory', info)
          }
        })
        .finally(() => {
          _loading.value = false
        })
    }
  })
}

function onChatDeleted(id: number) {
  for (let i = 0; i < _chatList.value.length; i++) {
    if (_chatList.value[i].id === id) {
      _chatList.value.splice(i, 1)
      break
    }
  }
  if (id === _currentChatId.value) {
    goEmpty()
  }
  emits('onChatDeleted', id)
}

function onChatRenamed(chat: Chat) {
  _chatList.value.forEach((c: Chat) => {
    if (c.id === chat.id) {
      c.brief = chat.brief
    }
  })
  if (_currentChat.value.id === chat.id) {
    _currentChat.value.brief = chat.brief
  }
  emits('onChatRenamed', chat)
}
</script>

<template>
  <el-container class="chat-container-right-container">
    <el-header class="chat-list-header" :class="{ 'in-popover': inPopover }">
      <div v-if="!inPopover" class="title">
        <div>{{ appName || t('qa.title') }}</div>
        <el-button link type="primary" class="icon-btn" @click="onClickSideBarBtn">
          <el-icon>
            <icon_sidebar_outlined />
          </el-icon>
        </el-button>
      </div>
      <el-button class="btn" type="primary" @click="createNewChat">
        <el-icon style="margin-right: 6px">
          <icon_new_chat_outlined />
        </el-icon>
        {{ t('qa.new_chat') }}
      </el-button>
      <el-input
        v-model="search"
        :prefix-icon="Search"
        class="search"
        name="quick-search"
        autocomplete="off"
        :placeholder="t('qa.chat_search')"
        clearable
        @click.stop
      />
    </el-header>
    <el-main class="chat-list">
      <div v-if="!computedChatList.length" class="empty-search">
        {{ !!search ? $t('datasource.relevant_content_found') : $t('dashboard.no_chat') }}
      </div>
      <ChatList
        v-else
        v-model:loading="_loading"
        :current-chat-id="_currentChatId"
        :chat-list="computedChatList"
        @chat-selected="onClickHistory"
        @chat-deleted="onChatDeleted"
        @chat-renamed="onChatRenamed"
      />
    </el-main>

    <ChatCreator v-if="isCompletePage" ref="chatCreatorRef" @on-chat-created="onChatCreated" />
  </el-container>
</template>

<style scoped lang="less">
.chat-container-right-container {
  background: rgba(245, 246, 247, 1);

  height: 100%;

  .icon-btn {
    min-width: unset;
    width: 26px;
    height: 26px;
    font-size: 18px;

    &:hover {
      background: rgba(31, 35, 41, 0.1);
    }
  }

  .chat-list-header {
    --ed-header-padding: 16px;
    --ed-header-height: calc(16px + 24px + 16px + 40px + 16px + 32px + 16px);

    &.in-popover {
      --ed-header-height: calc(16px + 40px + 16px + 32px + 16px);
    }

    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 16px;

    .title {
      height: 24px;
      width: 100%;
      display: flex;
      flex-direction: row;
      align-items: center;
      justify-content: space-between;
      font-weight: 500;
    }

    .btn {
      width: 100%;
      height: 40px;

      font-size: 16px;
      font-weight: 500;

      --ed-button-text-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
      --ed-button-bg-color: var(--ed-color-primary-1a, #1cba901a);
      --ed-button-border-color: var(--ed-color-primary-60, #a4e3d3);
      --ed-button-hover-bg-color: var(--ed-color-primary-80, #d2f1e9);
      --ed-button-hover-text-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
      --ed-button-hover-border-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
      --ed-button-active-bg-color: var(--ed-color-primary-60, #a4e3d3);
      --ed-button-active-border-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
    }

    .search {
      height: 32px;
      width: 100%;
      :deep(.ed-input__wrapper) {
        background-color: #f5f6f7;
      }
    }
  }

  .chat-list {
    padding: 0 0 20px 0;

    .empty-search {
      width: 100%;
      text-align: center;
      margin-top: 80px;
      color: #646a73;
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;
    }
  }
}
</style>
