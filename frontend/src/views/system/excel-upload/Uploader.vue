<script setup lang="ts">
import { computed, ref } from 'vue'
import { endsWith, startsWith } from 'lodash-es'
import { useI18n } from 'vue-i18n'
import icon_warning_filled from '@/assets/svg/icon_warning_filled.svg'
import icon_upload_outlined from '@/assets/svg/icon_upload_outlined.svg'
import icon_fileExcel_colorful from '@/assets/datasource/icon_excel.png'
import { genFileId, type UploadInstance, type UploadProps, type UploadRawFile } from 'element-plus'
import { useCache } from '@/utils/useCache.ts'
import { settingsApi } from '@/api/setting.ts'
import ccmUpload from '@/assets/svg/icon_ccm-upload_outlined.svg'

const { t } = useI18n()
const { wsCache } = useCache()

const emits = defineEmits(['upload-finished'])

const props = defineProps<{
  uploadPath: string
  templatePath: string
  templateName: string
}>()

const uploadRef = ref<UploadInstance>()
const uploadLoading = ref(false)

const token = wsCache.get('user.token')
const headers = ref<any>({ 'X-SQLBOT-TOKEN': `Bearer ${token}` })
const getUploadURL = () => {
  return import.meta.env.VITE_API_BASE_URL + props.uploadPath
}

function downloadTemplate() {
  settingsApi
    .downloadTemplate(props.templatePath)
    .then((res) => {
      const blob = new Blob([res], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = props.templateName
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

function downloadErrorFile() {
  settingsApi
    .downloadError(errorFileName.value)
    .then((res) => {
      const blob = new Blob([res], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = errorFileName.value
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

const infoMessage = ref<string>('')
const hasError = ref(false)

const onSuccess = (response: any) => {
  uploadRef.value!.clearFiles()
  fileList.value = []
  hasError.value = false
  infoMessage.value = ''
  emits('upload-finished')
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
  showResult()
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
  <el-button class="no-margin" secondary @click="open">
    <template #icon>
      <ccmUpload></ccmUpload>
    </template>
    {{ $t('user.batch_import') }}
  </el-button>
  <el-dialog
    v-if="dialogShow"
    v-model="dialogShow"
    :title="t('user.batch_import')"
    width="600px"
    class="user-import-class"
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
    v-if="resultShow"
    v-model="resultShow"
    :title="hasError ? t('user.data_import_failed') : t('user.data_import_completed')"
    width="600px"
    class="user-import-class"
    @close="closeResult"
  >
    <div class="down-template-content">
      {{ infoMessage }}
      <el-button
        v-if="hasError && errorFileName.length > 0"
        type="primary"
        link
        class="down-button"
        @click="downloadErrorFile"
      >
        {{ errorFileName }}
      </el-button>
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
</style>
<style scoped lang="less">
.no-margin {
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
    flex-direction: row;
    align-items: center;
  }

  .font12 {
    font-size: 12px;
  }
}
</style>
