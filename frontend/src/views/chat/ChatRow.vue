<script setup lang="ts">
import { ChatInfo, type ChatMessage } from '@/api/chat.ts'
import logo_fold from '@/assets/LOGO-fold.svg'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import custom_small from '@/assets/svg/logo-custom_small.svg'

withDefaults(
  defineProps<{
    msg: ChatMessage
    currentChat: ChatInfo
    hideAvatar?: boolean
    logoAssistant?: string
  }>(),
  {
    hideAvatar: false,
  }
)
const appearanceStore = useAppearanceStoreWithOut()
</script>

<template>
  <div class="chat-row-container">
    <div class="chat-row" :class="{ 'right-to-left': msg.role === 'user' }">
      <div v-if="msg.role === 'assistant'" class="ai-avatar">
        <img
          v-if="!hideAvatar && appearanceStore.getLogin"
          :src="logoAssistant ? logoAssistant : appearanceStore.getLogin"
          alt=""
          width="28"
          height="28"
        />
        <el-icon v-else-if="!hideAvatar">
          <custom_small v-if="appearanceStore.themeColor === 'custom'"></custom_small>
          <logo_fold v-else />
        </el-icon>
      </div>
      <div :class="{ 'row-full': msg.role === 'assistant', 'width-auto': msg.role === 'user' }">
        <slot></slot>
      </div>
    </div>
    <slot name="footer"></slot>
  </div>
</template>

<style scoped lang="less">
.chat-row-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  max-width: 800px;

  .chat-row {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    gap: 8px;
    padding: 20px 0 0;

    width: 100%;

    &.right-to-left {
      flex-direction: row-reverse;
    }

    .row-full {
      flex: 1;
      width: 0;
    }

    .width-auto {
      width: auto;
      max-width: 100%;
    }

    .ai-avatar {
      font-size: 28px;
      background: transparent;
      width: 28px;
    }
  }
}
</style>
