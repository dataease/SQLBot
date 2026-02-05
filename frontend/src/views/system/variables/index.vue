<script lang="ts" setup>
import { ref, onMounted, reactive, unref, nextTick } from 'vue'
import { variablesApi } from '@/api/variables'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import IconOpeEdit from '@/assets/svg/icon_edit_outlined.svg'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { useI18n } from 'vue-i18n'
import { cloneDeep } from 'lodash-es'

interface Form {
  id?: string | null
  name: string | null
  var_type: string
  value: any[]
}

const { t } = useI18n()
const multipleSelectionAll = ref<any[]>([])
const keywords = ref('')
const oldKeywords = ref('')
const searchLoading = ref(false)

const selectable = (row: any) => {
  return ![1, 2, 3].includes(row.id)
}
onMounted(() => {
  search()
})
const dialogFormVisible = ref<boolean>(false)
const multipleTableRef = ref()
const isIndeterminate = ref(true)
const checkAll = ref(false)
const fieldList = ref<any>([])
const pageInfo = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0,
})

const var_type = {
  text: 'model.text',
  number: 'model.number',
  datetime: 'variables.date',
} as Record<string, unknown>

const dialogTitle = ref('')
const defaultForm = {
  id: null,
  name: null,
  var_type: 'text',
  value: [''],
}
const pageForm = ref<Form>(cloneDeep(defaultForm))

const cancelDelete = () => {
  handleToggleRowSelection(false)
  multipleSelectionAll.value = []
  checkAll.value = false
  isIndeterminate.value = false
}
const deleteBatchUser = () => {
  ElMessageBox.confirm(t('embedded.delete_10_apps', { msg: multipleSelectionAll.value.length }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    variablesApi.delete(multipleSelectionAll.value.map((ele) => ele.id)).then(() => {
      ElMessage({
        type: 'success',
        message: t('dashboard.delete_success'),
      })
      multipleSelectionAll.value = []
      search()
    })
  })
}
const deleteHandler = (row: any) => {
  if (row.type === 'system') return

  ElMessageBox.confirm(t('embedded.delete', { msg: row.name }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    variablesApi.delete([row.id]).then(() => {
      multipleSelectionAll.value = multipleSelectionAll.value.filter((ele) => row.id !== ele.id)
      ElMessage({
        type: 'success',
        message: t('dashboard.delete_success'),
      })
      search()
    })
  })
}
const handleSelectionChange = (val: any[]) => {
  if (toggleRowLoading.value) return
  const arr = fieldList.value.filter(selectable)
  const ids = arr.map((ele: any) => ele.id)
  multipleSelectionAll.value = [
    ...multipleSelectionAll.value.filter((ele: any) => !ids.includes(ele.id)),
    ...val,
  ]
  isIndeterminate.value = !(val.length === 0 || val.length === arr.length)
  checkAll.value = val.length === arr.length
}
const handleCheckAllChange = (val: any) => {
  isIndeterminate.value = false
  handleSelectionChange(val ? fieldList.value.filter(selectable) : [])
  if (val) {
    handleToggleRowSelection()
  } else {
    multipleTableRef.value.clearSelection()
  }
}

const toggleRowLoading = ref(false)

const handleToggleRowSelection = (check: boolean = true) => {
  toggleRowLoading.value = true
  const arr = fieldList.value.filter(selectable)
  let i = 0
  const ids = multipleSelectionAll.value.map((ele: any) => ele.id)
  for (const key in arr) {
    if (ids.includes((arr[key] as any).id)) {
      i += 1
      multipleTableRef.value.toggleRowSelection(arr[key], check)
    }
  }
  toggleRowLoading.value = false
  checkAll.value = i === arr.length
  isIndeterminate.value = !(i === 0 || i === arr.length)
}

const search = ($event: any = {}) => {
  if ($event?.isComposing) {
    return
  }
  searchLoading.value = true
  let data = keywords.value ? { name: keywords.value } : {}
  variablesApi
    .listPage(pageInfo.currentPage, pageInfo.pageSize, data)
    .then((res) => {
      toggleRowLoading.value = true
      fieldList.value = res.items.map((ele: any) => ({
        ...ele,
        value: ele.type === 'system' ? t('variables.built_in') : ele.value,
      }))
      pageInfo.total = res.total
      searchLoading.value = false
      nextTick(() => {
        handleToggleRowSelection()
      })
    })
    .finally(() => {
      oldKeywords.value = keywords.value
      searchLoading.value = false
    })
}

const deleteValues = (index: number) => {
  if (index === 0 && pageForm.value.value.length === 1) return
  pageForm.value.value.splice(index, 1)
}

const termFormRef = ref()
const validateValue = (_: any, value: any, callback: any) => {
  const { var_type } = pageForm.value
  if (var_type === 'text') {
    if (value === '') {
      callback(
        new Error(t('datasource.please_enter') + t('common.empty') + t('variables.variable_value'))
      )
    } else {
      callback()
    }
    return
  }
  if (value.some((ele: any) => ele === '')) {
    callback(
      new Error(
        t('datasource.please_enter') +
          t('common.empty') +
          t(pageForm.value.var_type === 'number' ? 'model.number' : 'variables.date')
      )
    )
  } else {
    callback()
  }
}
const rules = {
  name: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('embedded.application_name'),
    },
  ],
  value: [
    {
      required: true,
      validator: validateValue,
      trigger: 'blur',
    },
  ],
}

