<template>
  <div ref="appLoginView" class="appearance-login-view" :style="customStyle">
    <div class="top-tab-container">
      <div class="flex-top-tabs">
        <div class="tab-card">
          <span>{{ t('system.tab') }}</span>
          <el-icon size="10">
            <icon_close_outlined />
          </el-icon>
        </div>
        <div class="tab-card active">
          <div :title="pageName || 'SQLBot'" class="active-span">
            <img :src="pageWeb" alt="" />
            <span>{{ pageName || 'SQLBot' }}</span>
          </div>
          <el-icon size="10">
            <icon_close_outlined />
          </el-icon>
        </div>
        <div class="tab-card">
          <span>{{ t('system.tab') }}</span>
          <el-icon size="10">
            <icon_close_outlined />
          </el-icon>
        </div>
        <div class="tab-card">
          <span>{{ t('system.tab') }}</span>
          <el-icon size="10">
            <icon_close_outlined />
          </el-icon>
        </div>
      </div>
    </div>
    <div class="login-container">
      <div v-if="showLoginImage" class="left-img">
        <el-image class="login-image" :src="pageBg || login_image" />
      </div>
      <div class="right-container">
        <div class="login-form-center">
          <div class="config-area">
            <div class="login-logo">
              <div class="login-logo-icon">
                <img height="52" v-if="pageLogin" :src="pageLogin" alt="" />
                <el-icon size="52" v-else
                  ><custom_small v-if="themeColor !== 'default'"></custom_small>
                  <LOGO_fold v-else></LOGO_fold
                ></el-icon>
                <span
                  style="margin-left: 14px; font-size: 34px; font-weight: 900; color: #485559"
                  >{{ name }}</span
                >
              </div>
            </div>
            <div v-if="isBtnShow(showSlogan)" class="login-welcome">
              {{ pageSlogan ?? t('common.intelligent_questioning_platform') }}
            </div>
            <div v-else class="login-welcome"></div>
          </div>
          <div class="form-area">
            <div class="default-login-tabs">
              <el-form size="small">
                <el-form-item class="login-form-item" prop="username">
                  <el-input
                    readonly
                    :placeholder="
                      $t('datasource.please_enter') +
                      $t('common.empty') +
                      $t('common.your_account_email_address')
                    "
                    autofocus
                  />
                </el-form-item>
                <el-form-item prop="password">
                  <el-input
                    readonly
                    :placeholder="
                      $t('datasource.please_enter') +
                      $t('common.empty') +
                      $t('common.enter_your_password')
                    "
                    show-password
                    maxlength="30"
                    show-word-limit
                    type="password"
                    autocomplete="new-password"
                  />
                </el-form-item>
                <div class="login-btn">
                  <el-button type="primary" class="submit" size="small" :disabled="true">
                    {{ t('common.login_') }}
                  </el-button>
                </div>
              </el-form>
            </div>
          </div>
        </div>
        <div v-if="showFoot" class="dynamic-login-foot" v-html="pageFootContent" />
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import icon_close_outlined from '@/assets/svg/icon_close_outlined.svg'
import LOGO_fold from '@/assets/LOGO-fold.svg'
import login_image from '@/assets/embedded/login_image.png'
import logoHeader from '@/assets/blue/LOGO-head_blue.png'
import custom_small from '@/assets/svg/logo-custom_small.svg'
import loginImage from '@/assets/blue/login-image_blue.png'
import { propTypes } from '@/utils/propTypes'
import { sanitizeHtml } from '@/utils/xss'
import { isBtnShow } from '@/utils/utils'
import { useI18n } from 'vue-i18n'
import { computed, ref, onMounted, nextTick } from 'vue'
import elementResizeDetectorMaker from 'element-resize-detector'
const basePath = import.meta.env.VITE_API_BASE_URL
const baseUrl = basePath + '/system/appearance/picture/'

