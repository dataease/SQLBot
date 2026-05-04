<script lang="ts" setup>
import { ref, computed, onUnmounted, onBeforeMount, watch } from 'vue'
import Menu from './Menu.vue'
import custom_small from '@/assets/svg/logo-custom_small.svg'
import Workspace from './Workspace.vue'
import Person from './Person.vue'
import icon_moments_categories_outlined from '@/assets/svg/icon_moments-categories_outlined.svg'
import icon_side_fold_outlined from '@/assets/svg/icon_side-fold_outlined.svg'
import icon_side_expand_outlined from '@/assets/svg/icon_side-expand_outlined.svg'
import { useRoute, useRouter } from 'vue-router'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import { useEmitt } from '@/utils/useEmitt'
import { isMobile } from '@/utils/utils'

const isPhone = computed(() => {
  return isMobile()
})
const router = useRouter()
const collapse = ref(false)
const collapseCopy = ref(false)
const appearanceStore = useAppearanceStoreWithOut()
let time: any
onUnmounted(() => {
  clearTimeout(time)
})
const loginBg = computed(() => {
  return appearanceStore.getLogin
})
const handleCollapseChange = (val: any = true) => {
  collapseCopy.value = val
  clearTimeout(time)
  time = setTimeout(() => {
    collapse.value = val
  }, 100)
}
useEmitt({
  name: 'collapse-change',
  callback: handleCollapseChange,
})
const handleFoldExpand = () => {
  handleCollapseChange(!collapse.value)
}

const toWorkspace = () => {
  router.push('/')
}

const toChatIndex = () => {
  router.push('/chat/index')
}

const toUserIndex = () => {
  router.push('/system/user')
}
const route = useRoute()
const showSysmenu = computed(() => {
  return route.path.includes('/system')
})
const isChatRoute = computed(() => route.path.startsWith('/chat'))
const CHAT_LEFT_WIDTH_KEY = 'sqlbot-layout-chat-left-width'
const leftPanelWidth = ref(280)
let resizeActive = false

