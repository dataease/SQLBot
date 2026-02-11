<script lang="ts" setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { datasourceApi } from '@/api/datasource'
import icon_right_outlined from '@/assets/svg/icon_right_outlined.svg'
import icon_form_outlined from '@/assets/svg/icon_form_outlined.svg'
import icon_import_outlined from '@/assets/svg/icon_import_outlined.svg'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import edit from '@/assets/svg/icon_edit_outlined.svg'
import { useI18n } from 'vue-i18n'
import ParamsForm from './ParamsForm.vue'
import UploaderRemark from '@/views/system/excel-upload/UploaderRemark.vue'
import TableRelationship from '@/views/ds/TableRelationship.vue'
import icon_mindnote_outlined from '@/assets/svg/icon_mindnote_outlined.svg'
import { Refresh } from '@element-plus/icons-vue'
import { debounce } from 'lodash-es'

interface Table {
  name: string
  host: string
  port: string
  username: string
  password: string
  database: string
  extraJdbc: string
  dbSchema: string
  filename: string
  sheets: string
  mode: string
  timeout: string
  configuration: string
  id: number
}

const props = withDefaults(
  defineProps<{
    info: Table
  }>(),
  {
    info: () => ({
      name: '-',
      host: '-',
      port: '-',
      username: '-',
      password: '-',
      database: '-',
      extraJdbc: '-',
      dbSchema: '-',
      filename: '-',
      sheets: '-',
      mode: '-',
      timeout: '-',
      configuration: '-',
      id: 0,
    }),
  }
)
const { t } = useI18n()
const paramsFormRef = ref()
const tableList = ref([] as any[])
const loading = ref(false)
const initLoading = ref(false)
const activeRelationship = ref(false)
const keywords = ref('')
const tableListWithSearch = computed(() => {
  if (!keywords.value) return tableList.value
  return tableList.value.filter((ele) =>
    ele.table_name.toLowerCase().includes(keywords.value.toLowerCase())
  )
})
const total = ref(1000)
const showNum = ref(100)
const currentTable = ref<any>({})
const ds = ref<any>({})
const btnSelect = ref('d')
const isDrag = ref(false)
const tableName = ref<any[]>([])
const pageInfo = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0,
})
const handleRelationship = () => {
  activeRelationship.value = !activeRelationship.value
  tableName.value = []
  currentTable.value = {}
}
const singleDragStartD = (e: DragEvent, ele: any) => {
  isDrag.value = true
  e.dataTransfer!.setData('table', JSON.stringify(ele))
}

const getTableName = (val: any) => {
  tableName.value = val
}

const singleDragEnd = () => {
  isDrag.value = false
}
const handleSizeChange = (val: number) => {
  pageInfo.currentPage = 1
  pageInfo.pageSize = val
}
const handleCurrentChange = (val: number) => {
  pageInfo.currentPage = val
}

const fieldListComputed = computed(() => {
  const { currentPage, pageSize } = pageInfo
  return fieldListTotalComputed.value.slice((currentPage - 1) * pageSize, currentPage * pageSize)
})

const fieldListTotalComputed = computed(() => {
  return fieldList.value.filter((ele: any) =>
    ele.field_name.toLowerCase().includes(fieldName.value.toLowerCase())
  )
})

const init = (reset = false) => {
  initLoading.value = true
  datasourceApi.getDs(props.info.id).then((res) => {
    ds.value = res
    fieldList.value = []
    pageInfo.total = 0
    pageInfo.currentPage = 1
    datasourceApi
      .tableList(props.info.id)
      .then((res) => {
        tableList.value = res

        if (currentTable.value?.id && reset) {
          tableList.value.forEach((ele) => {
            if (ele.id === currentTable.value?.id) {
              clickTable(ele)
            }
          })
        }
      })
      .finally(() => {
        initLoading.value = false
      })
  })
}
onMounted(() => {
  init()
})
const tableComment = ref('')
const fieldDialog = ref<boolean>(false)
const tableDialog = ref<boolean>(false)
const fieldComment = ref('')
const currentField = ref<any>({})
const previewData = ref<any>({})
const fieldList = ref<any>([])

