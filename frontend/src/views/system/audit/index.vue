<script lang="ts" setup>
import { onMounted, reactive, ref } from 'vue'
import icon_export_outlined from '@/assets/svg/icon_export_outlined.svg'
import { formatTimestamp } from '@/utils/date'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { useI18n } from 'vue-i18n'
import { convertFilterText, FilterText } from '@/components/filter-text'
import { DrawerMain } from '@/components/drawer-main'
import iconFilter from '@/assets/svg/icon-filter_outlined.svg'
import { audit } from '@/api/audit.ts'
import { workspaceList } from '@/api/workspace.ts'
import { userApi } from '@/api/auth.ts'
import icon_success from '@/assets/svg/icon_success.svg'
import icon_error from '@/assets/svg/icon_error.svg'
import icon_issue from '@/assets/svg/icon_issue.svg'

const { t } = useI18n()
const multipleSelectionAll = ref<any[]>([])
const keywords = ref('')
const oldKeywords = ref('')
const searchLoading = ref(false)
const drawerMainRef = ref()

onMounted(() => {
  search()
  initWorkspace()
  initUsers()
  initOptions()
})
const multipleTableRef = ref()
const fieldList = ref<any>([])
const pageInfo = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0,
})

const curErrorInfo = ref()

const state = reactive<any>({
  conditions: [],
  filterTexts: [],
})