const varTypeChange = (val: any) => {
  if (val === 'text') {
    pageForm.value.value = ['']
    return
  }
  pageForm.value.value = ['', '']
}

const saveHandler = () => {
  termFormRef.value.validate((res: any) => {
    if (res) {
      const obj = unref(pageForm)
      if (obj.id === '' || obj.id === null) {
        delete obj.id
      }
      variablesApi.save(obj).then(() => {
        ElMessage({
          type: 'success',
          message: t('common.save_success'),
        })
        search()
        onFormClose()
      })
    }
  })
}

const editHandler = (row: any) => {
  pageForm.value.id = null
  if (row) {
    if (row.type === 'system') return
    const { id, name, var_type, value } = row
    pageForm.value.id = id
    pageForm.value.name = name
    pageForm.value.var_type = var_type
    pageForm.value.value = value
  }
  dialogTitle.value = row?.id ? t('variables.edit_variable') : t('variables.add_variable')
  dialogFormVisible.value = true
}

const onFormClose = () => {
  pageForm.value = cloneDeep(defaultForm)
  dialogFormVisible.value = false
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
</script>

<template>
  <div v-loading="searchLoading" class="variables">
    <div class="tool-left">
      <span class="page-title">{{ t('variables.system_variables') }}</span>
      <div>
        <el-input
          v-model="keywords"
          style="width: 240px; margin-right: 12px"
          :placeholder="$t('variables.search_variables')"
          clearable
          @keydown.enter.exact.prevent="search"
        >
          <template #prefix>
            <el-icon>
              <icon_searchOutline_outlined />
            </el-icon>
          </template>
        </el-input>

        <el-button type="primary" @click="editHandler(null)">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('variables.add_variable') }}
        </el-button>
      </div>
    </div>
    <div
      v-if="!searchLoading"
      class="table-content"
      :class="multipleSelectionAll.length && 'show-pagination_height'"
    >
      <template v-if="!oldKeywords && !fieldList.length">
        <EmptyBackground
          class="datasource-yet"
          :description="$t('variables.no_variables_yet')"
          img-type="noneWhite"
        />
      </template>
      <div v-else class="preview-or-schema">
        <el-table
          ref="multipleTableRef"
          :data="fieldList"
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
          <el-table-column :selectable="selectable" type="selection" width="55" />
          <el-table-column prop="name" :label="$t('variables.variable_name')">
            <template #default="scope">
              <div style="display: flex; align-items: center" :title="scope.row.name">
                <div class="ellipsis" style="max-width: calc(100% - 60px); width: fit-content">
                  {{ scope.row.name }}
                </div>
                <div v-if="scope.row.type === 'system'" class="system-flag">
                  {{ t('variables.system') }}
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column width="160" prop="var_type" :label="$t('variables.variable_type')">
            <template #default="scope">
              {{ t(var_type[scope.row.var_type] as string) }}
            </template>
          </el-table-column>
          <el-table-column
            prop="value"
            width="420"
            :label="$t('variables.variable_value')"
            show-overflow-tooltip
          />
          <el-table-column fixed="right" width="80" :label="t('ds.actions')">
            <template #default="scope">
              <div class="field-comment">
                <el-tooltip
                  :offset="14"
                  effect="dark"
                  :content="$t('datasource.edit')"
                  placement="top"
                >
                  <el-icon
                    class="action-btn"
                    :class="scope.row.type === 'system' && 'not-allow'"
                    size="16"
                    @click="editHandler(scope.row)"
                  >
                    <IconOpeEdit></IconOpeEdit>
                  </el-icon>
                </el-tooltip>
                <el-tooltip
                  :offset="14"
                  effect="dark"
                  :content="$t('dashboard.delete')"
                  placement="top"
                >
                  <el-icon
                    class="action-btn"
                    :class="scope.row.type === 'system' && 'not-allow'"
                    size="16"
                    @click="deleteHandler(scope.row)"
                  >
                    <IconOpeDelete></IconOpeDelete>
                  </el-icon>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <EmptyBackground
              v-if="!oldKeywords && !fieldList.length"
              :description="$t('embedded.no_application')"
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
    <div v-if="multipleSelectionAll.length" class="bottom-select">
      <el-checkbox
        v-model="checkAll"
        :indeterminate="isIndeterminate"
        @change="handleCheckAllChange"
      >
        {{ $t('datasource.select_all') }}
      </el-checkbox>

      <button class="danger-button" @click="deleteBatchUser">{{ $t('dashboard.delete') }}</button>

      <span class="selected">{{
        $t('user.selected_2_items', { msg: multipleSelectionAll.length })
      }}</span>

      <el-button text @click="cancelDelete">
        {{ $t('common.cancel') }}
      </el-button>
    </div>
  </div>

  <el-drawer
    v-model="dialogFormVisible"
    :title="dialogTitle"
    modal-class="variables-config"
    destroy-on-close
    size="600px"
    :before-close="onFormClose"
  >
    <el-form
      ref="termFormRef"
      :model="pageForm"
      label-width="180px"
      label-position="top"
      :rules="rules"
      class="form-content_error"
      @submit.prevent
    >
      <el-form-item prop="name" :label="t('variables.variable_name')">
        <el-input
          v-model="pageForm.name"
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('variables.variable_name')
          "
          autocomplete="off"
          maxlength="50"
          clearable
        />
      </el-form-item>
      <el-form-item :label="t('variables.variable_type')">
        <el-radio-group
          :disabled="!!pageForm.id"
          @change="varTypeChange"
          v-model="pageForm.var_type"
        >
          <el-radio value="text">{{ $t('model.text') }}</el-radio>
          <el-radio value="number">
            {{ $t('model.number') }}
          </el-radio>
          <el-radio value="datetime">
            {{ $t('variables.date') }}
          </el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item v-if="pageForm.var_type === 'text'">
        <template #label>
          <div style="display: flex; align-items: center; height: 22px">
            <span class="text">{{ t('variables.variable_value') }}</span>
            <span class="btn" @click="pageForm.value.push('')">
              <el-icon style="margin-right: 4px" size="16">
                <icon_add_outlined></icon_add_outlined>
              </el-icon>
              {{ $t('model.add') }}
            </span>
          </div>
        </template>
        <div class="value-list">
          <el-form-item
            :key="index"
            v-for="(_, index) in pageForm.value"
            :prop="'value.' + index"
            :rules="{
              required: true,
              message: $t('variables.enter_variable_value'),
              trigger: 'blur',
            }"
          >
            <div class="item">
              <el-input
                v-model="pageForm.value[index]"
                :placeholder="$t('variables.enter_variable_value')"
                autocomplete="off"
                maxlength="50"
                clearable
              />
              <el-icon
                class="action-btn"
                :class="index === 0 && pageForm.value.length === 1 && 'not-allow'"
                size="16"
                @click="deleteValues(index)"
              >
                <IconOpeDelete></IconOpeDelete>
              </el-icon>
            </div>
          </el-form-item>
        </div>
      </el-form-item>
      <el-form-item prop="value" v-else :label="t('variables.variable_value')">
        <div class="value-number_date">
          <template v-if="pageForm.var_type === 'number'">
            <el-input
              v-model.number="pageForm.value[0]"
              :placeholder="$t('variables.please_enter_value')"
              autocomplete="off"
              maxlength="50"
              clearable
            />
            <span class="ed-range-separator separator"></span>
            <el-input
              v-model.number="pageForm.value[1]"
              :placeholder="$t('variables.please_enter_value')"
              autocomplete="off"
              maxlength="50"
              clearable
            />
          </template>
          <template v-else>
            <el-date-picker
              v-model="pageForm.value"
              type="daterange"
              value-format="YYYY-MM-DD"
              range-separator=""
              :start-placeholder="$t('variables.start_date')"
              :end-placeholder="$t('variables.end_date')"
            />
          </template>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button secondary @click="onFormClose">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveHandler">
          {{ $t('common.save') }}
        </el-button>
      </div>
    </template>
  </el-drawer>
