<script lang="ts" setup>
import Assistant from '@/views/embedded/AssistantPreview.vue'
import { ref, unref, reactive, nextTick } from 'vue'
import { type UploadUserFile, ElMessage } from 'element-plus-secondary'
import { useI18n } from 'vue-i18n'
import { request } from '@/utils/request'
import { setCurrentColor } from '@/utils/utils'
import { cloneDeep } from 'lodash-es'
import { useAppearanceStoreWithOut } from '@/stores/appearance'

const { t } = useI18n()
const appearanceStore = useAppearanceStoreWithOut()
const currentId = ref()
interface SqlBotForm {
  theme: string
  header_font_color: string
  logo?: string
  x_type: string
  y_type: string
  welcome_desc: string
  float_icon?: string
  welcome: string
  float_icon_drag: boolean
  x_val: number
  y_val: number
}

const optionsY = [
  {
    label: t('embedded.up'),
    value: 'top',
  },
  {
    label: t('embedded.down'),
    value: 'bottom',
  },
]

const optionsX = [
  {
    label: t('embedded.left'),
    value: 'left',
  },
  {
    label: t('embedded.right'),
    value: 'right',
  },
]
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
const fileList = ref<(UploadUserFile & { flag: string })[]>([])
const dialogVisible = ref(false)
const logo = ref('')
const floatIcon = ref('')

const defaultSqlBotForm = reactive<SqlBotForm>({
  x_type: 'right',
  y_type: 'bottom',
  x_val: 30,
  y_val: 30,
  float_icon_drag: false,
  welcome: t('embedded.i_am_sqlbot'),
  welcome_desc: t('embedded.data_analysis_now'),
  theme: '#1CBA90',
  header_font_color: '#1F2329',
  logo: '',
  float_icon: '',
})
const sqlBotForm = reactive<SqlBotForm>(cloneDeep(defaultSqlBotForm)) as { [key: string]: any }
let rawData = {} as { [key: string]: any }
const init = () => {
  Object.assign(sqlBotForm, cloneDeep(defaultSqlBotForm))
  fileList.value = []
  logo.value = rawData.logo
  floatIcon.value = rawData.float_icon

  for (const key in sqlBotForm) {
    if (
      Object.prototype.hasOwnProperty.call(sqlBotForm, key) &&
      ![null, undefined].includes(rawData[key])
    ) {
      sqlBotForm[key] = rawData[key]
    }
  }

  if (!rawData.theme) {
    const { customColor, themeColor } = appearanceStore
    const currentColor =
      themeColor === 'custom' && customColor
        ? customColor
        : themeColor === 'blue'
          ? '#3370ff'
          : '#1CBA90'
    sqlBotForm.theme = currentColor || sqlBotForm.theme
  }

  nextTick(() => {
    setPageCustomColor(sqlBotForm.theme)
    setPageHeaderFontColor(sqlBotForm.header_font_color)
  })
}
const giveUp = () => {
  resetSqlBotForm(false)
  init()
  dialogVisible.value = false
}

