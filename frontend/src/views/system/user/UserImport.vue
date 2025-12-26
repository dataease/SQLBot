<script lang="ts" setup>
import icon_warning_filled from '@/assets/svg/icon_info_colorful.svg'
import icon_upload_outlined from '@/assets/svg/icon_upload_outlined.svg'
import icon_fileExcel_colorful from '@/assets/datasource/icon_excel.png'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import { ref, reactive, h } from 'vue'
import {
  ElMessage,
  ElMessageBox,
  ElLoading,
  type UploadRequestOptions,
  type UploadProps,
  ElButton,
} from 'element-plus-secondary'
import { useI18n } from 'vue-i18n'
import { userImportApi } from '@/api/user'
const { t } = useI18n()
const defaultTip = t('user.xls_format_files')
const loadingInstance = ref<any>(null)
const dialogShow = ref(false)
const form = ref({})
const file = ref<any>(null)
const fileName = ref('')
const errorFileKey = ref(null)
const emits = defineEmits(['refresh-grid'])
const state = reactive({
  errList: [],
  filesTmp: [],
})

const showLoading = () => {
  loadingInstance.value = ElLoading.service({ target: '.user-import-class' })
}
const closeLoading = () => {
  loadingInstance.value?.close()
}
const showDialog = () => {
  file.value = null
  fileName.value = ''
  errorFileKey.value = null
  dialogShow.value = true
}
const closeDialog = () => {
  dialogShow.value = false
}
const handleExceed: UploadProps['onExceed'] = () => {
  ElMessage.warning(t('userimport.exceedMsg'))
}
const handleError = () => {
  ElMessage.warning(t('user.contact_the_administrator'))
}
const uploadValidate = (file: any) => {
  const suffix = file.name.substring(file.name.lastIndexOf('.') + 1)
  if (suffix !== 'xlsx' && suffix !== 'xls') {
    ElMessage.warning(t('userimport.suffixMsg'))
    return false
  }

  if (file.size / 1024 / 1024 > 10) {
    ElMessage.warning(t('userimport.limitMsg'))
    return false
  }
  state.errList = []
  return true
}
const fileSize = ref('-')
const setFile = (options: UploadRequestOptions) => {
  file.value = options.file
  fileName.value = options.file.name
  fileSize.value = setSize(options.file.size)
}

