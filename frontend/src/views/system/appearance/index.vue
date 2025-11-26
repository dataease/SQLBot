<template>
  <div class="appearance no-padding">
    <el-scrollbar>
      <div class="scroll-content">
        <p class="router-title">{{ t('system.appearance_settings') }}</p>
        <div class="appearance-table__content">
          <div class="theme">
            <div class="show-theme">{{ $t('system.platform_display_theme') }}</div>
            <div class="theme-color">
              <div class="btn-select">
                <el-button
                  :class="[themeColor === 'default' && 'is-active']"
                  text
                  @click="themeColorChange('default')"
                >
                  {{ $t('system.default_turquoise') }}
                </el-button>
                <el-button
                  :class="[themeColor === 'blue' && 'is-active']"
                  text
                  @click="themeColorChange('blue')"
                >
                  {{ $t('system.tech_blue') }}
                </el-button>
                <el-button
                  :class="[themeColor === 'custom' && 'is-active']"
                  text
                  @click="themeColorChange('custom')"
                >
                  {{ $t('system.custom') }}
                </el-button>
              </div>
            </div>

            <template v-if="themeColor === 'custom'">
              <div class="theme-bg">{{ t('system.customize_theme_color') }}</div>
              <el-color-picker
                v-model="customColor"
                :trigger-width="28"
                :predefine="COLOR_PANEL"
                is-custom
                effect="light"
                @change="customColorChange"
              />
            </template>
          </div>
          <div class="login" :class="themeColor">
            <div class="platform-login">
              {{ t('system.platform_login_settings') }}
            </div>
            <div class="page-preview">
              <div class="title">
                <span class="left">{{ t('system.page_preview') }}</span>
                <el-button text @click="resetLoginForm(true)">{{
                  t('system.restore_default')
                }}</el-button>
              </div>
              <div class="page-setting">
                <div class="page-content">
                  <!-- <img :src="loginPreview" alt="" /> -->
                  <login-preview
                    :navigate-bg="navigateBg"
                    :theme-color="themeColor"
                    :custom-color="customColor"
                    :name="loginForm.name"
                    :slogan="loginForm.slogan"
                    :web="web"
                    :show-slogan="loginForm.showSlogan"
                    :bg="bg"
                    :login="login"
                    :is-blue="isBlue"
                    :height="navigateHeight"
                    :foot="loginForm.foot"
                    :foot-content="loginForm.footContent"
                  />
                  <div class="tips-page">
                    {{
                      t('system.screen_customization_supported', {
                        msg: loginForm.name || 'SQLBot',
                      })
                    }}
                  </div>
                </div>
                <div class="config-list">
                  <div v-for="ele in configList" :key="ele.type" class="config-item">
                    <div class="config-logo">
                      <span class="logo">{{ ele.logo }}</span>
                      <el-upload
                        :name="ele.type"
                        :show-file-list="false"
                        class="upload-demo"
                        accept=".jpeg,.jpg,.png,.gif,.svg"
                        :before-upload="(e: any) => beforeUpload(e, ele)"
                        :http-request="uploadImg"
                      >
                        <el-button secondary>{{ t('system.replace_image') }}</el-button>
                      </el-upload>
                    </div>
                    <div class="tips">{{ ele.tips }}</div>
                  </div>
                  <el-form
                    ref="loginFormRef"
                    :model="loginForm"
                    label-position="top"
                    :rules="rules"
                    require-asterisk-position="right"
                    label-width="120px"
                    class="page-Form form-content_error_a"
                  >
                    <el-form-item :label="t('system.website_name')" prop="name">
                      <el-input
                        v-model="loginForm.name"
                        :placeholder="
                          $t('datasource.please_enter') +
                          $t('common.empty') +
                          $t('system.website_name')
                        "
                        maxlength="20"
                      />
                      <div class="form-tips">{{ t('system.on_webpage_tabs') }}</div>
                    </el-form-item>
                    <el-form-item>
                      <template #label>
                        <el-checkbox
                          v-model="loginForm.showSlogan"
                          true-value="0"
                          false-value="1"
                          :label="$t('system.welcome_message')"
                        />
                      </template>
                      <el-input v-model="loginForm.slogan" maxlength="50" />
                    </el-form-item>
                    <!-- <el-form-item :label="t('system.footer')" prop="foot">
                  <el-switch v-model="loginForm.foot" active-value="true" inactive-value="false" />
                </el-form-item>
                <el-form-item
                  v-if="loginForm.foot === 'true'"
                  :label="t('system.footer_content')"
                  prop="footContent"
                >
                  <tinymce-editor
                    v-if="loginForm.foot === 'true'"
                    v-model="loginForm.footContent"
                  />
                </el-form-item> -->
                  </el-form>
                </div>
              </div>
            </div>
          </div>
          <div class="login">
            <div class="platform-login">{{ t('system.platform_settings') }}</div>
            <div class="page-preview">
              <div class="title">
                <span class="left">{{ t('system.page_preview') }}</span>
                <el-button text @click="resetTopForm(true)">{{
                  t('system.restore_default')
                }}</el-button>
              </div>
              <div class="page-setting">
                <div class="page-content">
                  <!-- <div class="navigate-preview" :style="{'height': `${navigateHeight}px`}"> -->
                  <div class="navigate-preview" style="height: 425px">
                    <div class="navigate-head">
                      <div class="header-sql">
                        <img height="30" width="30" v-if="pageLogin" :src="pageLogin" alt="" />
                        <custom_small v-else-if="themeColor !== 'default'" class="logo" />
                        <logo v-else></logo>
                        <span style="margin-left: 8px">{{ loginForm.name }}</span>
                      </div>
                      <div class="bottom-sql">
                        <Person
                          :is-blue="isBlue"
                          :show-about="topForm.showAbout === '0'"
                          :show-doc="topForm.showDoc === '0'"
                        ></Person>
                        <el-icon size="20" class="fold">
                          <icon_side_fold_outlined></icon_side_fold_outlined>
                        </el-icon>
                      </div>
                    </div>
                    <div class="welcome-content">
                      <div class="greeting">
                        <img v-if="pageLogin" height="32" width="32" :src="pageLogin" alt="" />
                        <el-icon v-else size="32"
                          ><custom_small v-if="themeColor !== 'default'"></custom_small>
                          <LOGO_fold v-else></LOGO_fold
                        ></el-icon>
                        {{ topForm.pc_welcome }}
                      </div>
                      <div class="sub">
                        {{ topForm.pc_welcome_desc }}
                      </div>
                      <el-button size="large" type="primary" class="greeting-btn">
                        <span class="inner-icon">
                          <el-icon>
                            <icon_new_chat_outlined />
                          </el-icon>
                        </span>
                        {{ t('qa.start_sqlbot') }}
                      </el-button>
                    </div>
                  </div>
                  <div class="tips-page">
                    {{
                      t('system.screen_customization_settings', {
                        msg: loginForm.name || 'SQLBot',
                      })
                    }}
                  </div>
                </div>
                <div class="config-list">
                  <el-checkbox
                    v-model="topForm.showDoc"
                    true-value="0"
                    false-value="1"
                    :label="$t('system.help_documentation')"
                  />
                  <div class="doc-input">
                    <el-input
                      v-model="topForm.help"
                      style="width: 100%"
                      :placeholder="
                        $t('datasource.please_enter') +
                        $t('common.empty') +
                        $t('system.help_documentation')
                      "
                    />
                  </div>
                  <el-checkbox
                    v-model="topForm.showAbout"
                    true-value="0"
                    false-value="1"
                    :label="$t('system.show_about')"
                  />
                  <div style="margin-top: 8px" class="label">
                    {{ $t('system.welcome_message') }}
                  </div>
                  <div style="margin: 8px 0">
                    <el-input
                      v-model="topForm.pc_welcome"
                      :placeholder="
                        $t('datasource.please_enter') +
                        $t('common.empty') +
                        $t('system.welcome_message')
                      "
                      maxlength="50"
                    />
                  </div>
                  <div class="label">
                    {{ $t('embedded.welcome_description') }}
                  </div>
                  <div style="margin: 8px 0">
                    <el-input
                      v-model="topForm.pc_welcome_desc"
                      :placeholder="
                        $t('datasource.please_enter') +
                        $t('common.empty') +
                        $t('embedded.welcome_description')
                      "
                      type="textarea"
                      show-word-limit
                      maxlength="50"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-scrollbar>
    <div class="appearance-foot">
      <el-button secondary @click="giveUp">{{ $t('system.abort_update') }}</el-button>
      <el-button v-if="showSaveButton" type="primary" @click="saveHandler">{{
        $t('system.save_and_apply')
      }}</el-button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import logo from '@/assets/LOGO-fold.svg'
