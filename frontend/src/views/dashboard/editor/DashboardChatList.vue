<script setup lang="ts">
import { type Chat } from '@/api/chat.ts'
import { ElIcon } from 'element-plus-secondary'
import { Icon } from '@/components/icon-custom'
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'

const props = withDefaults(
  defineProps<{
    currentChatId?: number
    chatList: Array<Chat>
  }>(),
  {
    currentChatId: undefined,
    chatList: () => [],
  }
)
const { t } = useI18n()
const emits = defineEmits(['chatSelected'])
const filterText = ref('')

function onClickHistory(chat: Chat) {
  emits('chatSelected', chat)
}

const now = new Date()
const startOfWeek = new Date(now)
startOfWeek.setDate(now.getDate() - now.getDay() + (now.getDay() === 0 ? -6 : 1)) // 设置为本周一
startOfWeek.setHours(0, 0, 0, 0)

const filteredAndGroupedData = computed(() => {
  const today: Chat[] = []
  const thisWeek: Chat[] = []
  const earlier: Chat[] = []

  const filteredList = props.chatList.filter(
    (chat) =>
      !filterText.value ||
      (chat.brief && chat.brief.toLowerCase().includes(filterText.value.toLowerCase()))
  )

  filteredList.forEach((item) => {
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    const itemDate = new Date(item.create_time)

    if (
      itemDate.getDate() === now.getDate() &&
      itemDate.getMonth() === now.getMonth() &&
      itemDate.getFullYear() === now.getFullYear()
    ) {
      today.push(item)
    } else if (itemDate >= startOfWeek && itemDate < now) {
      thisWeek.push(item)
    } else {
      earlier.push(item)
    }
  })

  return { today, thisWeek, earlier }
})
</script>

<template>
  <div style="width: 100%; height: 100%">
    <el-input
      v-model="filterText"
      :placeholder="t('dashboard.search')"
      clearable
      class="search-bar"
    >
      <template #prefix>
        <el-icon>
          <Icon name="icon_search-outline_outlined">
            <icon_searchOutline_outlined class="svg-icon" />
          </Icon>
        </el-icon>
      </template>
    </el-input>
    <el-scrollbar ref="chatListRef" class="custom-chart-list">
      <div class="chat-list-inner flex-gap-fallback flex-col">
        <!-- today -->
        <div v-if="filteredAndGroupedData.today.length > 0" class="time-group flex-gap-fallback flex-col">
          <div class="time-group-title">{{ t('dashboard.today') }}</div>
          <div
            v-for="chat in filteredAndGroupedData.today"
            :key="chat.id"
            class="chat-list-item"
            :class="{ active: currentChatId === chat.id }"
            @click="onClickHistory(chat)"
          >
            <span class="title">{{ chat.brief ?? 'Untitled' }}</span>
          </div>
        </div>

        <!-- this week -->
        <div v-if="filteredAndGroupedData.thisWeek.length > 0" class="time-group flex-gap-fallback flex-col">
          <div class="time-group-title">{{ t('dashboard.this_week') }}</div>
          <div
            v-for="chat in filteredAndGroupedData.thisWeek"
            :key="chat.id"
            class="chat-list-item"
            :class="{ active: currentChatId === chat.id }"
            @click="onClickHistory(chat)"
          >
            <span class="title">{{ chat.brief ?? 'Untitled' }}</span>
          </div>
        </div>

        <!-- earlier -->
        <div v-if="filteredAndGroupedData.earlier.length > 0" class="time-group flex-gap-fallback flex-col">
          <div class="time-group-title">{{ t('dashboard.earlier') }}</div>
          <div
            v-for="chat in filteredAndGroupedData.earlier"
            :key="chat.id"
            class="chat-list-item"
            :class="{ active: currentChatId === chat.id }"
            @click="onClickHistory(chat)"
          >
            <span class="title">{{ chat.brief ?? 'Untitled' }}</span>
          </div>
        </div>

        <!-- no data -->
        <div
          v-if="
            filteredAndGroupedData.today.length === 0 &&
            filteredAndGroupedData.thisWeek.length === 0 &&
            filteredAndGroupedData.earlier.length === 0
          "
          class="no-data"
        >
          {{ t('dashboard.no_data') }}
        </div>
      </div>
    </el-scrollbar>
  </div>
</template>

<style scoped lang="less">
.chat-list-inner {
  --hover-color: var(--ed-color-primary-light-9);
  --active-color: var(--hover-color);

  padding-left: 14px;
  padding-right: 14px;
  width: 100%;

  display: flex;
  flex-direction: column;

  --gap-size: 8px;
  gap: 8px;

  .time-group {
    display: flex;
    flex-direction: column;
    --gap-size: 8px;
    gap: 8px;
    margin-top: 12px;

    &:first-child {
      margin-top: 0;
    }

    .time-group-title {
      font-size: 12px;
      color: rgba(100, 106, 115, 1);
      padding: 4px 8px;
      font-weight: 500;
    }
  }

  .chat-list-item {
    width: 100%;
    height: 42px;
    cursor: pointer;
    border-radius: 6px;
    line-height: 1em;
    margin-bottom: 2px;

    display: flex;
    align-items: center;
    padding: 8px;

    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;

    .title {
      flex: 1;
      width: 0;
      color: rgba(31, 35, 41, 1);
      font-size: 14px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .icon-more {
      margin-left: auto;
      display: none;

      min-width: unset;
    }

    &:hover {
      background-color: rgba(255, 255, 255, 0.75);

      .icon-more {
        display: inline-flex;
      }
    }

    &.active {
      background-color: rgba(255, 255, 255, 1);
    }
  }

  .no-data {
    text-align: center;
    padding: 16px;
    margin-top: 140px;
    color: var(--ed-text-color-placeholder);
    font-size: 14px;
  }
}
.custom-chart-list {
  height: calc(100% - 32px);
}
.search-bar {
  padding: 0 12px 10px 12px;
  width: 100%;
  --ed-input-bg-color: rgba(245, 246, 247, 1);
}
</style>
