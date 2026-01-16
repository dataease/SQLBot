<script lang="ts" setup>
import { ref, computed } from 'vue'
import Default_avatar_custom from '@/assets/img/Default-avatar.svg'
import icon_admin_outlined from '@/assets/svg/icon_admin_outlined.svg'
import icon_info_outlined_1 from '@/assets/svg/icon_info_outlined_1.svg'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import icon_maybe_outlined from '@/assets/svg/icon-maybe_outlined.svg'
import icon_key_outlined from '@/assets/svg/icon-key_outlined.svg'
import icon_api_key from '@/assets/svg/icon-api_key.svg'
import icon_translate_outlined from '@/assets/svg/icon_translate_outlined.svg'
import icon_logout_outlined from '@/assets/svg/icon_logout_outlined.svg'
import icon_right_outlined from '@/assets/svg/icon_right_outlined.svg'
import AboutDialog from '@/components/about/index.vue'
import icon_done_outlined from '@/assets/svg/icon_done_outlined.svg'
import { useI18n } from 'vue-i18n'
import PwdForm from './PwdForm.vue'
import Apikey from './Apikey.vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { userApi } from '@/api/auth'
import { toLoginPage } from '@/utils/utils'
import { useCache } from '@/utils/useCache'

const { wsCache } = useCache()
const router = useRouter()
const appearanceStore = useAppearanceStoreWithOut()
const userStore = useUserStore()
const pwdFormRef = ref()
const { t, locale } = useI18n()
defineProps({
  collapse: { type: [Boolean], required: true },
  inSysmenu: { type: [Boolean], required: true },
})

const name = computed(() => userStore.getName)
const account = computed(() => userStore.getAccount)
const currentLanguage = computed(() => userStore.getLanguage)
const isAdmin = computed(() => userStore.isAdmin)
const isLocalUser = computed(() => !userStore.getOrigin)

const isClient = computed(() => {
  return !!wsCache.get('sqlbot-platform-client')
})

const platFlag = computed(() => {
  const platformInfo = userStore.getPlatformInfo
  return platformInfo?.origin || 0
})
const dialogVisible = ref(false)
const apikeyDialogVisible = ref(false)
const aboutRef = ref()
const languageList = computed(() => [
  {
    name: 'English',
    value: 'en',
  },
  {
    name: '简体中文',
    value: 'zh-CN',
  },
  {
    name: '한국인',
    value: 'ko-KR',
  },
])
const popoverRef = ref()

const toSystem = () => {
  popoverRef.value.hide()
  router.push('/system')
}

const changeLanguage = (lang: string) => {
  locale.value = lang
  userStore.setLanguage(lang)
  const param = {
    language: lang,
  }
  userApi.language(param).then(() => {
    window.location.reload()
  })
}

const openHelp = () => {
  window.open(appearanceStore.getHelp || 'https://dataease.cn/sqlbot/', '_blank')
}

const openPwd = () => {
  dialogVisible.value = true
}
const closePwd = () => {
  dialogVisible.value = false
}
const openApikey = () => {
  apikeyDialogVisible.value = true
}
const toAbout = () => {
  aboutRef.value?.open()
}
const savePwdHandler = () => {
  pwdFormRef.value?.submit()
}
const logout = async () => {
  if (!(await userStore.logout())) {
    router.push(toLoginPage(router?.currentRoute?.value?.fullPath || ''))
    // router.push('/login')
  }
}
</script>