const { t } = useI18n()
const props = defineProps({
  web: propTypes.string.def(''),
  name: propTypes.string.def(''),
  slogan: propTypes.string.def(''),
  themeColor: propTypes.string.def(''),
  customColor: propTypes.string.def(''),
  login: propTypes.string.def(''),
  showSlogan: propTypes.string.def('0'),
  bg: propTypes.string.def(''),
  height: propTypes.number.def(425),
  foot: propTypes.string.def(''),
  footContent: propTypes.string.def(''),
  isBlue: propTypes.bool.def(false),
})
const appLoginView = ref()
const loginContainerWidth = ref(0)
const pageWeb = computed(() => {
  return !props.web
    ? props.isBlue
      ? logoHeader
      : '/LOGO-fold.svg'
    : props.web.startsWith('blob')
      ? props.web
      : baseUrl + props.web
})
const pageLogin = computed(() =>
  !props.login ? null : props.login.startsWith('blob') ? props.login : baseUrl + props.login
)
const pageBg = computed(() =>
  !props.bg
    ? props.isBlue
      ? loginImage
      : null
    : props.bg.startsWith('blob')
      ? props.bg
      : baseUrl + props.bg
)
const pageName = computed(() => props.name)
const pageSlogan = computed(() => props.slogan)
const showFoot = computed(() => props.foot && props.foot === 'true')
const pageFootContent = computed(() => {
  // Sanitize HTML content to prevent XSS attacks
  const content = props.foot && props.foot === 'true' ? props.footContent : null
  return content ? sanitizeHtml(content) : null
})
const customStyle = computed(() => {
  const result = { height: `${props.height + 23}px` } as {
    [key: string]: any
  }
  return result
})
const showLoginImage = computed<boolean>(() => {
  return !(loginContainerWidth.value < 555)
})
onMounted(() => {
  const erd = elementResizeDetectorMaker()
  erd.listenTo(appLoginView.value, () => {
    nextTick(() => {
      loginContainerWidth.value = appLoginView.value?.offsetWidth
    })
  })
})
</script>

<style lang="less" scoped>
.appearance-login-view {
  min-width: 390px;
  min-height: 314px;
  width: 100%;
  height: 464px;
  background-color: #fff;
  position: relative;
  border-radius: 6px;
  overflow: hidden;
  .top-tab-container {
    width: 100%;
    height: 22px;
    background-color: #eff0f1;
    .flex-top-tabs {
      display: flex;
      height: 23px;
      padding-top: 3px;
      align-items: center;
      .active {
        background-color: #fff;
        height: 20px !important;
        line-height: 20px !important;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
      }

      .tab-card + .tab-card:not(.active) {
        border-right: 1px solid #e0e0e2;
      }
      .tab-card {
        padding: 0 8px;
        display: flex;
        justify-content: space-between;
        width: 8%;
        min-width: 100px;
        height: 14px;
        line-height: 14px;
        font-size: 9px;
        align-items: center;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;

        .active-span {
          display: flex;
          align-items: center;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          img {
            width: 14px;
            height: 14px;
            margin-right: 4px;
          }
        }
      }
    }
  }

  .login-container {
    height: calc(100% - 22px);
    width: 100%;
    display: flex;
    .left-img {
      overflow: hidden;
      height: 100%;
      width: 40%;
      min-width: 240px;
      .login-image {
        background-size: 100% 100%;
        width: 100%;
        height: 100%;
      }
    }
    .right-container {
      position: relative;
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 290px;
      .login-form-center {
        width: 300px;
        font-size: 10px;
        .config-area {
          .login-logo {
            text-align: center;
            img {
              width: auto;
              max-height: 52px;
              @media only screen and (max-width: 1280px) {
                width: auto;
                max-height: 52px;
              }
            }
            .login-logo-icon {
              width: auto;
              height: 52px;
              display: flex;
              align-items: center;
              justify-content: center;
            }
          }
          .login-welcome {
            text-align: center;
            margin-top: 3px;
            color: #646a73;
            font-size: 12px;
            font-style: normal;
            font-weight: 400;
            line-height: 16px;
            word-wrap: break-word;
          }
        }
        .form-area {
          margin-top: 24px;
          padding: 24px;
          padding-top: 12px;
          box-shadow: 0px 4px 15px rgba(31, 35, 41, 0.08);
          border: 1px solid #dee0e3;
          border-radius: 12px;

          .login-form-item {
            margin-top: 15px;
          }

          .ed-form-item--default {
            margin-bottom: 15px;
          }
        }
      }
    }
  }
  .dynamic-login-foot {
    visibility: visible;
    width: 100%;
    position: absolute;
    z-index: 302;
    bottom: 0;
    left: 0;
    height: auto;
    padding-top: 1px;
    zoom: 1;
    margin: 0;
  }
}
.login-btn {
  :deep(button) {
    width: 100%;
  }
}
</style>