import LOGO_fold from '@/assets/LOGO-fold.svg'
import custom_small from '@/assets/svg/logo-custom_small.svg'
import { ref, unref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import {
  type FormInstance,
  type FormRules,
  type UploadUserFile,
  ElMessage,
} from 'element-plus-secondary'
import { useI18n } from 'vue-i18n'
import { request } from '@/utils/request'
import icon_side_fold_outlined from '@/assets/svg/icon_side-fold_outlined.svg'
import icon_new_chat_outlined from '@/assets/svg/icon_new_chat_outlined.svg'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import LoginPreview from './LoginPreview.vue'
import Person from './Person.vue'
import { setCurrentColor } from '@/utils/utils'

// import TinymceEditor from '@/components/rich-text/TinymceEditor.vue'
import { cloneDeep } from 'lodash-es'
const appearanceStore = useAppearanceStoreWithOut()
const { t } = useI18n()
interface LoginForm {
  name: string
  slogan: string
  foot: string
  showSlogan: string
  footContent?: string
}
interface ConfigItem {
  pkey: string
  pval: string
  ptype: string
  sort: number
}
const COLOR_PANEL = [
  '#FF4500',
  '#FF8C00',
  '#FFD700',
  '#71AE46',
  '#00CED1',
  '#1E90FF',
  '#C71585',
  '#999999',
  '#000000',
  '#FFFFFF',
]
const basePath = import.meta.env.VITE_API_BASE_URL
const baseUrl = basePath + '/system/appearance/picture/'
const fileList = ref<(UploadUserFile & { flag: string })[]>([])
const navigateBg = ref('dark')
const themeColor = ref('default')
const customColor = ref('#1CBA90')
const web = ref('')
const bg = ref('')
const login = ref('')
const navigate = ref('')
const mobileLogin = ref('')
const mobileLoginBg = ref('')
const navigateHeight = ref(400)

const changedItemArray = ref<ConfigItem[]>([])

const loginFormRef = ref<FormInstance>()
const defaultLoginForm = reactive<LoginForm>({
  name: 'SQLBot',
  slogan: t('common.intelligent_questioning_platform'),
  foot: 'false',
  showSlogan: '0',
  footContent: '',
})
const loginForm = reactive<LoginForm>(cloneDeep(defaultLoginForm))
const pageLogin = computed(() =>
  !login.value ? null : login.value.startsWith('blob') ? login.value : baseUrl + login.value
)
const rules = reactive<FormRules>({
  name: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('system.website_name'),
      trigger: 'blur',
    },
  ],
  foot: [
    {
      required: true,
      message: '',
      trigger: 'change',
    },
  ],
})