<template>
  <el-popover
    ref="popoverRef"
    trigger="click"
    popper-class="system-person"
    :placement="collapse ? 'right' : 'top-start'"
  >
    <template #reference>
      <button class="person" :title="name" :class="collapse && 'collapse'">
        <el-icon size="32">
          <Default_avatar_custom></Default_avatar_custom>
        </el-icon>
        <span v-if="!collapse" class="name ellipsis">{{ name }}</span>
      </button></template
    >
    <div class="popover">
      <div class="popover-content">
        <div class="info">
          <el-icon class="avatar-custom" size="40">
            <Default_avatar_custom></Default_avatar_custom>
          </el-icon>
          <div :title="name" class="top ellipsis">{{ name }}</div>
          <div :title="account" class="bottom ellipsis">{{ account }}</div>
        </div>
        <div v-if="isAdmin && !inSysmenu" class="popover-item" @click="toSystem">
          <el-icon style="color: #646a73" size="16">
            <icon_admin_outlined></icon_admin_outlined>
          </el-icon>
          <div class="datasource-name">{{ $t('common.system_manage') }}</div>
        </div>
        <div v-if="isLocalUser && !platFlag" class="popover-item" @click="openPwd">
          <el-icon size="16">
            <icon_key_outlined></icon_key_outlined>
          </el-icon>
          <div class="datasource-name">{{ $t('user.change_password') }}</div>
        </div>
        <div class="popover-item" @click="openApikey">
          <el-icon size="16">
            <icon_api_key></icon_api_key>
          </el-icon>
          <div class="datasource-name">API Key</div>
        </div>
        <el-popover :teleported="false" popper-class="system-language" placement="right">
          <template #reference>
            <div class="popover-item">
              <el-icon size="16">
                <icon_translate_outlined></icon_translate_outlined>
              </el-icon>
              <div class="datasource-name">{{ $t('common.language') }}</div>
              <el-icon class="right" size="16">
                <icon_right_outlined></icon_right_outlined>
              </el-icon>
            </div>
          </template>
          <div class="language-popover">
            <div
              v-for="ele in languageList"
              :key="ele.name"
              class="popover-item_language"
              :class="currentLanguage === ele.value && 'isActive'"
              @click="changeLanguage(ele.value)"
            >
              <div class="language-name">{{ ele.name }}</div>
              <el-icon size="16" class="done">
                <icon_done_outlined></icon_done_outlined>
              </el-icon>
            </div>
          </div>
        </el-popover>
        <div v-if="appearanceStore.getShowAbout" class="popover-item" @click="toAbout">
          <el-icon size="16">
            <icon_info_outlined_1></icon_info_outlined_1>
          </el-icon>
          <div class="datasource-name">{{ $t('about.title') }}</div>
        </div>
        <div v-if="appearanceStore.getShowDoc" class="popover-item" @click="openHelp">
          <el-icon size="16">
            <icon_maybe_outlined></icon_maybe_outlined>
          </el-icon>
          <div class="datasource-name">{{ $t('common.help') }}</div>
        </div>
        <div style="height: 4px; width: 100%"></div>
        <div v-if="!isClient" class="popover-item mr4" @click="logout">
          <el-icon size="16">
            <icon_logout_outlined></icon_logout_outlined>
          </el-icon>
          <div class="datasource-name">{{ $t('common.logout') }}</div>
        </div>
      </div>
    </div>
  </el-popover>

  <el-dialog v-model="dialogVisible" :title="t('user.upgrade_pwd.title')" width="600">
    <pwd-form v-if="dialogVisible" ref="pwdFormRef" @pwd-saved="closePwd" />
    <template #footer>
      <div class="dialog-footer">
        <el-button secondary @click="closePwd">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="savePwdHandler">{{ t('common.save') }}</el-button>
      </div>
    </template>
  </el-dialog>
  <el-dialog v-model="apikeyDialogVisible" title="API Key" width="840">
    <apikey v-if="apikeyDialogVisible" ref="apikeyRef" />
  </el-dialog>
  <AboutDialog ref="aboutRef" />
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

  &.collapse {
    min-width: 48px;
    margin-left: -4px;
    position: relative;
    margin-top: -6px;
    margin-bottom: 16px;

    .default-avatar {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
    }
  }

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
  }

  &:hover,
  &:focus {
    &::after {
      background: #1f23291a;
    }
  }

  &:active {
    &::after {
      background: #1f232926;
    }
  }
}
</style>

<style lang="less">
.system-person.system-person {
  padding: 0;
  width: 200px !important;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border: 1px solid #dee0e3;
  position: relative;
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
      margin-bottom: 4px;

      .avatar-custom {
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
      padding-left: 8px;
      padding-right: 4px;
      position: relative;
      cursor: pointer;
      margin: 0 4px;
      border-radius: 4px;
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