const buildFormData = (file: any, files: any, param: any) => {
  const formData = new FormData()
  if (file) {
    formData.append('file', file)
  }
  if (files) {
    files.forEach((f: any) => {
      formData.append('files', f)
    })
  }
  if (param) {
    formData.append('request', new Blob([JSON.stringify(param)], { type: 'application/json' }))
  }

  return formData
}
const downExcel = () => {
  showLoading()
  userImportApi
    .downExcelTemplateApi()
    .then((res) => {
      const blob = new Blob([res], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const link = document.createElement('a')
      link.style.display = 'none'
      link.href = URL.createObjectURL(blob)
      link.download = 'user.xlsx' // 下载的文件名
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      closeLoading()
    })
    .catch(() => {
      closeLoading()
    })
}

const setSize = (size: any) => {
  let data = ''
  const _size = Number.parseFloat(size)
  if (_size < 1 * 1024) {
    //如果小于0.1KB转化成B
    data = _size.toFixed(2) + 'B'
  } else if (_size < 1 * 1024 * 1024) {
    //如果小于0.1MB转化成KB
    data = (_size / 1024).toFixed(2) + 'KB'
  } else if (_size < 1 * 1024 * 1024 * 1024) {
    //如果小于0.1GB转化成MB
    data = (_size / (1024 * 1024)).toFixed(2) + 'MB'
  } else {
    //其他转化成GB
    data = (_size / (1024 * 1024 * 1024)).toFixed(2) + 'GB'
  }
  const size_str = data + ''
  const len = size_str.indexOf('.')
  const dec = size_str.substr(len + 1, 2)
  if (dec == '00') {
    //当小数点后为00时 去掉小数部分
    return size_str.substring(0, len) + size_str.substr(len + 3, 2)
  }
  return size_str
}

const toGrid = () => {
  file.value = null
  fileName.value = ''
  dialogShow.value = false
  emits('refresh-grid')
}

const clearFile = () => {
  file.value = null
  fileName.value = ''
}
const sure = () => {
  const param = buildFormData(file.value, null, null)
  showLoading()
  userImportApi
    .importUserApi(param)
    .then((res) => {
      closeLoading()
      const data = res
      errorFileKey.value = data.dataKey
      closeDialog()
      showTips(data.successCount, data.errorCount)
    })
    .catch(() => {
      closeLoading()
    })
}
const downErrorExcel = () => {
  if (errorFileKey.value) {
    showLoading()
    userImportApi
      .downErrorRecordApi(errorFileKey.value)
      .then((res) => {
        const blob = new Blob([res], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        const link = document.createElement('a')
        link.style.display = 'none'
        link.href = URL.createObjectURL(blob)
        link.download = 'error.xlsx'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        closeLoading()
        // closeDialog()
      })
      .catch(() => {
        closeLoading()
      })
  }
}
const showTips = (successCount: any, errorCount: any) => {
  let title = successCount ? t('user.data_import_completed') : t('user.data_import_failed')
  const childrenDomList = [
    h('strong', null, title),
    h('br', {}, {}),
    h('span', null, t('user.imported_100_data', { msg: successCount })),
  ]
  if (errorCount) {
    const errorCountDom = h('span', null, t('user.failed_100_can', { msg: errorCount }))
    const errorDom = h('div', { class: 'error-record-tip flex-align-center' }, [
      /* h('span', null, t('user.can')), */
      h(
        ElButton,
        {
          onClick: downErrorExcel,
          type: 'primary',
          text: true,
          class: 'down-button',
        },
        t('user.download_error_report')
      ),
      h('span', null, t('user.modify_and_re_import')),
    ])

    childrenDomList.push(errorCountDom)
    childrenDomList.push(errorDom)
  }
  ElMessageBox.confirm('', {
    confirmButtonType: 'primary',
    type: !errorCount ? 'success' : successCount ? 'warning' : 'error',
    autofocus: false,
    dangerouslyUseHTMLString: true,
    message: h('div', { class: 'import-tip-box' }, childrenDomList),
    showClose: false,
    cancelButtonText: t('user.return_to_view'),
    confirmButtonText: t('user.continue_importing'),
  })
    .then(() => {
      // clearErrorRecord()
      showDialog()
      emits('refresh-grid')
    })
    .catch(() => {
      // clearErrorRecord()
      toGrid()
    })
}
/* const clearErrorRecord = () => {
  if (errorFileKey.value) {
    userImportApi.clearErrorApi(errorFileKey.value)
  }
} */

const rules = {
  file: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('user.file'),
      trigger: 'blur',
    },
  ],
}