const emits = defineEmits(['refresh'])
const saveHandler = () => {
  const param = buildParam()
  const url = '/system/assistant/ui'
  request
    .patch(url, param, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    .then(() => {
      ElMessage.success(t('system.setting_successfully'))
      dialogVisible.value = false
      emits('refresh')
    })
}
const buildParam = () => {
  const formData = new FormData()
  if (fileList.value.length) {
    fileList.value.forEach((file: any) => {
      const name = file.name + ',' + file['flag']
      const fileArray = [file]
      const newfile = new File(fileArray, name, { type: file['type'] })
      formData.append('files', newfile)
    })
  }
  formData.append('data', JSON.stringify({ ...unref(sqlBotForm), id: currentId.value }))
  return formData
}

const headerFontColorChange = (val: any) => {
  setPageHeaderFontColor(val)
}

const customColorChange = (val: any) => {
  setPageCustomColor(val)
}

const setPageCustomColor = (val: any) => {
  const ele = document.querySelector('.left-preview') as HTMLElement
  setCurrentColor(val, ele)
}

const setPageHeaderFontColor = (val: any) => {
  const ele = document.getElementsByClassName('left-preview')[0] as HTMLElement
  ele.style.setProperty('--ed-text-color-primary', val)
}
const resetSqlBotForm = (reset2Default?: boolean) => {
  Object.assign(sqlBotForm, cloneDeep(defaultSqlBotForm))
  clearFiles(['logo', 'float_icon'])
  if (reset2Default) {
    logo.value = ''
    floatIcon.value = ''
    sqlBotForm.restoreDefaults = true
    nextTick(() => {
      setPageCustomColor(sqlBotForm.theme)
      setPageHeaderFontColor(sqlBotForm.header_font_color)
    })
  }
}

const uploadImg = (options: any) => {
  const file = options.file
  if (file['flag'] === 'logo') {
    logo.value = URL.createObjectURL(file)
  } else if (file['flag'] === 'float_icon') {
    floatIcon.value = URL.createObjectURL(file)
  }
}
const beforeUpload = (file: any, type: any) => {
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
const appName = ref('')
const open = (row: any) => {
  rawData = JSON.parse(row.configuration)
  currentId.value = row.id
  appName.value = row.name
  dialogVisible.value = true
  init()
}
defineExpose({
  open,
})
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="$t('embedded.display_settings')"
    width="1000"
    modal-class="embed-third_party_ui"
  >
    <div class="ui-main">
      <div class="left-preview">
        <assistant
          :welcome-desc="sqlBotForm.welcome_desc"
          :welcome="sqlBotForm.welcome"
          :name="appName"
          :logo="logo"
        ></assistant>
      </div>
      <div class="right-form">
        <div style="display: flex; align-items: center; justify-content: space-between">
          <div class="theme">
            <div class="theme-bg">{{ $t('system.customize_theme_color') }}</div>
            <el-color-picker
              v-model="sqlBotForm.theme"
              :trigger-width="28"
              :predefine="COLOR_PANEL"
              is-custom
              effect="light"
              @change="customColorChange"
            />
          </div>
          <div class="theme">
            <div class="theme-bg">{{ $t('embedded.header_text_color') }}</div>
            <el-color-picker
              v-model="sqlBotForm.header_font_color"
              :trigger-width="28"
              :predefine="COLOR_PANEL"
              is-custom
              effect="light"
              @change="headerFontColorChange"
            />
          </div>
        </div>

        <div class="config-item" style="margin-top: 3px">
          <div class="config-logo">
            <span class="logo">{{ $t('embedded.app_logo') }}</span>
            <el-upload
              name="logo"
              :show-file-list="false"
              accept=".jpg,.png,.gif,.svg"
              :before-upload="(e: any) => beforeUpload(e, 'logo')"
              :http-request="uploadImg"
            >
              <el-button secondary>{{ t('embedded.replace') }}</el-button>
            </el-upload>
          </div>
          <div class="tips">{{ $t('embedded.maximum_size_10mb') }}</div>
        </div>

        <div class="config-item float-icon">
          <div class="config-logo">
            <span class="logo">{{ $t('embedded.window_entrance_icon') }}</span>
            <el-upload
              name="float_icon"
              :show-file-list="false"
              accept=".jpg,.png,.gif,.svg"
              :before-upload="(e: any) => beforeUpload(e, 'float_icon')"
              :http-request="uploadImg"
            >
              <el-button secondary>{{ t('embedded.replace') }}</el-button>
            </el-upload>
          </div>
          <div class="tips">{{ $t('embedded.maximum_size_10mb') }}</div>
          <div style="background: #1f232926; height: 1px; margin: 12px 0"></div>
          <div class="position-set">
            {{ $t('embedded.default_icon_position') }}
            <el-checkbox
              v-model="sqlBotForm.float_icon_drag"
              :label="$t('embedded.draggable_position')"
            />
          </div>
          <div class="position-set_input">
            <div class="x">
              <el-input-number
                v-model="sqlBotForm.x_val"
                step-strictly
                :min="0"
                controls-position="right"
              >
                <template #prefix>
                  <el-select v-model="sqlBotForm.x_type" style="width: 51px">
                    <el-option
                      v-for="item in optionsX"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </el-select>
                </template> </el-input-number
              >px
            </div>
            <div class="y">
              <el-input-number
                v-model="sqlBotForm.y_val"
                step-strictly
                :min="0"
                controls-position="right"
              >
                <template #prefix>
                  <el-select v-model="sqlBotForm.y_type" style="width: 51px">
                    <el-option
                      v-for="item in optionsY"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </el-select>
                </template> </el-input-number
              >px
            </div>
          </div>
        </div>
        <el-form
          label-position="top"
          require-asterisk-position="right"
          label-width="120px"
          class="page-Form"
        >
          <el-form-item :label="$t('system.welcome_message')">
            <el-input
              v-model="sqlBotForm.welcome"
              :placeholder="
                $t('datasource.please_enter') + $t('common.empty') + $t('system.welcome_message')
              "
              maxlength="50"
            />
          </el-form-item>
          <el-form-item :label="$t('embedded.welcome_description')">
            <el-input
              v-model="sqlBotForm.welcome_desc"
              :placeholder="
                $t('datasource.please_enter') +
                $t('common.empty') +
                $t('embedded.welcome_description')
              "
              type="textarea"
              show-word-limit
              maxlength="200"
            />
          </el-form-item>
        </el-form>
        <div class="btns">
          <el-button secondary @click="resetSqlBotForm(true)">{{
            t('system.restore_default')
          }}</el-button>
          <el-button style="margin-left: auto" secondary @click="giveUp">{{
            t('common.cancel')
          }}</el-button>
          <el-button type="primary" @click="saveHandler">{{ t('common.save') }}</el-button>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<style lang="less">
.embed-third_party_ui {
  .ui-main {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 628px;

    .left-preview {
      width: 460px;
      height: 100%;

      .content {
        pointer-events: none;
      }
    }

    .right-form {
      width: 470px;
      height: 100%;
      position: relative;

      .theme {
        width: 223px;

        .ed-color-picker__trigger {
          padding: 0 !important;
          height: 26px !important;
          width: 26px !important;
        }
        .ed-color-picker__icon {
          display: none;
        }
        .ed-color-picker {
          height: 28px !important;
          padding: 0;
        }

        .theme-bg {
          font-size: 14px;
          font-weight: 400;
          line-height: 22px;
          margin: 0 0 8px 0;
        }
        .ed-color-picker {
          height: 32px;
          .ed-color-picker__trigger {
            height: 100%;
            padding: 8px;
          }
        }
      }

      .config-item {
        min-height: 86px;
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
            min-width: 48px;
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

      .position-set,
      .position-set_input {
        display: flex;
        align-items: center;
        justify-content: space-between;
      }

      .position-set_input {
        margin-top: 8px;
        .x,
        .y {
          display: flex;
          align-items: center;

          .ed-input-number.is-controls-right .ed-input-number__increase {
            --ed-input-number-controls-height: 17px;
          }

          .ed-input-number {
            margin-right: 8px;
          }

          .ed-input-number.is-controls-right .ed-input__wrapper {
            padding-left: 1px;
          }
          .ed-select__wrapper {
            box-shadow: none;
            padding-right: 0;
          }
          .ed-input__prefix {
            border-right: 1px solid #d9dcdf;
          }
        }
      }

      .page-Form {
        margin-top: 8px;
        .ed-form-item {
          margin-bottom: 8px;
        }

        .ed-form-item--label-top .ed-form-item__label {
          height: 22px;
          line-height: 22px;
        }

        .ed-textarea__inner {
          padding-bottom: 14px;
        }
      }

      .btns {
        display: flex;
        align-items: center;
        justify-content: space-between;
        position: absolute;
        left: 0;
        bottom: 0;
        width: 100%;
      }
    }
  }
}
</style>
