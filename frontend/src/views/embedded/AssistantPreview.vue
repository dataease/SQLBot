<script lang="ts" setup>
import { ref, computed } from 'vue'
import icon_sidebar_outlined from '@/assets/embedded/icon_sidebar_outlined_nofill.svg'
import icon_new_chat_outlined from '@/assets/svg/icon_new_chat_outlined.svg'
import LOGO from '@/assets/embedded/LOGO.png'
import disable_answer from '@/assets/embedded/disable.png'
import icon_close_outlined from '@/assets/svg/icon_close_outlined.svg'
import icon_magnify_outlined from '@/assets/svg/icon_magnify_outlined.svg'
import { propTypes } from '@/utils/propTypes'

const props = defineProps({
  welcomeDesc: propTypes.string.def(''),
  logo: propTypes.string.def(''),
  welcome: propTypes.string.def(''),
  name: propTypes.string.def(''),
})
const textareaVal = ref('')
const basePath = import.meta.env.VITE_API_BASE_URL
const baseUrl = basePath + '/system/assistant/picture/'

const pageLogo = computed(() => {
  return !props.logo ? LOGO : props.logo.startsWith('blob') ? props.logo : baseUrl + props.logo
})
</script>

<template>
  <div class="assistant-window">
    <div class="header">
      <el-icon size="20">
        <icon_sidebar_outlined></icon_sidebar_outlined>
      </el-icon>
      <img :src="pageLogo" class="logo" width="30px" height="30px" alt="" />
      <span class="title">{{ name }}</span>

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
      <img :src="pageLogo" class="logo" width="30px" height="30px" alt="" />
      <div class="i-am">{{ welcome }}</div>
      <div class="i-can">{{ welcomeDesc }}</div>
    </div>
    <div class="content">
      <div class="textarea-send">
        <el-input
          v-model="textareaVal"
          :autosize="{ minRows: 1, maxRows: 8.5848 }"
          type="textarea"
          clearable
          :placeholder="$t('embedded.enter_a_question')"
        />
        <el-tooltip :offset="10" effect="dark" :content="$t('embedded.send')" placement="top">
          <img :src="disable_answer" width="32px" height="32px" alt="" />
        </el-tooltip>

        <!-- <el-tooltip
          :offset="10"
          effect="dark"
          :content="$t('embedded.stop_replying')"
          placement="top"
        >
          <img :src="answer" width="32px" height="32px" alt="" />
        </el-tooltip>

        <img :src="loading_answer" width="32px" height="32px" alt="" />
        <img :src="send_answer" width="32px" height="32px" alt="" /> -->
      </div>
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
    }

    .ed-icon {
      position: relative;
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
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    display: flex;
    align-items: center;
    flex-direction: column;

    .i-am {
      font-weight: 600;
      font-size: 24px;
      line-height: 32px;
      margin: 16px 0;
    }

    .i-can {
      margin-bottom: 4px;
      max-width: 350px;
      text-align: center;
      font-weight: 400;
      font-size: 14px;
      line-height: 24px;
      color: #646a73;
    }
  }
  .content {
    width: calc(100% - 32px);

    .textarea-send {
      width: 100%;
      position: relative;
      .ed-textarea {
        width: 100%;
      }

      :deep(.ed-textarea__inner) {
        padding: 12px 12px 52px 12px;
        font-weight: 400;
        font-size: 16px;
        line-height: 24px;
        border-radius: 16px;

        &::placeholder {
          color: #8f959e;
        }
      }

      img {
        cursor: pointer;
        position: absolute;
        right: 12px;
        bottom: 12px;
      }
    }

    position: absolute;
    bottom: 16px;
    left: 16px;
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