const defaultTopForm = {
  help: 'https://dataease.cn/sqlbot/v1/',
  showDoc: '0',
  showAbout: '0',
  pc_welcome: '你好，我是 SQLBot ',
  pc_welcome_desc: `我可以查询数据、生成图表、检测数据异常、预测数据等赶快开启智能问数吧～`,
}

const topForm = reactive<{
  help: string
  showDoc: string
  showAbout: string
  pc_welcome: string
  pc_welcome_desc: string
}>(cloneDeep(defaultTopForm))

const isBlue = computed(() => {
  return themeColor.value === 'blue'
})
const configList = [
  {
    logo: t('system.website_logo'),
    type: 'web',
    tips: t('system.larger_than_200kb'),
    size: 200 * 1024,
  },
  {
    logo: t('system.login_logo'),
    type: 'login',
    tips: t('system.larger_than_200kb_de'),
    size: 200 * 1024,
  },
  {
    logo: t('system.login_background_image'),
    type: 'bg',
    tips: t('system.larger_than_5mb'),
    size: 1024 * 1024 * 5,
  },
]

const giveUp = () => {
  resetLoginForm(false)
  resetTopForm(false)
  resetMobileForm(false)
  init()
}
const showSaveButton = ref(true)
const saveHandler = () => {
  loginFormRef.value?.validate((valLogin) => {
    if (valLogin) {
      const param = buildParam()
      const url = '/system/appearance'
      request
        .post(url, param, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })
        .then((res) => {
          if (!res) {
            ElMessage.success(t('system.setting_successfully'))
            appearanceStore.setLoaded(false)
            appearanceStore.setAppearance()
            showSaveButton.value = false
            nextTick(() => {
              showSaveButton.value = true
            })
          }
        })
    }
  })
}
const buildParam = () => {
  for (const key in loginForm) {
    const item = loginForm[key as keyof typeof loginForm]
    if (key === 'footContent') {
      addChangeArray(key, item!, 'file')
    } else {
      addChangeArray(key, item!)
    }
  }
  for (const key in topForm) {
    const item = topForm[key as keyof typeof topForm]
    addChangeArray(key, item)
  }
  const formData = new FormData()
  if (fileList.value.length) {
    fileList.value.forEach((file: any) => {
      const name = file.name + ',' + file['flag']
      const fileArray = [file]
      const newfile = new File(fileArray, name, { type: file['type'] })
      formData.append('files', newfile)
    })
  }
  formData.append('data', JSON.stringify(unref(changedItemArray)))
  return formData
}
const init = () => {
  const url = '/system/appearance/ui'
  changedItemArray.value = []
  fileList.value = []
  request
    .get(url)
    .then((res) => {
      const list = res || []
      if (!list.length) {
        return
      }
      list.forEach((item: any) => {
        const pkey = item.pkey
        const pval = item.pval
        if (pkey === 'navigateBg') {
          navigateBg.value = pval
        } else if (pkey === 'themeColor') {
          themeColor.value = pval
        } else if (pkey === 'customColor') {
          customColor.value = pval
        } else if (pkey === 'web') {
          web.value = pval
        } else if (pkey === 'login') {
          login.value = pval
        } else if (pkey === 'bg') {
          bg.value = pval
        } else if (pkey === 'navigate') {
          navigate.value = pval
        } else if (Object.prototype.hasOwnProperty.call(loginForm, pkey)) {
          loginForm[pkey as keyof typeof loginForm] = pval
        } else if (Object.prototype.hasOwnProperty.call(topForm, pkey)) {
          topForm[pkey as keyof typeof topForm] = pval
        } else if (pkey === 'mobileLogin') {
          mobileLogin.value = pval
        } else if (pkey === 'mobileLoginBg') {
          mobileLoginBg.value = pval
        }
      })
    })
    .finally(() => {
      nextTick(() => {
        if (themeColor.value === 'custom') {
          setPageCustomColor(customColor.value)
        } else {
          setPageCustomColor(isBlue.value ? '#3370FF' : '#1CBA90')
        }
      })
    })
}
const addChangeArray = (key: string, val: string, type?: string) => {
  let len = changedItemArray.value.length
  let match = false
  while (len--) {
    const item = changedItemArray.value[len]
    if (item['pkey'] === key) {
      changedItemArray.value[len] = {
        pkey: key,
        pval: val,
        ptype: type || 'str',
        sort: 1,
      }
      match = true
    }
  }
  if (!match) {
    changedItemArray.value.push({
      pkey: key,
      pval: val,
      ptype: type || 'str',
      sort: 1,
    })
  }
}

