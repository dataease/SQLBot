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
const props = withDefaults(
  defineProps<{
    inPopover?: boolean
    chatList?: Array<ChatInfo>
    currentChatId?: number
    currentChat?: ChatInfo
    loading?: boolean
    appName?: string
    /** 会话列表停靠在 layout 左侧槽位（与主导航同列） */
    layoutDocked?: boolean
  }>(),
  {
    chatList: () => [],
    currentChatId: undefined,
    currentChat: () => new ChatInfo(),
    loading: false,
    inPopover: false,
    appName: '',
    layoutDocked: false,
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

const selectAssistantDs = computed(() => {
  return assistantStore.getAssistant && !assistantStore.getAutoDs
})

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
  <el-container class="chat-container-right-container" :class="{ 'layout-docked': layoutDocked }">
    <el-header class="chat-list-header" :class="{ 'in-popover': inPopover, 'layout-docked': layoutDocked }">
      <div v-if="!inPopover && !layoutDocked" class="title">
        <div>{{ appName || t('qa.title') }}</div>
        <el-button link type="primary" class="icon-btn" @click="onClickSideBarBtn">
          <el-icon>
            <icon_sidebar_outlined />
          </el-icon>
        </el-button>
      </div>
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

    <ChatCreator
      v-if="isCompletePage || selectAssistantDs"
      ref="chatCreatorRef"
      @on-chat-created="onChatCreated"
    />
  </el-container>
</template>

<style scoped lang="less">
.chat-container-right-container {
  background: rgba(245, 246, 247, 1);

  height: 100%;

  &.layout-docked {
    min-height: 0;

    .chat-list {
      padding: 2px 0 16px 0;
    }
  }

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

    &.layout-docked {
      --ed-header-padding: 10px 12px 4px;
      --ed-header-height: calc(10px + 4px + 32px + 4px);
      gap: 0;
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

    &.layout-docked .search {
      :deep(.ed-input__wrapper) {
        box-shadow: none;
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
