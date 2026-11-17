<template>
  <el-dialog
    v-model="dialogVisible"
    :title="dialogTitle"
    width="600"
    :destroy-on-close="true"
    :close-on-click-modal="false"
    modal-class="add-datasource_dialog"
    @closed="close"
  >
    <template #header>
      <div style="display: flex">
        <div style="margin-right: 24px">{{ dialogTitle }}</div>
        <el-steps
          v-show="isCreate"
          :active="active"
          align-center
          custom
          style="max-width: 400px; flex: 1"
        >
          <el-step :title="t('ds.form.base_info')" />
          <el-step :title="t('ds.form.choose_tables')" />
        </el-steps>
      </div>
    </template>

    <div v-show="active === 0" class="container">
      <el-form
        ref="dsFormRef"
        :model="form"
        label-position="top"
        label-width="auto"
        :rules="rules"
        @submit.prevent
      >
        <el-form-item :label="t('ds.form.name')" prop="name">
          <el-input v-model="form.name" clearable />
        </el-form-item>
        <el-form-item :label="t('ds.form.description')">
          <el-input v-model="form.description" clearable :rows="2" type="textarea" />
        </el-form-item>
        <el-form-item :label="t('ds.type')" prop="type">
          <el-select v-model="form.type" placeholder="Select Type" :disabled="!isCreate">
            <el-option
              v-for="item in dsType"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <div v-if="form.type === 'excel'">
          <el-form-item label="File">
            <el-upload
              :disabled="!isCreate"
              accept=".xls, .xlsx, .csv"
              :headers="headers"
              :action="getUploadURL"
              :before-upload="beforeUpload"
              :on-success="onSuccess"
            >
              <el-button :disabled="!isCreate">{{ t('ds.form.upload.button') }}</el-button>
              <template #tip>
                <div class="el-upload__tip">{{ t('ds.form.upload.tip') }}</div>
              </template>
            </el-upload>
          </el-form-item>
        </div>
        <div v-else>
          <el-form-item :label="t('ds.form.host')" prop="host">
            <el-input v-model="form.host" clearable />
          </el-form-item>
          <el-form-item :label="t('ds.form.port')" prop="port">
            <el-input v-model="form.port" clearable />
          </el-form-item>
          <el-form-item :label="t('ds.form.username')">
            <el-input v-model="form.username" clearable />
          </el-form-item>
          <el-form-item :label="t('ds.form.password')">
            <el-input
              v-model="form.password"
              :placeholder="form.id ? t('ds.form.keep_saved_value') : undefined"
              clearable
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item :label="t('ds.form.database')" prop="database">
            <el-input v-model="form.database" clearable />
          </el-form-item>
          <el-form-item
            v-if="form.type === 'oracle'"
            :label="t('ds.form.connect_mode')"
            prop="mode"
          >
            <el-radio-group v-model="form.mode">
              <el-radio value="service_name">{{ t('ds.form.mode.service_name') }}</el-radio>
              <el-radio value="sid">{{ t('ds.form.mode.sid') }}</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item :label="t('ds.form.extra_jdbc')">
            <el-input
              v-model="form.extraJdbc"
              :placeholder="form.id ? t('ds.form.keep_saved_value') : undefined"
              clearable
            />
          </el-form-item>
          <el-form-item
            v-if="haveSchema.includes(form.type)"
            :label="t('ds.form.schema')"
            prop="dbSchema"
          >
            <el-input v-model="form.dbSchema" clearable />
            <el-button v-if="false" link type="primary" :icon="Plus">Get Schema</el-button>
          </el-form-item>
          <el-form-item :label="t('ds.form.timeout')" prop="timeout">
            <el-input-number
              v-model="form.timeout"
              clearable
              :min="0"
              :max="300"
              controls-position="right"
            />
          </el-form-item>
          <span>
            <span>{{ t('ds.form.support_version') }}:&nbsp;</span>
            <span v-if="form.type === 'sqlServer'">2012+</span>
            <span v-else-if="form.type === 'oracle'">12+</span>
            <span v-else-if="form.type === 'mysql'">5.6+</span>
            <span v-else-if="form.type === 'pg'">9.6+</span>
          </span>
        </div>
      </el-form>
    </div>
    <div v-show="active === 1" v-loading="tableListLoading" class="container">
      <el-checkbox-group v-model="checkList" style="position: relative">
        <FixedSizeList
          :item-size="40"
          :data="tableList"
          :total="tableList.length"
          :width="560"
          :height="400"
          :scrollbar-always-on="true"
          class-name="ed-select-dropdown__list"
          layout="vertical"
        >
          <template #default="{ index, style }">
            <div class="list-item_primary" :style="style">
              <el-checkbox :label="tableList[index].tableName">{{
                tableList[index].tableName
              }}</el-checkbox>
            </div>
          </template>
        </FixedSizeList>
      </el-checkbox-group>
      <span>{{ t('ds.form.selected', [checkList.length, tableList.length]) }}</span>
    </div>
    <div style="display: flex; justify-content: flex-end; margin-top: 20px">
      <el-button secondary @click="close">{{ t('common.cancel') }}</el-button>
      <el-button v-show="!isCreate && !isEditTable && form.type !== 'excel'" @click="check">
        {{ t('ds.check') }}
      </el-button>
      <el-button v-show="active === 0 && isCreate" type="primary" @click="next(dsFormRef)">
        {{ t('common.next') }}
      </el-button>
      <el-button v-show="active === 1 && isCreate" @click="preview">
        {{ t('ds.previous') }}
      </el-button>
      <el-button
        v-show="active === 1 || !isCreate"
        :loading="saveLoading"
        type="primary"
        @click="save(dsFormRef)"
      >
        {{ t('common.save') }}
      </el-button>
    </div>
  </el-dialog>