const themeColorChange = (val: any) => {
  themeColor.value = val
  addChangeArray('themeColor', val)
  if (themeColor.value === 'custom') {
    setPageCustomColor(customColor.value)
  } else {
    setPageCustomColor(isBlue.value ? '#3370FF' : '#1CBA90')
  }
}
const customColorChange = (val: any) => {
  addChangeArray('customColor', val)
  setPageCustomColor(val)
}
const setPageCustomColor = (val: any) => {
  const ele = document.getElementsByClassName('appearance-table__content')[0] as HTMLElement
  setCurrentColor(val, ele)
}
const resetLoginForm = (reset2Default?: boolean) => {
  for (const key in loginForm) {
    loginForm[key as keyof typeof loginForm] =
      defaultLoginForm[key as keyof typeof defaultLoginForm]!
  }
  clearFiles(['web', 'login', 'bg'])
  if (reset2Default) {
    addChangeArray('web', '', 'file')
    addChangeArray('login', '', 'file')
    addChangeArray('bg', '', 'file')
    web.value = ''
    login.value = ''
    bg.value = ''
  }
}
const resetTopForm = (reset2Default?: boolean) => {
  for (const key in topForm) {
    topForm[key as keyof typeof topForm] = defaultTopForm[key as keyof typeof defaultTopForm]
  }
  clearFiles(['navigate'])
  if (reset2Default) {
    addChangeArray('navigate', '', 'file')
    navigate.value = ''
  }
}

const resetMobileForm = (reset2Default?: boolean) => {
  clearFiles(['mobileLogin', 'mobileLoginBg'])
  if (reset2Default) {
    addChangeArray('mobileLogin', '', 'file')
    addChangeArray('mobileLoginBg', '', 'file')
    mobileLogin.value = ''
    mobileLoginBg.value = ''
  }
}

