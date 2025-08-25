<script lang="ts" setup>
import { computed } from 'vue'
import Default_avatar from '@/assets/workspace/default_avatar.png'
import icon_admin_outlined from '@/assets/svg/icon_admin_outlined.svg'
import icon_info_outlined_1 from '@/assets/svg/icon_info_outlined_1.svg'
import icon_maybe_outlined from '@/assets/svg/icon-maybe_outlined.svg'
import icon_key_outlined from '@/assets/svg/icon-key_outlined.svg'
import icon_translate_outlined from '@/assets/svg/icon_translate_outlined.svg'
import icon_logout_outlined from '@/assets/svg/icon_logout_outlined.svg'
import icon_right_outlined from '@/assets/svg/icon_right_outlined.svg'
import { useUserStore } from '@/stores/user'
import DefaultAvatarBlue from '@/assets/blue/Default-avatar_blue.png'

defineProps({
  showDoc: { type: [Boolean], required: true },
  showAbout: { type: [Boolean], required: true },
  isBlue: { type: [Boolean], required: true },
})
const userStore = useUserStore()
const name = computed(() => userStore.getName)
const account = computed(() => userStore.getAccount)
</script>

<template>
  <div style="position: relative">
    <button class="person" :title="name">
      <img
        class="default-avatar"
        :src="isBlue ? DefaultAvatarBlue : Default_avatar"
        width="32px"
        height="32px"
      />
      <span class="name ellipsis">{{ name }}</span>
    </button>
    <div class="ed-popper is-light ed-popover system-person_style">
      <div class="popover">
        <div class="popover-content">
          <div class="info">
            <img :src="isBlue ? DefaultAvatarBlue : Default_avatar" width="40px" height="40px" />
            <div :title="name" class="top ellipsis">{{ name }}</div>
            <div :title="account" class="bottom ellipsis">{{ account }}</div>
          </div>
          <div class="popover-item">
            <el-icon style="color: #646a73" size="16">
              <icon_admin_outlined></icon_admin_outlined>
            </el-icon>
            <div class="datasource-name">{{ $t('common.system_manage') }}</div>
          </div>
          <div class="popover-item">
            <el-icon size="16">
              <icon_key_outlined></icon_key_outlined>
            </el-icon>
            <div class="datasource-name">{{ $t('user.change_password') }}</div>
          </div>
          <div class="popover-item">
            <el-icon size="16">
              <icon_translate_outlined></icon_translate_outlined>
            </el-icon>
            <div class="datasource-name">{{ $t('common.language') }}</div>
            <el-icon class="right" size="16">
              <icon_right_outlined></icon_right_outlined>
            </el-icon>
          </div>
          <div v-if="showAbout" class="popover-item">
            <el-icon size="16">
              <icon_info_outlined_1></icon_info_outlined_1>
            </el-icon>
            <div class="datasource-name">{{ $t('about.title') }}</div>
          </div>
          <div v-if="showDoc" class="popover-item">
            <el-icon size="16">
              <icon_maybe_outlined></icon_maybe_outlined>
            </el-icon>
            <div class="datasource-name">{{ $t('common.help') }}</div>
          </div>
          <div class="popover-item mr4">
            <el-icon size="16">
              <icon_logout_outlined></icon_logout_outlined>
            </el-icon>
            <div class="datasource-name">{{ $t('common.logout') }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.person {
  padding: 0 8px;
  display: flex;
  align-items: center;
  cursor: pointer;
  width: 156px;
  height: 40px;
  border: none;
  background-color: transparent;
  position: relative;
  pointer-events: none;

  .name {
    font-weight: 400;
    font-size: 14px;
    line-height: 22px;
    margin-left: 8px;
    max-width: 85px;
  }

  &::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 100%;
    height: 100%;
    border-radius: 6px;
    background: #1f23291a;
  }
}
</style>

<style lang="less">
.system-person_style.system-person_style {
  padding: 0;
  width: 200px !important;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border: 1px solid #dee0e3;
  position: absolute;
  bottom: 44px;
  pointer-events: none;
  border-radius: 6px;

  &::after {
    content: '';
    position: absolute;
    bottom: 40px;
    left: 0;
    height: 1px;
    width: 100%;
    background: #dee0e3;
  }

  &::before {
    content: '';
    position: absolute;
    top: 62px;
    left: 0;
    height: 1px;
    width: 100%;
    background: #dee0e3;
  }

  .popover {
    .info {
      height: 62px;
      padding: 8px;

      img {
        float: left;
        margin: 3px 8px 0 7px;
      }

      .top {
        float: left;
        font-weight: 500;
        font-size: 16px;
        line-height: 24px;
        width: calc(100% - 60px);
      }

      .bottom {
        float: left;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        width: calc(100% - 60px);
      }
    }
    .popover-item {
      height: 32px;
      display: flex;
      align-items: center;
      padding-left: 12px;
      padding-right: 8px;
      position: relative;
      cursor: pointer;
      &:hover {
        background-color: #1f23291a;
      }
      &:active {
        background-color: #1f232926;
      }
      .datasource-name {
        margin-left: 8px;
      }

      &.mr4 {
        margin: 4px;
      }

      .right {
        margin-left: auto;
      }
    }
  }
}

.system-language.system-language {
  padding: 4px 4px 2px 4px;
  width: 240px !important;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border: 1px solid #dee0e3;

  .language-popover {
    .popover-item_language {
      height: 32px;
      display: flex;
      align-items: center;
      padding-left: 8px;
      padding-right: 8px;
      margin-bottom: 2px;
      position: relative;
      border-radius: 4px;
      cursor: pointer;
      &:not(.empty):hover {
        background: #1f23291a;
      }

      .language-name {
        margin-left: 8px;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        margin-bottom: 2px;
      }

      .done {
        margin-left: auto;
        display: none;
      }

      &.isActive {
        color: var(--ed-color-primary);

        .done {
          display: block;
        }
      }
    }
  }
}
</style>