const exportExcel = () => {
  ElMessageBox.confirm(t('audit.all_236_terms', { msg: pageInfo.total }), {
    confirmButtonType: 'primary',
    confirmButtonText: t('audit.export'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    searchLoading.value = true
    audit
      .export2Excel(configParams())
      .then((res) => {
        const blob = new Blob([res], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        const link = document.createElement('a')
        link.href = URL.createObjectURL(blob)
        link.download = `${t('audit.system_log')}.xlsx`
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
      .finally(() => {
        searchLoading.value = false
      })
  })
}

const toggleRowLoading = ref(false)

const configParams = () => {
  let str = ''
  let str_conditions = ''
  if (keywords.value) {
    str += `name=${keywords.value}`
  }

  state.conditions.forEach((ele: any) => {
    str_conditions = ''
    ele.value.forEach((itx: any) => {
      str_conditions += str_conditions ? `__${itx}` : `${ele.field}=${itx}`
    })
    str += str ? `&${str_conditions}` : `${str_conditions}`
  })

  if (str.length) {
    str = `?${str}`
  }
  return str
}

const search = () => {
  searchLoading.value = true
  oldKeywords.value = keywords.value
  audit
    .getList(pageInfo.currentPage, pageInfo.pageSize, configParams())
    .then((res) => {
      toggleRowLoading.value = true
      fieldList.value = res.data
      pageInfo.total = res.total_count
      searchLoading.value = false
    })
    .finally(() => {
      searchLoading.value = false
    })
}

const handleSizeChange = (val: number) => {
  pageInfo.currentPage = 1
  pageInfo.pageSize = val
  search()
}

const handleCurrentChange = (val: number) => {
  pageInfo.currentPage = val
  search()
}
const rowInfoDialog = ref(false)

const onErrorInfoOpen = (info: string) => {
  rowInfoDialog.value = true
  curErrorInfo.value = info
}

const onErrorInfoClose = () => {
  rowInfoDialog.value = false
}
const filterOption = ref<any[]>([
  {
    type: 'tree-select',
    option: [],
    field: 'opt_type_list',
    title: t('audit.operation_type'),
    operate: 'in',
    property: { placeholder: t('common.empty') + t('audit.operation_type') },
  },
  {
    type: 'select',
    option: [],
    field: 'uid_list',
    title: t('audit.operation_user_name'),
    operate: 'in',
    property: { placeholder: t('common.empty') + t('audit.operation_user_name') },
  },
  {
    type: 'select',
    option: [],
    field: 'oid_list',
    title: t('audit.operation_user_name'),
    operate: 'in',
    property: { placeholder: t('common.empty') + t('audit.oid_name') },
  },
  {
    type: 'enum',
    option: [
      { id: 'success', name: t('audit.success') },
      { id: 'failed', name: t('audit.failed') },
    ],
    field: 'log_status',
    title: t('user.user_status'),
    operate: 'in',
  },
  {
    type: 'time',
    option: [],
    field: 'time_range',
    title: t('audit.opt_time'),
    operate: 'between',
    property: {
      showType: 'datetimerange',
      format: 'YYYY-MM-DD HH:mm:ss',
      valueFormat: 'x',
    },
  },
])

const fillFilterText = () => {
  const textArray = state.conditions?.length
    ? convertFilterText(state.conditions, filterOption.value)
    : []
  state.filterTexts = [...textArray]
  Object.assign(state.filterTexts, textArray)
}
const searchCondition = (conditions: any) => {
  state.conditions = conditions
  fillFilterText()
  search()
  drawerMainClose()
}

const clearFilter = (params?: number) => {
  let index = params ? params : 0
  if (isNaN(index)) {
    state.filterTexts = []
  } else {
    state.filterTexts.splice(index, 1)
  }
  drawerMainRef.value.clearFilter(index)
}

const drawerMainOpen = async () => {
  drawerMainRef.value.init()
}

const drawerMainClose = () => {
  drawerMainRef.value.close()
}
const initWorkspace = () => {
  workspaceList().then((res) => {
    filterOption.value[2].option = [...res]
  })
}

const initUsers = () => {
  userApi.pager(1, 10000).then((res: any) => {
    filterOption.value[1].option = [{ id: 1, name: 'Administrator' }, ...res.items]
  })
}

const initOptions = () => {
  audit.getOptions().then((res: any) => {
    filterOption.value[0].option = [...res]
  })
}
</script>

<template>
  <div v-loading="searchLoading" class="professional">
    <div class="tool-left">
      <span class="page-title">{{ $t('audit.system_log') }}</span>
      <div class="tool-row">
        <el-button secondary @click="exportExcel">
          <template #icon>
            <icon_export_outlined />
          </template>
          {{ $t('professional.export_all') }}
        </el-button>
        <el-button class="no-margin" secondary @click="drawerMainOpen">
          <template #icon>
            <iconFilter></iconFilter>
          </template>
          {{ $t('user.filter') }}
        </el-button>
      </div>
    </div>
    <div
      v-if="!searchLoading"
      class="table-content"
      :class="multipleSelectionAll?.length && 'show-pagination_height'"
    >
      <filter-text
        :total="pageInfo.total"
        :filter-texts="state.filterTexts"
        @clear-filter="clearFilter"
      />
      <div class="preview-or-schema">
        <el-table ref="multipleTableRef" :data="fieldList" style="width: 100%">
          <el-table-column prop="word" :label="$t('audit.operation_type')" width="140">
            <template #default="scope">
              {{ scope.row.operation_type_name }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('audit.operation_details')" min-width="200"
            ><template #default="scope">
              {{ scope.row.operation_detail_info }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('audit.operation_user_name')" min-width="120"
            ><template #default="scope">
              {{ scope.row.user_name }}
            </template>
          </el-table-column>
          <el-table-column prop="word" :label="$t('audit.oid_name')" width="120">
            <template #default="scope">
              {{ scope.row.oid_name }}
            </template>
          </el-table-column>
          <el-table-column prop="word" :label="$t('audit.operation_status')" width="100">
            <template #default="scope">
              <div style="display: flex; align-items: center">
                <el-icon size="16" style="margin-right: 4px">
                  <icon_success v-if="scope.row.operation_status === 'success'"></icon_success>
                  <icon_error v-if="scope.row.operation_status === 'failed'"></icon_error>
                </el-icon>
                {{ scope.row.operation_status_name }}
                <el-icon
                  v-if="scope.row.operation_status === 'failed'"
                  size="16"
                  style="margin-left: 4px; cursor: pointer"
                  @click="onErrorInfoOpen(scope.row.error_message)"
                >
                  <icon_issue></icon_issue>
                </el-icon>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="word" :label="$t('audit.ip_address')" width="140">
            <template #default="scope">
              {{ scope.row.ip_address }}
            </template>
          </el-table-column>
          <el-table-column prop="create_time" sortable :label="$t('audit.create_time')" width="180">
            <template #default="scope">
              <span>{{ formatTimestamp(scope.row.create_time, 'YYYY-MM-DD HH:mm:ss') }}</span>
            </template>
          </el-table-column>
          <template #empty>
            <EmptyBackground
              v-if="!oldKeywords && !fieldList.length"
              :description="$t('audit.no_log')"
              img-type="noneWhite"
            />

            <EmptyBackground
              v-if="!!oldKeywords && !fieldList.length"
              :description="$t('datasource.relevant_content_found')"
              img-type="tree"
            />
          </template>
        </el-table>
      </div>
    </div>

    <div v-if="fieldList.length" class="pagination-container">
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
  </div>
  <el-drawer
    v-model="rowInfoDialog"
    :title="$t('audit.failed_info')"
    destroy-on-close
    :before-close="onErrorInfoClose"
    direction="btt"
    size="80%"
    modal-class="professional-term_drawer"
  >
    <div style="width: 100%; height: 100%">
      {{ curErrorInfo }}
    </div>
  </el-drawer>
  <drawer-main
    ref="drawerMainRef"
    :filter-options="filterOption"
    @trigger-filter="searchCondition"
  />
</template>

<style lang="less" scoped>
.no-margin {
  margin: 0;
}
.professional {
  height: 100%;
  position: relative;

  .datasource-yet {
    padding-bottom: 0;
    height: auto;
    padding-top: 200px;
  }

  :deep(.ed-table__cell) {
    cursor: pointer;
  }

  .tool-left {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;

    .page-title {
      font-weight: 500;
      font-size: 20px;
      line-height: 28px;
    }
    .tool-row {
      display: flex;
      align-items: center;
      flex-direction: row;
      gap: 8px;
    }
  }

  .pagination-container {
    display: flex;
    justify-content: end;
    align-items: center;
    margin-top: 16px;
  }

  .table-content {
    max-height: calc(100% - 104px);
    overflow-y: auto;

    &.show-pagination_height {
      max-height: calc(100% - 165px);
    }

    .preview-or-schema {
      .field-comment_d {
        display: flex;
        align-items: center;
        min-height: 24px;
      }
      .notes-in_table {
        max-width: 100%;
        display: -webkit-box;
        max-height: 66px;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 3; /* 限制行数为3 */
        overflow: hidden;
        text-overflow: ellipsis;
        word-break: break-word;
      }
      .ed-icon {
        color: #646a73;
      }

      .user-status-container {
        display: flex;
        align-items: center;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        height: 24px;

        .ed-icon {
          margin-left: 8px;
        }
      }

      .field-comment {
        height: 24px;

        .ed-icon {
          position: relative;
          cursor: pointer;
          margin-top: 4px;

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

          &:not(.not-allow):hover {
            &::after {
              display: block;
            }
          }

          &.not-allow {
            cursor: not-allowed;
          }
        }
        .ed-icon + .ed-icon {
          margin-left: 12px;
        }
      }

      .preview-num {
        margin: 12px 0;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        color: #646a73;
      }
    }
  }

  .bottom-select {
    position: absolute;
    height: 64px;
    width: calc(100% + 48px);
    left: -24px;
    bottom: -16px;
    border-top: 1px solid #1f232926;
    display: flex;
    background-color: #fff;
    align-items: center;
    padding-left: 24px;
    background-color: #fff;
    z-index: 10;

    .danger-button {
      border: 1px solid var(--ed-color-danger);
      color: var(--ed-color-danger);
      border-radius: var(--ed-border-radius-base);
      min-width: 80px;
      height: 32px;
      line-height: 32px;
      text-align: center;
      cursor: pointer;
      margin: 0 16px;
      background-color: transparent;
    }

    .primary-button {
      border: 1px solid var(--ed-color-primary);
      color: var(--ed-color-primary);
      border-radius: var(--ed-border-radius-base);
      min-width: 80px;
      height: 32px;
      line-height: 32px;
      text-align: center;
      cursor: pointer;
      margin: 0 16px;
      background-color: transparent;
    }

    .selected {
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;
      color: #646a73;
      margin-right: 12px;
    }
  }
}
</style>
<style lang="less">
.professional-term_drawer {
  .ed-form-item--label-top .ed-form-item__label {
    margin-bottom: 4px;
  }

  .ed-form-item__label {
    color: #646a73;
  }

  .content {
    width: 100%;
    line-height: 22px;
    word-break: break-all;
  }
}

.professional-add_drawer {
  .no-error.no-error {
    .ed-form-item__error {
      display: none;
    }
    margin-bottom: 16px;
  }
  .ed-textarea__inner {
    line-height: 22px;
  }

  .ed-form-item__label:has(.btn) {
    padding-right: 0;
    width: 100%;
  }

  .scrollbar-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-right: 4px;
    margin-bottom: 8px;
  }

  .synonyms-list {
    position: absolute;
    left: 0;
    top: 0;
    width: calc(100% + 4px);
    height: calc(100vh - 390px);
  }

  .btn {
    margin-left: auto;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 4px;
    border-radius: 6px;
    margin-right: -4px;
    cursor: pointer;

    &:hover {
      background-color: #1f23291a;
    }
  }
}
</style>