const buildData = () => {
  return { table: currentTable.value, fields: fieldList.value }
}

const handleSelectTableList = () => {
  paramsFormRef.value.open(props.info)
}

const clickTable = (table: any) => {
  if (activeRelationship.value) return
  loading.value = true
  currentTable.value = table
  fieldList.value = []
  pageInfo.total = 0
  previewData.value = []
  datasourceApi
    .fieldList(table.id)
    .then((res) => {
      fieldList.value = res
      pageInfo.total = res.length
      pageInfo.currentPage = 1
      fieldName.value = ''
      datasourceApi.previewData(props.info.id, buildData()).then((res) => {
        previewData.value = res
      })
    })
    .finally(() => {
      loading.value = false
    })
}

const closeTable = () => {
  tableDialog.value = false
}
const editTable = () => {
  tableComment.value = currentTable.value.custom_comment
  tableDialog.value = true
}
const saveTable = () => {
  currentTable.value.custom_comment = tableComment.value
  datasourceApi.saveTable(currentTable.value).then(() => {
    closeTable()
    ElMessage({
      message: t('common.save_success'),
      type: 'success',
      showClose: true,
    })
  })
}
const closeField = () => {
  fieldDialog.value = false
}

const refresh = () => {
  emits('refresh')
  datasourceApi.tableList(props.info.id).then((res) => {
    tableList.value = res
    if (!currentTable.value.table_name) return
    const nameArr = tableList.value.map((ele: any) => ele.table_name)
    if (!nameArr.includes(currentTable.value.table_name)) {
      currentTable.value = {}
    }
  })
}

const saveField = () => {
  currentField.value.custom_comment = fieldComment.value
  datasourceApi.saveField(currentField.value).then(() => {
    closeField()
    ElMessage({
      message: t('common.save_success'),
      type: 'success',
      showClose: true,
    })
  })
}

const editField = (row: any) => {
  currentField.value = row
  fieldComment.value = currentField.value.custom_comment
  fieldDialog.value = true
}

const changeStatus = (row: any) => {
  currentField.value = row
  datasourceApi.saveField(currentField.value).then(() => {
    closeField()
    ElMessage({
      message: t('common.save_success'),
      type: 'success',
      showClose: true,
    })
  })
}

const syncFields = () => {
  loading.value = true
  datasourceApi
    .syncFields(currentTable.value.id)
    .then(() => {
      btnSelectClick('d')
      loading.value = false
    })
    .catch(() => {
      loading.value = false
    })
}