</template>
<script lang="ts" setup>
import { ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { datasourceApi } from '@/api/datasource'
import { encrypted } from './js/aes'
import { ElMessage } from 'element-plus-secondary'
import type { FormInstance, FormRules } from 'element-plus-secondary'
import FixedSizeList from 'element-plus-secondary/es/components/virtual-list/src/components/fixed-size-list.mjs'
import { Plus } from '@element-plus/icons-vue'
import { useCache } from '@/utils/useCache'
import { dsType, haveSchema } from '@/views/ds/js/ds-type'

const { wsCache } = useCache()
const dsFormRef = ref<FormInstance>()
const emit = defineEmits(['refresh'])
const active = ref(0)
const isCreate = ref(true)
const isEditTable = ref(false)
const checkList = ref<any>([])
const tableList = ref<any>([])
const excelUploadSuccess = ref(false)
const tableListLoading = ref(false)
const token = wsCache.get('user.token')
const headers = ref<any>({ 'X-SQLBOT-TOKEN': `Bearer ${token}` })
const dialogTitle = ref('')
const getUploadURL = import.meta.env.VITE_API_BASE_URL + '/datasource/uploadExcel'
const saveLoading = ref<boolean>(false)

const { t } = useI18n()

const rules = reactive<FormRules>({
  name: [
    { required: true, message: t('ds.form.validate.name_required'), trigger: 'blur' },
    { min: 1, max: 50, message: t('ds.form.validate.name_length'), trigger: 'blur' },
  ],
  type: [{ required: true, message: t('ds.form.validate.type_required'), trigger: 'change' }],
  host: [{ required: true, message: 'Please input host', trigger: 'blur' }],
  port: [{ required: true, message: 'Please input port', trigger: 'blur' }],
  database: [{ required: true, message: 'Please input database', trigger: 'blur' }],
  mode: [{ required: true, message: 'Please choose mode', trigger: 'change' }],
  dbSchema: [{ required: true, message: 'Please input schema', trigger: 'blur' }],
})

const dialogVisible = ref<boolean>(false)
const form = ref<any>({
  name: '',
  description: '',
  type: 'mysql',
  configuration: '',
  driver: '',
  host: '',
  port: 0,
  username: '',
  password: '',
  database: '',
  extraJdbc: '',
  dbSchema: '',
  filename: '',
  sheets: [],
  mode: 'service_name',
  timeout: 30,
})

const close = () => {
  dialogVisible.value = false
  isCreate.value = true
  active.value = 0
  isEditTable.value = false
  checkList.value = []
  tableList.value = []
  excelUploadSuccess.value = false
  saveLoading.value = false
}

const open = async (item: any, editTable: boolean = false) => {
  if (item && !item.configuration) item = await datasourceApi.getDs(item.id)
  isEditTable.value = false
  if (item) {
    form.value.password = ''
    form.value.extraJdbc = ''
    dialogTitle.value = editTable ? t('ds.form.title.choose_tables') : t('ds.form.title.edit')
    isCreate.value = false
    form.value.id = item.id
    form.value.name = item.name
    form.value.description = item.description
    form.value.type = item.type
    form.value.configuration = item.configuration
    if (item.configuration) {
      const configuration = JSON.parse(item.configuration)
      form.value.host = configuration.host
      form.value.port = configuration.port
      form.value.username = configuration.username
      form.value.database = configuration.database
      form.value.dbSchema = configuration.dbSchema
      form.value.filename = configuration.filename
      form.value.sheets = configuration.sheets
      form.value.mode = configuration.mode
      form.value.timeout = configuration.timeout ? configuration.timeout : 30
    }

    if (editTable) {
      dialogTitle.value = t('ds.form.choose_tables')
      active.value = 1
      isEditTable.value = true
      isCreate.value = false
      // request tables and check tables

      datasourceApi.tableList(item.id).then((res) => {
        checkList.value = res.map((ele: any) => {
          return ele.table_name
        })
        if (item.type === 'excel') {
          tableList.value = form.value.sheets
        } else {
          tableListLoading.value = true
          datasourceApi
            .getTables(item.id)
            .then((table) => {
              tableList.value = table
              checkList.value = checkList.value.filter((ele: string) => {
                return table
                  .map((ele: any) => {
                    return ele.tableName
                  })
                  .includes(ele)
              })
            })
            .finally(() => {
              tableListLoading.value = false
            })
        }
      })
    }
  } else {
    dialogTitle.value = t('ds.form.title.add')
    isCreate.value = true
    isEditTable.value = false
    checkList.value = []
    tableList.value = []
    form.value = {
      name: '',
      description: '',
      type: 'mysql',
      configuration: '',
      driver: '',
      host: '',
      port: 0,
      username: '',
      password: '',
      database: '',
      extraJdbc: '',
      dbSchema: '',
      filename: '',
      sheets: [],
      mode: 'service_name',
      timeout: 30,
    }
  }
  dialogVisible.value = true
}

const save = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  await formEl.validate((valid) => {
    if (valid) {
      saveLoading.value = true
      const list = tableList.value
        .filter((ele: any) => {
          return checkList.value.includes(ele.tableName)
        })
        .map((ele: any) => {
          return { table_name: ele.tableName, table_comment: ele.tableComment }
        })

      const requestObj = buildConf()
      if (form.value.id) {
        if (!isEditTable.value) {
          // only update datasource config info
          datasourceApi.update(requestObj).then(() => {
            close()
            emit('refresh')
          })
        } else {
          // save table and field
          datasourceApi.chooseTables(form.value.id, list).then(() => {
            close()
            emit('refresh')
          })
        }
      } else {
        requestObj.tables = list
        datasourceApi.add(requestObj).then(() => {
          close()
          emit('refresh')
        })
      }
    }
  })
}

