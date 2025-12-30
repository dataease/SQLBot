<script setup lang="ts">
import { computed, ref } from 'vue'
import { endsWith, startsWith } from 'lodash-es'
import { useI18n } from 'vue-i18n'
import icon_warning_filled from '@/assets/svg/icon_warning_filled.svg'
import icon_upload_outlined from '@/assets/svg/icon_upload_outlined.svg'
import icon_fileExcel_colorful from '@/assets/datasource/icon_excel.png'
import { genFileId, type UploadInstance, type UploadProps, type UploadRawFile } from 'element-plus'
import { useCache } from '@/utils/useCache.ts'
import { datasourceApi } from '@/api/datasource'
import { getLocale } from '@/utils/utils.ts'
import ccmUpload from '@/assets/svg/icon_export_outlined.svg'

const { t } = useI18n()
const { wsCache } = useCache()

const emits = defineEmits(['upload-finished'])

const props = defineProps<{
  uploadPath: string
}>()

const uploadRef = ref<UploadInstance>()
const uploadLoading = ref(false)

const token = wsCache.get('user.token')
const locale = getLocale()
const headers = ref<any>({ 'X-SQLBOT-TOKEN': `Bearer ${token}`, 'Accept-Language': locale })
const getUploadURL = () => {
  return import.meta.env.VITE_API_BASE_URL + props.uploadPath
}