</template>

<style lang="less" scoped>
.variables {
  height: 100%;
  position: relative;

  .datasource-yet {
    padding-bottom: 0;
    height: auto;
    padding-top: 200px;
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
    .btn-select {
      height: 32px;
      padding-left: 4px;
      padding-right: 4px;
      display: inline-flex;
      background: #ffffff;
      align-items: center;
      border: 1px solid #d9dcdf;
      border-radius: 6px;

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
      .system-flag {
        background-color: var(--ed-color-primary-33, #1cba9033);
        border-radius: 4px;
        height: 16px;
        line-height: 16px;
        padding: 0 4px;
        font-size: 10px;
        margin-left: 4px;
        color: var(--ed-color-primary-15-d, #189e7a);
      }
      .ed-icon {
        color: #646a73;
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
            color: #bbbfc4;
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
.variables-config {
  .ed-form-item__label:has(.btn) {
    padding-right: 0;
    width: 100%;
    margin-bottom: 8px;
  }

  .ed-form-item__content:has(.item) {
    margin-bottom: 8px;
  }

  .text::after {
    color: var(--ed-color-danger);
    content: '*';
    margin-left: 2px;
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
  .value-list {
    width: 100%;
    .item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;

      .action-btn {
        margin-left: 8px;
        cursor: pointer;

        &.not-allow {
          cursor: not-allowed;
          color: #bbbfc4;
        }
      }
    }
  }
  .value-number_date {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    .ed-range-separator::after {
      content: '';
      height: 1px;
      width: 10px;
      background: #1f2329;
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
    }

    .separator {
      width: 12px;
      margin: 0 8px;
    }
  }
}
</style>