const buildConf = () => {
  form.value.configuration = encrypted(
    JSON.stringify({
      host: form.value.host,
      port: form.value.port,
      username: form.value.username,
      password: form.value.id && !form.value.password ? undefined : form.value.password,
      database: form.value.database,
      extraJdbc: form.value.id && !form.value.extraJdbc ? undefined : form.value.extraJdbc,
      dbSchema: form.value.dbSchema,
      filename: form.value.filename,
      sheets: form.value.sheets,
      mode: form.value.mode,
      timeout: form.value.timeout,
    })
  )
  const obj = JSON.parse(JSON.stringify(form.value))
  delete obj.driver
  delete obj.host
  delete obj.port
  delete obj.username
  delete obj.password
  delete obj.database
  delete obj.extraJdbc
  delete obj.dbSchema
  delete obj.filename
  delete obj.sheets
  delete obj.mode
  delete obj.timeout
  return obj
}

const check = () => {
  const requestObj = buildConf()
  datasourceApi.check(requestObj).then((res: any) => {
    if (res) {
      ElMessage({
        message: t('ds.form.connect.success'),
        type: 'success',
        showClose: true,
      })
    } else {
      ElMessage({
        message: t('ds.form.connect.failed'),
        type: 'error',
        showClose: true,
      })
    }
  })
}

const next = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  await formEl.validate((valid) => {
    if (valid) {
      if (form.value.type === 'excel') {
        // next, show tables
        if (excelUploadSuccess.value) {
          active.value++
        }
      } else {
        // check status if success do next
        const requestObj = buildConf()
        datasourceApi.check(requestObj).then((res: boolean) => {
          if (res) {
            active.value++
            // request tables
            datasourceApi.getTablesByConf(requestObj).then((res) => {
              tableList.value = res
            })
          } else {
            ElMessage({
              message: t('ds.form.connect.failed'),
              type: 'error',
              showClose: true,
            })
          }
        })
      }
    }
  })
}

const preview = () => {
  active.value--
}

const beforeUpload = (rawFile: any) => {
  if (rawFile.size / 1024 / 1024 > 50) {
    ElMessage.error('File size can not exceed 50MB!')
    return false
  }
  return true
}

const onSuccess = (response: any) => {
  form.value.filename = response.data.filename
  form.value.sheets = response.data.sheets
  tableList.value = response.data.sheets
  excelUploadSuccess.value = true
}

defineExpose({ open })
</script>
<style lang="less">
.add-datasource_dialog {
  .container {
    max-height: 600px;
    overflow-y: auto;
    .ed-vl__window.ed-select-dropdown__list::-webkit-scrollbar {
      width: 0;
      height: 0;
    }
  }
}
</style>