const uploadImg = (options: any) => {
  const file = options.file
  if (file['flag'] === 'web') {
    web.value = URL.createObjectURL(file)
  } else if (file['flag'] === 'bg') {
    bg.value = URL.createObjectURL(file)
  } else if (file['flag'] === 'login') {
    login.value = URL.createObjectURL(file)
  } else if (file['flag'] === 'navigate') {
    navigate.value = URL.createObjectURL(file)
  } else if (file['flag'] === 'mobileLogin') {
    mobileLogin.value = URL.createObjectURL(file)
  } else if (file['flag'] === 'mobileLoginBg') {
    mobileLoginBg.value = URL.createObjectURL(file)
  }
}
const beforeUpload = (file: any, { type, size, tips }: any) => {
  if (file.size > size) {
    ElMessage.error(tips)
    return false
  }
  addChangeArray(type, file.uid, 'file')
  let len = fileList.value?.length
  let match = false
  file.flag = type
  while (len--) {
    const tfile = fileList.value[len]
    if (type == tfile['flag']) {
      fileList.value[len] = file
      match = true
    }
  }
  if (!match) {
    fileList.value?.push(file)
  }
  return true
}

const clearFiles = (array?: string[]) => {
  if (!array?.length || !fileList.value?.length) {
    fileList.value = []
    return
  }
  let len = fileList.value.length
  while (len--) {
    const file = fileList.value[len]
    if (array.includes(file['flag'])) {
      fileList.value.splice(len, 1)
    }
  }
}

const getHeight = () => {
  const dom = document.getElementsByClassName('navigate-preview')
  const width = dom[0].clientWidth
  navigateHeight.value = parseInt((width * 0.625).toString())
}

onMounted(() => {
  init()
  nextTick(() => {
    getHeight()
  })
  window.addEventListener('resize', getHeight)
})
onUnmounted(() => {
  window.removeEventListener('resize', getHeight)
})
</script>