function downloadTemplate() {
  datasourceApi
    .exportDsSchema(props.info.id)
    .then((res) => {
      const blob = new Blob([res], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = props.info.name + '.xlsx'
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

const emits = defineEmits(['back', 'refresh'])
const back = () => {
  emits('back')
}

const renderHeader = ({ column }: any) => {
  //创建一个元素用于存放表头信息
  const span = document.createElement('span')
  // 将表头信息渲染到元素上
  span.innerText = column.label
  // 在界面中添加该元素
  document.body.appendChild(span)
  //获取该元素的宽度（包含内外边距等信息）
  const spanWidth = span.getBoundingClientRect().width + 20 //渲染后的 div 内左右 padding 都是 10，所以 +20
  //判断是否小于element的最小宽度，两者取最大值
  column.minWidth = column.minWidth > spanWidth ? column.minWidth : spanWidth
  // 计算完成后，删除该元素
  document.body.removeChild(span)
  return column.label
}
const fieldNameSearch = debounce(() => {
  pageInfo.currentPage = 1
  pageInfo.total = fieldListTotalComputed.value.length
}, 100)
const fieldName = ref('')
const btnSelectClick = (val: any) => {
  btnSelect.value = val
  loading.value = true

  if (val === 'd') {
    datasourceApi
      .fieldList(currentTable.value.id, { fieldName: '' })
      .then((res) => {
        fieldList.value = res
        pageInfo.total = res.length
        pageInfo.currentPage = 1
        fieldName.value = ''
      })
      .finally(() => {
        loading.value = false
      })
  } else {
    datasourceApi
      .previewData(props.info.id, buildData())
      .then((res) => {
        previewData.value = res
      })
      .finally(() => {
        loading.value = false
      })
  }
}
</script>

<template>
  <div class="data-table no-padding">
    <div class="info">
      <el-button text @click="back">{{ $t('ds.title') }}</el-button>
      <el-icon size="12">
        <icon_right_outlined></icon_right_outlined>
      </el-icon>
      <div class="name">{{ info.name }}</div>
      <div class="export-remark">
        <el-button style="margin-right: 12px" @click="downloadTemplate" secondary>
          <template #icon>
            <icon_import_outlined></icon_import_outlined>
          </template>
          {{ $t('parameter.export_notes') }}
        </el-button>
        <UploaderRemark
          :upload-path="`/datasource/uploadDsSchema/${info.id}`"
          @upload-finished="init"
        ></UploaderRemark>
      </div>
    </div>
    <div class="content">
      <div class="side-list">
        <div class="select-table_top">
          {{ $t('ds.tables') }}

          <el-tooltip
            effect="dark"
            offset="10"
            :content="$t('ds.form.choose_tables')"
            placement="top"
          >
            <el-button style="margin-right: -4px" @click="handleSelectTableList" text>
              <el-icon size="18">
                <icon_form_outlined></icon_form_outlined>
              </el-icon>
            </el-button>
          </el-tooltip>
        </div>
        <el-input
          v-model="keywords"
          clearable
          style="width: 232px"
          :placeholder="$t('datasource.search')"
        >
          <template #prefix>
            <el-icon>
              <icon_searchOutline_outlined class="svg-icon" />
            </el-icon>
          </template>
        </el-input>

        <div v-loading="initLoading" class="list-content">
          <el-scrollbar v-if="tableListWithSearch.length">
            <div
              v-for="ele in tableListWithSearch"
              :key="ele.table_name"
              :draggable="activeRelationship && !tableName.includes(ele.id)"
              class="model"
              :class="[
                currentTable.table_name === ele.table_name && 'isActive',
                tableName.includes(ele.id) && activeRelationship && 'disabled-table',
              ]"
              :title="ele.table_name"
              @dragstart="($event: any) => singleDragStartD($event, ele)"
              @dragend="singleDragEnd"
              @click="clickTable(ele)"
            >
              <el-icon size="16">
                <icon_form_outlined></icon_form_outlined>
              </el-icon>
              <span class="name">{{ ele.table_name }}</span>
            </div>
          </el-scrollbar>
          <EmptyBackground
            v-if="!!keywords && !tableListWithSearch.length"
            :description="$t('datasource.relevant_content_found')"
            img-type="tree"
            style="width: 100%"
          />
          <div v-else-if="!initLoading && !tableListWithSearch.length" class="no-data">
            <div class="no-data-msg">
              <div>
                {{ $t('datasource.no_table') }}
              </div>
              <el-button type="primary" link @click="handleSelectTableList">
                {{ $t('datasource.go_add') }}
              </el-button>
            </div>
          </div>
        </div>
        <div class="table-relationship">
          <div :class="activeRelationship && 'active'" class="btn" @click="handleRelationship">
            <el-icon size="16">
              <icon_mindnote_outlined></icon_mindnote_outlined>
            </el-icon>
            {{ t('training.table_relationship_management') }}
          </div>
        </div>
      </div>

      <div v-if="activeRelationship" class="relationship-content">
        <div class="title">{{ t('training.table_relationship_management') }}</div>
        <div class="content">
          <TableRelationship
            :id="info.id"
            :dragging="isDrag"
            @get-table-name="getTableName"
          ></TableRelationship>
        </div>
      </div>

      <div
        v-if="currentTable.table_name && !activeRelationship"
        v-loading="loading"
        class="info-table"
      >
        <div class="table-name">
          <div class="name">{{ currentTable.table_name }}</div>
          <div class="notes">
            {{ $t('about.remark') }}:
            <span :title="currentTable.custom_comment" class="field-notes">{{
              currentTable.custom_comment || '-'
            }}</span>

            <el-tooltip :offset="14" effect="dark" :content="$t('datasource.edit')" placement="top">
              <el-icon style="margin-left: 8px; cursor: pointer" size="16" @click="editTable">
                <edit></edit>
              </el-icon>
            </el-tooltip>
          </div>
        </div>

        <div class="table-content">
          <div class="btn-select">
            <el-button
              :class="[btnSelect === 'd' && 'is-active']"
              text
              @click="btnSelectClick('d')"
            >
              {{ t('ds.table_schema') }}
            </el-button>
            <el-button
              :class="[btnSelect === 'q' && 'is-active']"
              text
              @click="btnSelectClick('q')"
            >
              {{ t('ds.preview') }}
            </el-button>
          </div>
          <div v-if="btnSelect === 'd'" class="field-name">
            <el-input
              v-model="fieldName"
              style="width: 240px"
              :placeholder="t('dashboard.search')"
              autocomplete="off"
              clearable
              @input="fieldNameSearch"
            />
            <el-button
              v-if="ds.type !== 'excel'"
              :icon="Refresh"
              style="margin-left: 12px"
              @click="syncFields()"
            >
              {{ t('ds.sync_fields') }}
            </el-button>
          </div>

          <div
            v-if="!loading"
            class="preview-or-schema"
            :class="btnSelect === 'q' && 'overflow-preview'"
          >
            <div v-if="btnSelect === 'd'" class="table-content_preview">
              <el-table
                row-class-name="hover-icon_edit"
                :data="fieldListComputed"
                style="width: 100%"
              >
                <el-table-column
                  prop="field_name"
                  :label="t('datasource.field_name')"
                  width="180"
                />
                <el-table-column
                  prop="field_type"
                  :label="t('datasource.field_type')"
                  width="180"
                />
                <el-table-column
                  prop="field_comment"
                  :label="t('datasource.field_original_notes')"
                />
                <el-table-column :label="t('datasource.field_notes_1')">
                  <template #default="scope">
                    <div class="field-comment">
                      <span :title="scope.row.custom_comment" class="notes-in_table">{{
                        scope.row.custom_comment
                      }}</span>
                      <el-tooltip
                        :offset="14"
                        effect="dark"
                        :content="$t('datasource.edit')"
                        placement="top"
                      >
                        <el-icon class="action-btn" size="16" @click="editField(scope.row)">
                          <edit></edit>
                        </el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column :label="t('datasource.enabled_status')" width="180">
                  <template #default="scope">
                    <div style="display: flex; align-items: center">
                      <el-switch
                        v-model="scope.row.checked"
                        size="small"
                        @change="changeStatus(scope.row)"
                      />
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div v-if="pageInfo.total && btnSelect === 'd'" class="pagination-container">
              <el-pagination
                v-model:current-page="pageInfo.currentPage"
                v-model:page-size="pageInfo.pageSize"
                :page-sizes="[10, 20, 30]"
                :background="true"
                layout="total, sizes, prev, pager, next, jumper"
                :total="pageInfo.total"
                @size-change="handleSizeChange"
                @current-change="handleCurrentChange"
              />
            </div>
            <template v-if="btnSelect === 'q'">
              <div class="preview-num">
                {{ t('ds.pieces_in_total', { msg: total, ms: showNum }) }}
              </div>
              <div class="table-container">
                <el-table :data="previewData.data" style="width: 100%; height: 100%">
                  <el-table-column
                    v-for="(c, index) in previewData.fields"
                    :key="index"
                    :prop="c"
                    :label="c"
                    min-width="150"
                    :render-header="renderHeader"
                  />
                </el-table>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
  <el-dialog
    v-model="tableDialog"
    :title="t('datasource.table_notes')"
    width="600"
    :destroy-on-close="true"
    :close-on-click-modal="false"
    modal-class="notes-dialog"
    @closed="closeTable"
  >
    <el-input
      v-model="tableComment"
      :placeholder="$t('datasource.please_enter')"
      :autosize="{ minRows: 3.64, maxRows: 11.095 }"
      type="textarea"
      clearable
    />
    <div style="display: flex; justify-content: flex-end; margin-top: 20px">
      <el-button secondary @click="closeTable">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" @click="saveTable">{{ t('common.save') }}</el-button>
    </div>
  </el-dialog>

  <el-dialog
    v-model="fieldDialog"
    :title="t('datasource.field_notes')"
    width="600"
    :destroy-on-close="true"
    :close-on-click-modal="false"
    modal-class="notes-dialog"
    @closed="closeField"
  >
    <el-input
      v-model="fieldComment"
      :placeholder="$t('datasource.please_enter')"
      :autosize="{ minRows: 3.64, maxRows: 11.095 }"
      clearable
      type="textarea"
    />
    <div style="display: flex; justify-content: flex-end; margin-top: 20px">
      <el-button secondary @click="closeField">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" @click="saveField">{{ t('common.save') }}</el-button>
    </div>
  </el-dialog>
  <ParamsForm ref="paramsFormRef" @refresh="refresh"></ParamsForm>
</template>

<style lang="less" scoped>
.data-table {
  height: 100%;
  .info {
    height: 56px;
    width: 100%;
    padding-left: 20px;
    display: flex;
    align-items: center;
    font-family: PingFang SC;
    font-weight: 400;
    font-size: 14px;
    line-height: 22px;
    color: #646a73;
    border-bottom: 1px solid #1f232926;
    position: relative;

    .ed-button.is-text {
      height: 22px;
      line-height: 22px;
      color: #646a73;

      &:hover {
        background: var(--ed-color-primary-1a, #1cba901a);
        color: var(--ed-color-primary);
      }
      &:active {
        color: var(--ed-color-primary-dark-2);
        background: var(--ed-color-primary-33, #1cba9033);
      }
    }

    .export-remark {
      position: absolute;
      right: 24px;
      top: 12px;
    }

    .name {
      color: #1f2329;
      margin-left: 4px;
    }
  }
  .content {
    height: calc(100% - 56px);
    position: relative;
    .side-list {
      width: 280px;
      padding: 8px 16px;
      height: 100%;
      border-right: 1px solid #1f232926;
      .table-relationship {
        height: 56px;
        width: 100%;
        display: flex;
        align-items: center;
        margin-top: 20px;
        position: relative;

        &::after {
          content: '';
          width: calc(100% + 32px);
          position: absolute;
          left: -16px;
          background-color: #1f232926;
          top: 0;
          height: 1px;
        }

        .btn {
          width: 248px;
          height: 32px;
          cursor: pointer;
          border-radius: 6px;
          display: flex;
          align-items: center;
          padding-left: 8px;
          .ed-icon {
            color: #646a73;
            margin-right: 8px;
          }

          &.active {
            color: var(--ed-color-primary);
            .ed-icon {
              color: var(--ed-color-primary);
            }
            background-color: var(--ed-color-primary-1a);
          }
        }
      }
      .select-table_top {
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px;
        font-weight: 500;

        .ed-icon {
          cursor: pointer;
          color: var(--ed-color-primary);
        }
      }

      .ed-input {
        margin: 8px;
      }

      .list-content {
        height: calc(100% - 156px);
        .no-result {
          margin-top: 72px;
          font-weight: 400;
          font-size: 14px;
          line-height: 22px;
          text-align: center;
          color: #646a73;
        }
        .model {
          width: 100%;
          height: 32px;
          display: flex;
          align-items: center;
          padding-left: 8px;
          border-radius: 4px;
          cursor: pointer;

          &:not(:last-child) {
            margin-bottom: 2px;
          }

          &.disabled-table {
            background: #dee0e3 !important;
            color: #646a73;
            cursor: not-allowed;
          }

          .name {
            margin-left: 8px;
            font-weight: 500;
            font-size: 14px;
            line-height: 22px;
            max-width: 80%;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }
          &:hover {
            background: #1f23291a;
          }

          &.isActive {
            background: var(--ed-color-primary-1a, #1cba901a);
            color: var(--ed-color-primary);
          }
        }
      }

      .no-data {
        height: 100%;
        text-align: center;
        display: flex;
        align-items: center;
        width: 100%;
        .no-data-msg {
          display: inline;
          width: 100%;
          color: var(--ed-text-color-secondary);
          font-size: var(--ed-font-size-base);
        }
      }
    }
    .relationship-content {
      position: absolute;
      right: 0;
      top: 0;
      width: calc(100% - 280px);
      height: 100%;

      .content {
        height: calc(100% - 56px);
        width: 100%;
      }

      .title {
        height: 56px;
        padding-left: 24px;
        line-height: 56px;
        font-weight: 500;
        font-size: 16px;
        border-bottom: 1px solid #1f232926;
      }
    }
    .info-table {
      position: absolute;
      right: 0;
      top: 0;
      width: calc(100% - 280px);
      height: 100%;
      .table-name {
        height: 80px;
        padding: 16px 0 0 24px;
        border-bottom: 1px solid #1f232926;

        .name {
          font-weight: 500;
          font-size: 16px;
          line-height: 24px;
        }

        .ed-icon {
          position: relative;
          cursor: pointer;
          margin-top: 4px;
          margin-left: 8px;

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

        .notes {
          font-weight: 400;
          font-size: 14px;
          line-height: 22px;
          color: #646a73;
          display: flex;
          align-items: center;

          .field-notes {
            display: inline-block;
            max-width: calc(100% - 75px);
            text-overflow: ellipsis;
            white-space: nowrap;
            overflow: hidden;
          }
        }
      }

      .table-content {
        padding: 16px 24px;
        height: calc(100% - 80px);
        position: relative;

        .field-name {
          position: absolute;
          right: 24px;
          top: 16px;
          display: flex;
        }

        .btn-select {
          height: 32px;
          padding-left: 4px;
          padding-right: 4px;
          display: inline-flex;
          background: #ffffff;
          align-items: center;
          border: 1px solid #d0d3d6;
          border-radius: 4px;

          .is-active {
            background: var(--ed-color-primary-1a, #1cba901a);
          }

          .ed-button:not(.is-active) {
            color: #1f2329;
          }
          .ed-button.is-text {
            height: 24px;
            width: auto;
            padding: 0 8px;
            line-height: 24px;
          }
          .ed-button + .ed-button {
            margin-left: 4px;
          }
        }

        .preview-or-schema {
          margin-top: 16px;
          height: calc(100% - 50px);

          .table-content_preview {
            max-height: calc(100% - 50px);
            overflow-y: auto;
            margin-bottom: 16px;
          }

          .pagination-container {
            display: flex;
            justify-content: flex-end;
          }

          .hover-icon_edit:hover {
            .ed-icon {
              display: block;
            }
          }

          .field-comment {
            display: flex;
            align-items: center;
            min-height: 24px;
            .notes-in_table {
              max-width: 100%;
              display: -webkit-box;
              max-height: 66px;
              -webkit-box-orient: vertical;
              -webkit-line-clamp: 3; /* 限制行数为3 */
              overflow: hidden;
              text-overflow: ellipsis;
            }

            .ed-icon {
              position: relative;
              cursor: pointer;
              margin-left: 8px;
              display: none;
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

          .preview-num {
            margin: 12px 0;
            font-weight: 400;
            font-size: 14px;
            line-height: 22px;
            color: #646a73;
          }

          .table-container {
            width: 100%;
            height: calc(100% - 46px);
          }
        }
      }
    }
  }
}
</style>

<style lang="less">
.notes-dialog {
  .ed-textarea__inner {
    line-height: 22px;
  }
}
</style>