function downloadTemplate() {
  datasourceApi
    .exportDsSchema(0)
    .then((res) => {
      const blob = new Blob([res], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = t('parameter.import_notes') + '.xlsx'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    })
    .catch(async (error) => {
      if (error.response) {
        try {
          let text = await error.response.data.text()
          try {
            text = JSON.parse(text)
          } finally {
            ElMessage({
              message: text,
              type: 'error',
              showClose: true,
            })
          }
        } catch (e) {
          console.error('Error processing error response:', e)
        }
      } else {
        console.error('Other error:', error)
        ElMessage({
          message: error,
          type: 'error',
          showClose: true,
        })
      }
    })
}

const handleExceed: UploadProps['onExceed'] = (files) => {
  uploadRef.value!.clearFiles()
  const file = files[0] as UploadRawFile
  file.uid = genFileId()
  uploadRef.value!.handleStart(file)
}
const fileList = ref<Array<any>>([])
const fileName = computed(() => {
  if (fileList.value.length > 0) {
    return fileList.value[0].name
  }
  return undefined
})

const beforeUpload = (rawFile: any) => {
  if (rawFile.size / 1024 / 1024 > 50) {
    ElMessage.error(t('common.not_exceed_50mb'))
    return false
  }
  uploadLoading.value = true
  return true
}

const errorFileName = ref<string>('')

const infoMessage = ref<string>('')
const hasError = ref(false)

const onSuccess = (response: any) => {
  uploadRef.value!.clearFiles()
  fileList.value = []
  hasError.value = false
  infoMessage.value = ''
  emits('upload-finished', true)
  if (response?.data?.failed_count > 0 && response?.data?.error_excel_filename) {
    infoMessage.value = t('training.upload_failed', {
      success: response.data.success_count,
      fail: response.data.failed_count,
      fail_info: '',
    })
    errorFileName.value = response.data.error_excel_filename
    hasError.value = true
  } else {
    infoMessage.value = t('training.upload_success')
    hasError.value = false
  }
  uploadLoading.value = false
  close()
  showResult()
}

const onError = (err: Error) => {
  uploadLoading.value = false
  uploadRef.value!.clearFiles()
  fileList.value = []
  let msg = err.message
  if (startsWith(msg, '"') && endsWith(msg, '"')) {
    msg = msg.slice(1, msg.length - 1)
  }
  errorFileName.value = ''
  infoMessage.value = msg
  hasError.value = true
  close()
  ElMessage.error(err.toString())
}

const dialogShow = ref<boolean>(false)

const resultShow = ref(false)

function showResult() {
  resultShow.value = true
}
function closeResult() {
  resultShow.value = false
}
function backToUpload() {
  closeResult()
  open()
}
function open() {
  dialogShow.value = true
  errorFileName.value = ''
  fileList.value = []
  hasError.value = false
  infoMessage.value = ''
}

function close() {
  uploadRef.value!.clearFiles()
  fileList.value = []
  dialogShow.value = false
}

const submitUpload = () => {
  uploadRef.value!.submit()
}
</script>

<template>
  <el-button class="up-loader-remark" secondary @click="open">
    <template #icon>
      <ccmUpload></ccmUpload>
    </template>
    {{ $t('parameter.import_notes') }}
  </el-button>
  <el-dialog
    v-if="dialogShow"
    v-model="dialogShow"
    :title="t('user.batch_import')"
    width="600px"
    modal-class="up-loader_dialog"
    @close="close"
  >
    <div class="import-container">
      <div class="down-template">
        <span class="icon-span">
          <el-icon>
            <Icon name="icon_warning_filled"><icon_warning_filled class="svg-icon" /></Icon>
          </el-icon>
        </span>
        <div class="down-template-content">
          <span>{{ t('common.upload_hint_first') }}</span>
          <el-button type="primary" link class="down-button" @click="downloadTemplate">
            {{ t('common.upload_hint_download_template') }}
          </el-button>
          <span>{{ t('common.upload_hint_end') }}</span>
        </div>
        <div style="width: 100%; line-height: 22px; padding: 0 26px; margin: -10px 0 8px 0">
          {{ $t('parameter.memo') }}
        </div>
      </div>
      <div style="width: 100%">
        <el-upload
          ref="uploadRef"
          v-model:file-list="fileList"
          style="width: 100%"
          :multiple="false"
          accept=".xlsx,.xls"
          :action="getUploadURL()"
          :before-upload="beforeUpload"
          :headers="headers"
          :on-success="onSuccess"
          :on-error="onError"
          :show-file-list="false"
          :auto-upload="false"
          :limit="1"
          :on-exceed="handleExceed"
        >
          <el-input
            v-model="fileName"
            style="width: 100%"
            :placeholder="t('common.click_to_select_file')"
            readonly
          >
            <template #suffix>
              <el-icon>
                <Icon name="icon_upload_outlined">
                  <icon_upload_outlined class="svg-icon" />
                </Icon>
              </el-icon>
            </template>
            <template #prefix>
              <img v-if="!!fileName" :src="icon_fileExcel_colorful" width="16px" height="16px" />
            </template>
          </el-input>
        </el-upload>

        <div>
          <el-link class="font12" type="info" disabled>
            {{ t('common.excel_file_type_limit') }}
          </el-link>
        </div>
      </div>
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="close">{{ t('common.cancel') }}</el-button>
        <el-button
          :type="fileName ? 'primary' : 'info'"
          :disabled="!fileName"
          @click="submitUpload"
        >
          {{ t('user.import') }}
        </el-button>
      </span>
    </template>
  </el-dialog>

  <el-dialog
    v-model="resultShow"
    :title="t('user.notes_import_completed')"
    width="600px"
    class="user-import-class"
    @close="closeResult"
  >
    <div class="down-template-content">
      {{ infoMessage }}
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="closeResult">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="backToUpload">
          {{ t('common.continue_to_upload') }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<style lang="less">
.up-loader_dialog {
  .down-template-content {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
    line-height: 24px;
    height: 24px;

    .down-button {
      padding: 0;
      height: unset !important;
      min-width: unset;
    }
  }
}
</style>
<style scoped lang="less">
.up-loader-remark {
  margin: 0;
}
.import-container {
  display: flex;
  flex-direction: column;
  gap: 16px;

  :deep(.ed-upload) {
    width: 100%;
  }
  .down-template {
    display: flex;
    width: 100%;
    min-height: 40px;
    flex-wrap: wrap;
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

  .font12 {
    font-size: 12px;
  }
}
</style>