<style lang="less" scoped>
.appearance {
  position: relative;
  height: 100%;
  & > .ed-scrollbar {
    .scroll-content {
      padding: 16px 24px 80px 24px;
      height: 100%;
      position: relative;
      z-index: 10;
    }
  }
  .router-title {
    color: #1f2329;
    font-feature-settings:
      'clig' off,
      'liga' off;
    font-family: var(--de-custom_font, 'PingFang');
    font-size: 20px;
    font-style: normal;
    font-weight: 500;
    line-height: 28px;
  }
  .appearance-table__content {
    width: 100%;
    min-width: 840px;
    margin-top: 16px;
    height: 100%;
    box-sizing: border-box;

    :deep(.ed-form-item__error) {
      top: 88%;
    }
    :deep(.ed-form-item__label) {
      line-height: 22px !important;
      height: 22px;
    }

    .login,
    .setting {
      background: var(--ContentBG, #ffffff);
      width: 100%;
      border-radius: 6px;

      & > :nth-child(1) {
        font-size: 16px;
        font-weight: 500;
        line-height: 24px;
      }
    }

    .theme {
      :deep(.ed-color-picker__trigger) {
        padding: 0 !important;
        height: 26px !important;
        width: 26px !important;
      }
      :deep(.ed-color-picker__icon) {
        display: none;
      }
      :deep(.ed-color-picker) {
        height: 28px !important;
        padding: 0;
      }
      .navigate-bg {
        font-size: 14px;
        font-weight: 400;
        line-height: 22px;
        margin: 16px 0 8px 0;
      }
      .theme-bg {
        font-size: 14px;
        font-weight: 400;
        line-height: 22px;
        margin: 16px 0 8px 0;
      }
      :deep(.ed-color-picker) {
        height: 32px;
        .ed-color-picker__trigger {
          height: 100%;
          padding: 8px;
        }
      }

      .color-type {
        display: flex;
        .color-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: space-between;
          padding-top: 10px;
          width: 258px;
          height: 184px;
          border-radius: 6px;
          border: 1px solid #dee0e3;
          background-color: #f5f6f7;
          margin-right: 17px;
          &:hover {
            cursor: pointer;
          }
          img {
            width: 180px;
            height: 120px;
          }

          .color-item-label {
            height: 40px;
            width: 100%;
            border-top: 1px solid #dddedf;
            display: flex;
            align-items: center;
            padding-left: 12px;
            background-color: #fff;
            border-bottom-left-radius: 4px;
            border-bottom-right-radius: 4px;
          }
          &.active {
            border-color: var(--ed-color-primary);
            .color-item-label {
              background-color: #ebf1ff;
            }
          }
        }
      }

      .show-theme {
        font-weight: 500;
        font-size: 14px;
        line-height: 22px;
        margin-bottom: 16px;
      }

      .theme-color {
        .btn-select {
          height: 32px;
          display: inline-flex;
          padding: 0 4px;
          align-items: center;
          justify-content: center;
          background: #ffffff;
          border: 1px solid var(--ed-border-color);
          border-radius: 6px;

          .is-active {
            background: var(--ed-color-primary-1a, #1cba901a);
            font-weight: 500;
          }

          .ed-button:not(.is-active) {
            color: #1f2329;
          }
          .ed-button.is-text {
            height: 24px;
            padding: 0 8px;
            line-height: 22px;
          }
          .ed-button + .ed-button {
            margin-left: 4px;
          }
        }
      }
    }

    .setting,
    .login {
      margin-top: 24px;
    }

    .login.custom {
      margin-top: 19px;
    }

    .login {
      .page-preview {
        background-color: #f8f9fa;
        border: 1px solid #dee0e3;
        margin-top: 16px;
        padding: 16px;
        border-radius: 12px;
        .title {
          margin-bottom: 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          .left {
            font-size: 14px;
            font-weight: 500;
            line-height: 22px;
          }
        }

        .page-setting {
          display: flex;
          justify-content: space-between;
          .page-content {
            width: calc(100% - 378px);

            .tips-page {
              margin-top: 8px;
            }
            .navigate-preview {
              height: calc(100% - 28px);
              background-color: #fff;
              border-radius: 6px;
              overflow: hidden;
              position: relative;

              .navigate-head {
                width: 240px;
                margin-bottom: 1px;
                background-color: #eff1f0;
                padding: 16px;
                height: 100%;
                position: relative;

                .header-sql {
                  width: 131px;
                  display: flex;
                  align-items: center;
                  font-size: 16px;
                  font-weight: 500;
                }

                .bottom-sql {
                  position: absolute;
                  bottom: 16px;
                  left: 16px;
                  display: flex;
                  align-items: center;
                  width: calc(100% - 32px);

                  .fold {
                    cursor: pointer;
                    margin-left: auto;
                  }
                }
              }

              .welcome-content {
                width: calc(100% - 240px);
                display: flex;
                gap: 16px;
                align-items: center;
                flex-direction: column;
                position: absolute;
                right: 0;
                top: 50%;
                transform: translateY(-50%);

                .greeting {
                  display: flex;
                  align-items: center;
                  gap: 16px;
                  line-height: 32px;
                  font-size: 24px;
                  font-weight: 600;
                  color: rgba(31, 35, 41, 1);
                }

                .sub {
                  color: grey;
                  font-size: 16px;
                  line-height: 24px;
                }

                .greeting-btn {
                  width: 80%;
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
            }
          }

          .config-list {
            width: 378px;
            margin-left: 16px;
            .doc-input {
              padding-left: 24px;
              margin: 8px 0;
            }

            .label {
              font-weight: 400;
              font-size: 14px;
              line-height: 22px;
            }

            .config-item {
              min-height: 104px;
              margin-bottom: 8px;
              padding: 16px;
              border-radius: 6px;
              border: 1px solid #dee0e3;
              background: #fff;
              .config-logo {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 8px;
                .logo {
                  font-size: 14px;
                  font-weight: 400;
                  line-height: 22px;
                }
                .ed-button {
                  min-width: 64px;
                  height: 28px;
                  line-height: 28px;
                  padding: 4px 7px;
                  font-size: 12px;
                  font-weight: 400;
                }
              }

              .tips {
                font-size: 12px;
                font-weight: 400;
                line-height: 18px;
                white-space: pre-wrap;
                color: #8f959e;
              }
            }

            .page-Form {
              .form-tips {
                font-size: 14px;
                font-weight: 400;
                line-height: 22px;
                color: #8f959e;
              }

              .appearance-radio-item {
                :deep(.ed-form-item__content) {
                  line-height: 22px;
                }
                :deep(label) {
                  height: 22px;
                  margin-right: 24px;
                }
              }
            }
          }
        }
      }
    }
  }
  .appearance-foot {
    display: flex;
    justify-content: flex-end;
    padding: 16px 24px;
    background: var(--ContentBG, #ffffff);
    position: absolute;
    left: 0;
    bottom: 0;
    width: 100%;
    border-top: 1px solid #1f232926;
    z-index: 100;
  }
}
</style>