defineExpose({
  showDialog,
})
</script>
<template>
  <el-dialog
    v-model="dialogShow"
    :title="t('user.batch_import')"
    width="600px"
    modal-class="user-import-class"
    @before-close="closeDialog"
  >
    <div class="down-template">
      <span class="icon-span">
        <el-icon>
          <Icon name="icon_warning_filled"><icon_warning_filled class="svg-icon" /></Icon>
        </el-icon>
      </span>
      <div class="down-template-content">
        <span>{{ t('user.please_first') }}</span>
        <el-button type="primary" text class="down-button" @click="downExcel">{{
          t('user.download_the_template')
        }}</el-button>
        <span>{{ t('user.required_and_upload') }}</span>
      </div>
    </div>
    <el-form
      ref="form"
      label-position="top"
      :rules="rules"
      class="form-content_error import-form"
      :model="form"
      label-width="0px"
      @submit.prevent
    >
      <el-form-item prop="file" :label="t('user.file')" style="margin-bottom: 0px">
        <div v-if="fileName" class="pdf-card">
          <img :src="icon_fileExcel_colorful" width="40px" height="40px" />
          <div class="file-name">
            <div class="name">{{ fileName }}</div>
            <div class="size">{{ fileName.split('.')[1] }} - {{ fileSize }}</div>
          </div>
          <el-icon class="action-btn" size="16" @click="clearFile">
            <IconOpeDelete></IconOpeDelete>
          </el-icon>
        </div>
        <el-upload
          v-if="fileName"
          class="upload-user"
          action=""
          accept=".xlsx,.xls"
          :on-exceed="handleExceed"
          :before-upload="uploadValidate"
          :on-error="handleError"
          :show-file-list="false"
          :file-list="state.filesTmp"
          :http-request="setFile"
        >
          <el-button text style="line-height: 22px; height: 22px">
            {{ $t('user.change_file') }}
          </el-button>
        </el-upload>
        <el-upload
          v-else
          class="upload-user"
          action=""
          accept=".xlsx,.xls"
          :on-exceed="handleExceed"
          :before-upload="uploadValidate"
          :on-error="handleError"
          :show-file-list="false"
          :file-list="state.filesTmp"
          :http-request="setFile"
        >
          <el-button secondary>
            <el-icon size="16" style="margin-right: 4px">
              <icon_upload_outlined></icon_upload_outlined>
            </el-icon>
            {{ t('user.upload_file') }}</el-button
          >
        </el-upload>

        <el-link
          v-if="!fileName"
          style="width: 100%; line-height: 22px; height: 22px; justify-content: start"
          class="font12"
          type="info"
          disabled
        >
          {{ defaultTip }}
        </el-link>
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button secondary @click="closeDialog">{{ t('common.cancel') }}</el-button>
        <el-button
          :type="file && fileName ? 'primary' : 'info'"
          :disabled="!file || !fileName"
          @click="sure"
          >{{ t('user.import') }}</el-button
        >
      </span>
    </template>
  </el-dialog>
</template>

<style lang="less">
.user-import-class {
  .upload-user {
    height: 32px;
    .ed-upload {
      width: 100% !important;
    }
  }
  .color-danger {
    :deep(.el-link--inner) {
      color: var(--deDanger, #f54a45) !important;
    }
  }
  .font12 {
    color: #8f959e !important;
    font-family: var(--de-custom_font, 'PingFang');
    font-size: 14px;
    font-style: normal;
    font-weight: 400;
    line-height: 22px;
  }
  .down-template {
    display: flex;
    width: 100%;
    height: 40px;
    align-items: center;
    line-height: 40px;
    background: var(--ed-color-primary-80, #d2f1e9);
    border-radius: 4px;
    padding-left: 10px;
    .icon-span {
      color: var(--ed-color-primary);
      font-size: 18px;
      i {
        top: 3px;
      }
    }
    .down-template-content {
      font-size: 14px;
      display: flex;
      flex-direction: row;
      margin-left: 10px;
      .down-button {
        height: 40px;
      }
    }
  }
  .import-form {
    margin-top: 16px;

    .pdf-card {
      width: 100%;
      height: 58px;
      display: flex;
      align-items: center;
      padding: 0 16px 0 12px;
      border: 1px solid #dee0e3;
      border-radius: 6px;

      .file-name {
        margin-left: 8px;
        .name {
          font-weight: 400;
          font-size: 14px;
          line-height: 22px;
        }

        .size {
          font-weight: 400;
          font-size: 12px;
          line-height: 20px;
          color: #8f959e;
        }
      }

      .action-btn {
        margin-left: auto;
      }

      .ed-icon {
        position: relative;
        cursor: pointer;
        color: #646a73;

        &::after {
          content: '';
          background-color: #1f23291a;
          position: absolute;
          border-radius: 6px;
          width: 24px;
          height: 24px;
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
    }
  }
  .import-tip-box {
    strong {
      font-size: 16px;
    }
    span {
      font-size: 13px;
    }
    .error-record-tip {
      font-size: 13px;
      flex-flow: wrap;
    }
  }
}
</style>
