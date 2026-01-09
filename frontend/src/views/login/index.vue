<template>
  <div
    v-if="showLoading"
    v-loading="true"
    :element-loading-text="t('qa.loading')"
    class="xpack-login-handler-mask"
    element-loading-background="#F5F6F7"
  ></div>

  <div class="login-container" :class="{ 'hide-login-container': showLoading }">
    <div class="login-left">
      <img :src="bg" alt="" />
    </div>
    <div class="login-content">
      <div class="login-right">
        <div class="login-logo-icon">
          <img v-if="loginBg" height="52" :src="loginBg" alt="" />
          <el-icon v-else size="52"
            ><custom_small v-if="appearanceStore.themeColor !== 'default'"></custom_small>
            <LOGO_fold v-else></LOGO_fold
          ></el-icon>
          <span style="margin-left: 14px; font-size: 34px; font-weight: 900; color: #485559">{{
            appearanceStore.name
          }}</span>
        </div>
        <div v-if="appearanceStore.getShowSlogan" class="welcome">
          {{ appearanceStore.slogan ?? $t('common.intelligent_questioning_platform') }}
        </div>
        <div v-else class="welcome" style="height: 0"></div>
        <div class="login-form">
          <div class="default-login-tabs">
            <h2 class="title">{{ $t('common.login') }}</h2>
            <el-form
              ref="loginFormRef"
              class="form-content_error"
              :model="loginForm"
              :rules="rules"
              @keyup.enter="submitForm"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="loginForm.username"
                  clearable
                  :placeholder="$t('common.your_account_email_address')"
                  size="large"
                ></el-input>
              </el-form-item>
              <el-form-item prop="password">
                <el-input
                  v-model="loginForm.password"
                  :placeholder="$t('common.enter_your_password')"
                  type="password"
                  show-password
                  clearable
                  size="large"
                ></el-input>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" class="login-btn" @click="submitForm">{{
                  $t('common.login_')
                }}</el-button>
              </el-form-item>
            </el-form>
          </div>
          <Handler
            ref="xpackLoginHandler"
            v-model:loading="showLoading"
            jsname="L2NvbXBvbmVudC9sb2dpbi9IYW5kbGVy"
            @switch-tab="switchTab"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useI18n } from 'vue-i18n'
import custom_small from '@/assets/svg/logo-custom_small.svg'
import LOGO_fold from '@/assets/LOGO-fold.svg'
import login_image from '@/assets/embedded/login_image.png'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import loginImage from '@/assets/blue/login-image_blue.png'
import Handler from './xpack/Handler.vue'
import { toLoginSuccess } from '@/utils/utils'

const showLoading = ref(true)
const router = useRouter()
const userStore = useUserStore()
const appearanceStore = useAppearanceStoreWithOut()
const { t } = useI18n()
const xpackLoginHandler = ref<any>(null)
const loginForm = ref({
  username: '',
  password: '',
})
const activeName = ref('simple')

// const isLdap = computed(() => activeName.value == 'ldap')
const bg = computed(() => {
  return appearanceStore.getBg || (appearanceStore.isBlue ? loginImage : login_image)
})

const loginBg = computed(() => {
  return appearanceStore.getLogin
})

const rules = {
  username: [{ required: true, message: t('common.your_account_email_address'), trigger: 'blur' }],
  password: [{ required: true, message: t('common.the_correct_password'), trigger: 'blur' }],
}

const loginFormRef = ref()

const submitForm = () => {
  loginFormRef.value.validate((valid: boolean) => {
    if (valid) {
      userStore.login(loginForm.value).then(() => {
        toLoginSuccess(router)
      })
    }
  })
}
const switchTab = (name: string) => {
  activeName.value = name || 'simple'
}
</script>

<style lang="less" scoped>
.login-container {
  height: 100vh;
  width: 100vw;
  background-color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;

  .login-left {
    display: flex;
    height: 100%;
    width: 40%;
    img {
      height: 100%;
      max-width: 100%;
    }
  }

  .login-content {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;

    .login-right {
      display: flex;
      align-items: center;
      flex-direction: column;
      position: relative;

      .login-logo-icon {
        width: auto;
        height: 52px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .welcome {
        margin: 8px 0 40px 0;
        font-weight: 400;
        font-size: 14px;
        line-height: 20px;
        color: #646a73;
      }

      .login-form {
        border: 1px solid #dee0e3;
        padding: 40px;
        width: 480px;
        min-height: 392px;
        border-radius: 12px;
        box-shadow: 0px 6px 24px 0px #1f232914;

        .form-content_error {
          .ed-form-item--default {
            margin-bottom: 24px;
            &.is-error {
              margin-bottom: 48px;
            }
          }
        }

        .title {
          font-weight: 500;
          font-style: Medium;
          font-size: 20px;
          line-height: 28px;
          margin-bottom: 24px;
        }

        .login-btn {
          width: 100%;
          height: 45px;
          font-size: 16px;
          border-radius: 4px;
        }

        .agreement {
          margin-top: 20px;
          text-align: center;
          color: #666;
        }
      }
    }
  }
}
.hide-login-container {
  display: none;
}
:deep(.ed-input__wrapper) {
  background-color: #f5f7fa;
}
.xpack-login-handler-mask {
  position: fixed;
  width: 100vw;
  height: 100vh;
  left: 0;
  top: 0;
  z-index: 999;
}
</style>
