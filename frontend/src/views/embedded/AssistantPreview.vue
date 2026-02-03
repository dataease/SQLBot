<script lang="ts" setup>
import { computed } from 'vue'
import icon_sidebar_outlined from '@/assets/embedded/icon_sidebar_outlined_nofill.svg'
import icon_new_chat_outlined from '@/assets/svg/icon_new_chat_outlined.svg'
import LOGO from '@/assets/svg/logo-custom_small.svg'
import icon_close_outlined from '@/assets/svg/icon_close_outlined.svg'
import icon_magnify_outlined from '@/assets/svg/icon_magnify_outlined.svg'
import { propTypes } from '@/utils/propTypes'

const props = defineProps({
  welcomeDesc: propTypes.string.def(''),
  logo: propTypes.string.def(''),
  welcome: propTypes.string.def(''),
  name: propTypes.string.def(''),
})
const basePath = import.meta.env.VITE_API_BASE_URL
const baseUrl = basePath + '/system/assistant/picture/'

const pageLogo = computed(() => {
  return props.logo.startsWith('blob') ? props.logo : baseUrl + props.logo
})
</script>

<template>
  <div class="assistant-window">
    <div class="header">
      <el-icon size="20">
        <icon_sidebar_outlined></icon_sidebar_outlined>
      </el-icon>
      <el-icon v-if="!props.logo" class="logo" size="30">
        <LOGO></LOGO>
      </el-icon>
      <img v-else :src="pageLogo" class="logo" width="30px" height="30px" alt="" />
      <span :title="name" class="title ellipsis">{{ name }}</span>

      <el-tooltip effect="dark" :content="$t('embedded.new_conversation')" placement="top">
        <el-icon class="new-chat" size="20">
          <icon_new_chat_outlined></icon_new_chat_outlined>
        </el-icon>
      </el-tooltip>

      <el-icon class="new-chat" style="right: 52px" size="20">
        <icon_magnify_outlined></icon_magnify_outlined>
      </el-icon>

      <el-icon class="new-chat" style="right: 16px" size="20">
        <icon_close_outlined></icon_close_outlined>
      </el-icon>
    </div>
    <div class="center">
      <el-icon v-if="!props.logo" class="logo" size="30">
        <LOGO></LOGO>
      </el-icon>
      <img v-else :src="pageLogo" class="logo" width="30px" height="30px" alt="" />
      <div class="i-am">{{ welcome }}</div>
      <div class="i-can">{{ welcomeDesc }}</div>
    </div>
    <div class="content">
      <el-button size="large" type="primary" class="greeting-btn">
        <span class="inner-icon">
          <el-icon>
            <icon_new_chat_outlined />
          </el-icon>
        </span>
        {{ $t('qa.start_sqlbot') }}
      </el-button>
    </div>

    <div class="drawer-assistant"></div>
  </div>
</template>

<style lang="less" scoped>
.assistant-window {
  width: 460px;
  height: 100%;
  border-radius: 12px;
  border: 1px solid #dee0e3;
  box-shadow: 0px 6px 24px 0px #1f232914;
  background-color: #fff;
  position: relative;
  overflow: hidden;
  .header {
    background: var(--ed-color-primary-1a, #1cba901a);
    height: 56px;
    padding: 0 16px;
    display: flex;
    align-items: center;
    position: relative;
    color: var(--ed-text-color-primary);
    .logo {
      margin: 0 8px 0 16px;
    }

    .title {
      font-weight: 500;
      font-size: 16px;
      line-height: 24px;
      color: var(--ed-text-color-primary);
      width: 242px;
    }

    .ed-icon:not(.logo) {
      cursor: pointer;

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

    .new-chat {
      position: absolute;
      right: 88px;
      top: 17px;
    }
  }
  .center {
    width: 100%;
    display: flex;
    align-items: center;
    flex-direction: column;
    margin-top: 180px;

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
  .content {
    width: calc(100% - 32px);
    margin-top: 8px;
    margin-left: 16px;

    .greeting-btn {
      width: 100%;
      height: 88px;
      border-radius: 16px;
      border-style: dashed;

      .inner-icon {
        display: flex;
        flex-direction: row;
        align-items: center;

        margin-right: 6px;
      }

      font-size: 16px;
      line-height: 24px;
      font-weight: 500;

      --ed-button-text-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
      --ed-button-hover-text-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
      --ed-button-active-text-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
      --ed-button-bg-color: rgba(248, 249, 250, 1);
      --ed-button-hover-bg-color: var(--ed-color-primary-1a, #1cba901a);
      --ed-button-border-color: rgba(217, 220, 223, 1);
      --ed-button-hover-border-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
      --ed-button-active-bg-color: var(--ed-color-primary-33, #1cba9033);
      --ed-button-active-border-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
    }
  }

  .drawer-assistant {
    height: 100%;
    position: absolute;
    left: 0;
    top: 0;
    width: 50%;
    background: #f5f6f7;
    box-shadow: 0px 6px 24px 0px #1f232914;
    padding: 16px;
    border-right: 1px solid #dee0e3;
    display: none;
  }
}
</style>