function onChatResizeStart(e: MouseEvent) {
  if (!isChatRoute.value || isPhone.value) return
  e.preventDefault()
  resizeActive = true
  const startX = e.clientX
  const startW = leftPanelWidth.value
  const onMove = (ev: MouseEvent) => {
    if (!resizeActive) return
    const dx = ev.clientX - startX
    leftPanelWidth.value = Math.min(520, Math.max(220, startW + dx))
  }
  const onUp = () => {
    resizeActive = false
    localStorage.setItem(CHAT_LEFT_WIDTH_KEY, String(leftPanelWidth.value))
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

watch(isChatRoute, (chat) => {
  if (chat) {
    const s = localStorage.getItem(CHAT_LEFT_WIDTH_KEY)
    if (s) {
      const n = parseInt(s, 10)
      if (!Number.isNaN(n)) {
        leftPanelWidth.value = Math.min(520, Math.max(220, n))
      }
    }
  }
})

onBeforeMount(() => {
  if (isPhone.value) {
    collapse.value = true
    collapseCopy.value = true
  }
  const s = localStorage.getItem(CHAT_LEFT_WIDTH_KEY)
  if (s) {
    const n = parseInt(s, 10)
    if (!Number.isNaN(n)) {
      leftPanelWidth.value = Math.min(520, Math.max(220, n))
    }
  }
})
</script>

<template>
  <div class="system-layout" :class="{ 'system-layout--chat': isChatRoute }">
    <div
      class="left-side"
      :class="[collapse && !isChatRoute && 'left-side-collapse', isChatRoute && 'left-side--chat']"
      :style="isChatRoute ? { width: leftPanelWidth + 'px', minWidth: '220px', maxWidth: '520px' } : undefined"
    >
      <div class="left-side-nav-block">
      <template v-if="showSysmenu">
        <div class="sys-management" @click="toUserIndex">
          <img
            v-if="loginBg"
            :style="{ marginLeft: collapse ? '5px' : 0 }"
            height="30"
            width="30"
            :src="loginBg"
            :class="!collapse && 'collapse-icon'"
            alt=""
            @click="toChatIndex"
          />
          <custom_small
            v-else
            :style="{ marginLeft: collapse ? '5px' : 0 }"
            :class="!collapse && 'collapse-icon'"
          ></custom_small>
          <span v-if="!collapse">{{ $t('training.system_management') }}</span>
        </div>
      </template>
      <template v-else>
        <template v-if="appearanceStore.isBlue">
          <img
            v-if="loginBg && collapse"
            style="margin: 0 0 6px 5px; cursor: pointer"
            height="30"
            width="30"
            :src="loginBg"
            alt=""
            @click="toChatIndex"
          />
          <div v-else-if="loginBg && !collapse" class="default-sqlbot">
            <img
              height="30"
              width="30"
              :src="loginBg"
              alt=""
              class="collapse-icon"
              @click="toChatIndex"
            />
            <span style="max-width: 150px" :title="appearanceStore.name" class="ellipsis">{{
              appearanceStore.name
            }}</span>
          </div>
          <custom_small
            v-else-if="collapse"
            :style="{ marginLeft: collapse ? '5px' : 0 }"
            :class="!collapse && 'collapse-icon'"
          ></custom_small>

          <div v-else class="default-sqlbot">
            <custom_small class="collapse-icon"></custom_small>
            <span style="max-width: 150px" :title="appearanceStore.name" class="ellipsis">{{
              appearanceStore.name
            }}</span>
          </div>
        </template>
        <template v-else-if="appearanceStore.themeColor === 'custom'">
          <img
            v-if="loginBg && collapse"
            style="margin: 0 0 6px 5px; cursor: pointer"
            height="30"
            width="30"
            :src="loginBg"
            alt=""
            @click="toChatIndex"
          />
          <div v-else-if="loginBg && !collapse" class="default-sqlbot">
            <img
              height="30"
              width="30"
              :src="loginBg"
              alt=""
              class="collapse-icon"
              @click="toChatIndex"
            />
            <span style="max-width: 150px" :title="appearanceStore.name" class="ellipsis">{{
              appearanceStore.name
            }}</span>
          </div>
          <custom_small
            v-else-if="collapse"
            style="margin: 0 0 6px 5px; cursor: pointer"
            @click="toChatIndex"
          ></custom_small>
          <div v-else class="default-sqlbot">
            <custom_small class="collapse-icon"></custom_small>
            <span style="max-width: 150px" :title="appearanceStore.name" class="ellipsis">{{
              appearanceStore.name
            }}</span>
          </div>
        </template>
        <template v-else>
          <img
            v-if="loginBg && collapse"
            style="margin: 0 0 6px 5px; cursor: pointer"
            height="30"
            width="30"
            :src="loginBg"
            alt=""
            @click="toChatIndex"
          />
          <div v-else-if="loginBg && !collapse" class="default-sqlbot">
            <img
              height="30"
              width="30"
              :src="loginBg"
              alt=""
              class="collapse-icon"
              @click="toChatIndex"
            />
            <span style="max-width: 150px" :title="appearanceStore.name" class="ellipsis">{{
              appearanceStore.name
            }}</span>
          </div>
          <custom_small
            v-else-if="collapse"
            style="margin: 0 0 6px 5px; cursor: pointer"
            @click="toChatIndex"
          ></custom_small>
          <div v-else class="default-sqlbot">
            <custom_small class="collapse-icon" @click="toChatIndex"></custom_small>
            <span style="max-width: 150px" :title="appearanceStore.name" class="ellipsis">{{
              appearanceStore.name
            }}</span>
          </div>
        </template>
      </template>
      <Workspace v-if="!showSysmenu" :collapse="collapse"></Workspace>
      <Menu :collapse="collapseCopy"></Menu>
      </div>
      <div v-if="isChatRoute" class="layout-chat-history-shell">
        <div class="layout-chat-history-divider" role="presentation" />
        <div class="layout-chat-history-heading">{{ $t('qa.chat_history_section') }}</div>
        <div id="layout-chat-history" class="layout-chat-history"></div>
      </div>
      <div class="bottom" :class="isChatRoute && 'bottom--flow'">
        <div
          v-if="showSysmenu"
          class="back-to_workspace"
          :class="collapse && 'collapse'"
          @click="toWorkspace"
        >
          <el-icon size="18">
            <icon_moments_categories_outlined></icon_moments_categories_outlined>
          </el-icon>
          {{ collapse ? '' : $t('workspace.return_to_workspace') }}
        </div>
        <div class="personal-info">
          <Person :collapse="collapse" :in-sysmenu="showSysmenu"></Person>
          <el-icon v-if="!isChatRoute" size="20" class="fold" @click="handleFoldExpand">
            <icon_side_expand_outlined v-if="collapse"></icon_side_expand_outlined>
            <icon_side_fold_outlined v-else></icon_side_fold_outlined>
          </el-icon>
        </div>
      </div>
    </div>
    <div
      v-if="isChatRoute && !isPhone"
      class="layout-column-resizer"
      @mousedown="onChatResizeStart"
    ></div>
    <div
      class="right-main"
      :class="[collapse && !isChatRoute && 'right-side-collapse', isChatRoute && 'right-main--chat']"
    >
      <div class="content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.system-layout {
  width: 100vw;
  height: 100vh;
  background-color: var(--color-canvas-parchment);
  display: flex;

  @keyframes rotate {
    0% {
      width: 240px;
    }
    100% {
      width: 64px;
    }
  }

  .left-side {
    width: 240px;
    height: 100%;
    padding: 16px;
    position: relative;
    min-width: 240px;
    background-color: var(--color-canvas);
    border-right: 1px solid var(--color-hairline);

    .default-sqlbot {
      display: flex;
      align-items: center;
      font-family: var(--font-sans);
      font-weight: 600;
      font-size: 17px;
      letter-spacing: -0.374px;
      color: var(--color-ink);
      cursor: pointer;
      margin-bottom: 12px;
      .collapse-icon {
        margin-right: 8px;
      }
    }

    .sys-management {
      display: flex;
      align-items: center;
      font-family: var(--font-sans);
      font-weight: 600;
      font-size: 17px;
      letter-spacing: -0.374px;
      color: var(--color-ink);
      cursor: pointer;
      margin-bottom: 12px;
      .collapse-icon {
        margin-right: 8px;
      }
    }

    .bottom {
      position: absolute;
      bottom: 20px;
      left: 16px;
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;
      width: calc(100% - 32px);
      .back-to_workspace {
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        height: 40px;
        cursor: pointer;

        &:not(.collapse) {
          background: var(--overlay-hover);
          border: 1px solid var(--color-hairline);
        }
        &:hover {
          background-color: var(--overlay-hover);
        }
        &:active {
          background-color: var(--overlay-pressed);
        }
        .ed-icon {
          margin-right: 4.95px;
        }
      }

      .personal-info {
        display: flex;
        align-items: center;
        margin-top: 16px;

        .fold {
          cursor: pointer;
          margin-left: auto;
          border-radius: 8px;
          width: 40px;
          height: 40px;
          &:hover,
          &:focus {
            background: var(--overlay-hover);
          }

          &:active {
            background: var(--overlay-strong);
          }
        }
      }
    }

    &.left-side-collapse {
      width: 64px;
      min-width: 64px;
      padding: 16px 12px;

      .ed-menu--collapse {
        --ed-menu-icon-width: 32px;
        width: 40px;
      }

      .bottom {
        left: 12px;
        width: calc(100% - 24px);
        .ed-icon {
          margin-right: 0;
        }
      }

      .personal-info {
        flex-wrap: wrap;

        .default-avatar {
          margin: 0 0 26px 4px;
        }

        .fold {
          margin: 0 auto;
        }
      }
    }
  }

  .right-main {
    width: calc(100% - 240px);
    padding: 8px 8px 8px 0;
    max-height: 100vh;

    &.right-side-collapse {
      width: calc(100% - 64px);
    }

    .content {
      width: 100%;
      height: 100%;
      padding: 16px 24px;
      background-color: var(--color-canvas);
      border: 1px solid var(--color-hairline);
      border-radius: 18px;
      box-shadow: none;
      overflow-x: auto;

      &:has(.no-padding) {
        padding: 0;
      }
    }
  }

  &.system-layout--chat {
    align-items: stretch;
  }

  .layout-column-resizer {
    width: 6px;
    flex-shrink: 0;
    cursor: col-resize;
    align-self: stretch;
    margin: 8px 0;
    border-radius: 4px;
    background: transparent;
    transition: background 0.15s;

    &:hover {
      background: var(--overlay-hover);
    }
  }

  .left-side--chat {
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: hidden;

    .left-side-nav-block {
      flex-shrink: 0;
      flex: 0 1 auto;
      max-height: 46%;
      min-height: 0;
      overflow-x: hidden;
      overflow-y: auto;
      position: relative;
      z-index: 5;
    }

    .layout-chat-history-shell {
      flex: 1;
      min-height: 0;
      min-width: 0;
      display: flex;
      flex-direction: column;
      padding-top: 4px;
      position: relative;
      z-index: 1;
    }

    .layout-chat-history-divider {
      flex-shrink: 0;
      height: 1px;
      margin: 0 12px;
      background: var(--color-hairline);
    }

    .layout-chat-history-heading {
      flex-shrink: 0;
      padding: 8px 16px 4px;
      font-size: 12px;
      font-weight: 600;
      line-height: 18px;
      color: var(--color-muted);
      letter-spacing: 0.02em;
    }

    .layout-chat-history {
      flex: 1;
      min-height: 0;
      min-width: 0;
      display: flex;
      flex-direction: column;

      & > * {
        flex: 1;
        min-height: 0;
        width: 100%;
      }
    }

    .bottom.bottom--flow {
      position: static !important;
      width: 100% !important;
      left: auto !important;
      bottom: auto !important;
      margin-top: auto;
      padding-top: 8px;
    }
  }

  .right-main--chat {
    flex: 1;
    width: auto !important;
    min-width: 0;
    min-height: 0;
  }
}
</style>
