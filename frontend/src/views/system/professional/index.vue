<script lang="ts" setup>
import { nextTick, onMounted, reactive, ref, unref } from 'vue'
import icon_export_outlined from '@/assets/svg/icon_export_outlined.svg'
import { professionalApi } from '@/api/professional'
import { formatTimestamp } from '@/utils/date'
import { datasourceApi } from '@/api/datasource'
import ccmUpload from '@/assets/svg/icon_ccm-upload_outlined.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import IconOpeEdit from '@/assets/svg/icon_edit_outlined.svg'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { useI18n } from 'vue-i18n'
import { cloneDeep } from 'lodash-es'

interface Form {
  id?: string | null
  word: string | null
  other_words: string[]
  specific_ds: boolean
  datasource_ids: number[]
  datasource_names: string[]
  description: string | null
}

const { t } = useI18n()
const multipleSelectionAll = ref<any[]>([])
const allDsList = ref<any[]>([])
const keywords = ref('')
const oldKeywords = ref('')
const searchLoading = ref(false)

const selectable = () => {
  return true
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

const dialogTitle = ref('')
const updateLoading = ref(false)
const defaultForm = {
  id: null,
  word: null,
  description: null,
  specific_ds: false,
  datasource_ids: [],
  other_words: [''],
  datasource_names: [],
}
const pageForm = ref<Form>(cloneDeep(defaultForm))

const cancelDelete = () => {
  handleToggleRowSelection(false)
  multipleSelectionAll.value = []
  checkAll.value = false
  isIndeterminate.value = false
}
const exportBatchUser = () => {
  ElMessageBox.confirm(
    t('professional.selected_2_terms_de', { msg: multipleSelectionAll.value.length }),
    {
      confirmButtonType: 'primary',
      confirmButtonText: t('professional.export'),
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
    }
  ).then(() => {
    professionalApi.deleteEmbedded(multipleSelectionAll.value.map((ele) => ele.id)).then(() => {
      ElMessage({
        type: 'success',
        message: t('dashboard.delete_success'),
      })
      multipleSelectionAll.value = []
      search()
    })
  })
}

const exportAllUser = () => {
  ElMessageBox.confirm(t('professional.all_236_terms', { msg: pageInfo.total }), {
    confirmButtonType: 'primary',
    confirmButtonText: t('professional.export'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    professionalApi.deleteEmbedded(multipleSelectionAll.value.map((ele) => ele.id)).then(() => {
      ElMessage({
        type: 'success',
        message: t('dashboard.delete_success'),
      })
      multipleSelectionAll.value = []
      search()
    })
  })
}
const deleteBatchUser = () => {
  ElMessageBox.confirm(
    t('professional.selected_2_terms', { msg: multipleSelectionAll.value.length }),
    {
      confirmButtonType: 'danger',
      confirmButtonText: t('dashboard.delete'),
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
    }
  ).then(() => {
    professionalApi.deleteEmbedded(multipleSelectionAll.value.map((ele) => ele.id)).then(() => {
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
  ElMessageBox.confirm(t('professional.the_term_gmv', { msg: row.word }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    professionalApi.deleteEmbedded([row.id]).then(() => {
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

const search = () => {
  searchLoading.value = true
  oldKeywords.value = keywords.value
  professionalApi
    .getList(
      pageInfo.currentPage,
      pageInfo.pageSize,
      keywords.value ? { word: keywords.value } : {}
    )
    .then((res) => {
      toggleRowLoading.value = true
      fieldList.value = res.data
      pageInfo.total = res.total_count
      searchLoading.value = false
      nextTick(() => {
        handleToggleRowSelection()
      })
    })
    .finally(() => {
      searchLoading.value = false
    })
}

const termFormRef = ref()

const validatePass = (_: any, value: any, callback: any) => {
  if (pageForm.value.specific_ds && !value.length) {
    callback(new Error(t('datasource.Please_select') + t('common.empty') + t('ds.title')))
  } else {
    callback()
  }
}

const rules = {
  word: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('professional.term_name'),
    },
  ],
  description: [
    {
      required: true,
      message:
        t('datasource.please_enter') + t('common.empty') + t('professional.term_description'),
    },
  ],
  datasource_ids: [
    {
      validator: validatePass,
      trigger: 'blur',
    },
  ],
}

const handleChange = () => {
  termFormRef.value.validateField('datasource_ids')
}

const saveHandler = () => {
  termFormRef.value.validate((res: any) => {
    if (res) {
      const arr = [...pageForm.value.other_words.filter((ele: any) => !!ele), pageForm.value.word]
      if (arr.length !== new Set(arr).size) {
        return ElMessage.error(t('professional.cannot_be_repeated'))
      }
      const obj = unref(pageForm)
      if (!obj.id) {
        delete obj.id
      }
      updateLoading.value = true
      professionalApi
        .updateEmbedded(obj)
        .then(() => {
          ElMessage({
            type: 'success',
            message: t('common.save_success'),
          })
          search()
          onFormClose()
        })
        .finally(() => {
          updateLoading.value = false
        })
    }
  })
}
const list = () => {
  datasourceApi.list().then((res) => {
    allDsList.value = res
  })
}
const editHandler = (row: any) => {
  pageForm.value.id = null
  if (row) {
    pageForm.value = cloneDeep(row)
    if (!pageForm.value.other_words.length) {
      pageForm.value.other_words = ['']
    }
  }
  dialogTitle.value = row?.id
    ? t('professional.editing_terminology')
    : t('professional.create_new_term')
  dialogFormVisible.value = true
  list()
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
const rowInfoDialog = ref(false)

const handleRowClick = (row: any) => {
  pageForm.value = cloneDeep(row)
  rowInfoDialog.value = true
}

const onRowFormClose = () => {
  pageForm.value = cloneDeep(defaultForm)
  rowInfoDialog.value = false
}

const deleteHandlerItem = (idx: number) => {
  pageForm.value.other_words = pageForm.value.other_words!.filter((_, index) => index !== idx)
}
</script>

<template>
  <div v-loading="searchLoading" class="professional">
    <div class="tool-left">
      <span class="page-title">{{ $t('professional.professional_terminology') }}</span>
      <div>
        <el-input
          v-model="keywords"
          style="width: 240px; margin-right: 12px"
          :placeholder="$t('professional.search_term')"
          clearable
          @blur="search"
        >
          <template #prefix>
            <el-icon>
              <icon_searchOutline_outlined />
            </el-icon>
          </template>
        </el-input>
        <template v-if="false">
          <el-button secondary @click="exportAllUser">
            <template #icon>
              <icon_export_outlined />
            </template>
            {{ $t('professional.export_all') }}
          </el-button>
          <el-button secondary @click="editHandler(null)">
            <template #icon>
              <ccmUpload></ccmUpload>
            </template>
            {{ $t('user.batch_import') }}
          </el-button>
        </template>
        <el-button type="primary" @click="editHandler(null)">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('professional.create_new_term') }}
        </el-button>
      </div>
    </div>
    <div
      v-if="!searchLoading"
      class="table-content"
      :class="multipleSelectionAll?.length && 'show-pagination_height'"
    >
      <div class="preview-or-schema">
        <el-table
          ref="multipleTableRef"
          :data="fieldList"
          style="width: 100%"
          @row-click="handleRowClick"
          @selection-change="handleSelectionChange"
        >
          <el-table-column :selectable="selectable" type="selection" width="55" />
          <el-table-column prop="word" :label="$t('professional.term_name')" width="280">
            <template #default="scope">
              {{ scope.row.word }}
              <span style="display: inline-block; width: 8px; height: 1px"></span>
              {{
                scope.row.other_words.filter((ele: any) => !!ele).length
                  ? `(${scope.row.other_words.join(',')})`
                  : ''
              }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('professional.term_description')" min-width="240"
            ><template #default="scope">
              <div class="field-comment_d">
                <span :title="scope.row.description" class="notes-in_table">{{
                  scope.row.description
                }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column :label="$t('training.effective_data_sources')" min-width="240"
            ><template #default="scope">
              <div v-if="scope.row.specific_ds" class="field-comment_d">
                <span :title="scope.row.datasource_names" class="notes-in_table">{{
                  scope.row.datasource_names.join(',')
                }}</span>
              </div>
              <div v-else>{{ t('training.all_data_sources') }}</div>
            </template>
          </el-table-column>
          <el-table-column
            prop="create_time"
            sortable
            :label="$t('dashboard.create_time')"
            width="240"
          >
            <template #default="scope">
              <span>{{ formatTimestamp(scope.row.create_time, 'YYYY-MM-DD HH:mm:ss') }}</span>
            </template>
          </el-table-column>
          <el-table-column fixed="right" width="80" :label="t('ds.actions')">
            <template #default="scope">
              <div class="field-comment">
                <el-tooltip
                  :offset="14"
                  effect="dark"
                  :content="$t('datasource.edit')"
                  placement="top"
                >
                  <el-icon class="action-btn" size="16" @click.stop="editHandler(scope.row)">
                    <IconOpeEdit></IconOpeEdit>
                  </el-icon>
                </el-tooltip>
                <el-tooltip
                  :offset="14"
                  effect="dark"
                  :content="$t('dashboard.delete')"
                  placement="top"
                >
                  <el-icon class="action-btn" size="16" @click.stop="deleteHandler(scope.row)">
                    <IconOpeDelete></IconOpeDelete>
                  </el-icon>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <EmptyBackground
              v-if="!oldKeywords && !fieldList.length"
              :description="$t('professional.no_term')"
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
      <button v-if="false" class="primary-button" @click="exportBatchUser">
        {{ $t('professional.export') }}
      </button>

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
    destroy-on-close
    size="600px"
    :before-close="onFormClose"
    modal-class="professional-add_drawer"
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
      <el-form-item prop="word" :label="t('professional.term_name')">
        <el-input
          v-model="pageForm.word"
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('professional.term_name')
          "
          autocomplete="off"
          maxlength="50"
          clearable
        />
      </el-form-item>
      <el-form-item prop="description" :label="t('professional.term_description')">
        <el-input
          v-model="pageForm.description"
          :placeholder="$t('datasource.please_enter')"
          :autosize="{ minRows: 3.636, maxRows: 11.09 }"
          type="textarea"
        />
      </el-form-item>
      <el-form-item
        class="is-required"
        :class="!pageForm.specific_ds && 'no-error'"
        prop="datasource_ids"
        :label="t('training.effective_data_sources')"
      >
        <el-radio-group v-model="pageForm.specific_ds">
          <el-radio :value="false">{{ $t('training.all_data_sources') }}</el-radio>
          <el-radio :value="true">{{ $t('training.partial_data_sources') }}</el-radio>
        </el-radio-group>
        <el-select
          v-model="pageForm.datasource_ids"
          multiple
          v-if="pageForm.specific_ds"
          filterable
          @change="handleChange"
          :placeholder="$t('datasource.Please_select') + $t('common.empty') + $t('ds.title')"
          style="width: 100%; margin-top: 8px"
        >
          <el-option v-for="item in allDsList" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
      </el-form-item>

      <el-form-item>
        <template #label>
          <div style="display: flex; align-items: center">
            <span>{{ t('professional.synonyms') }}</span>
            <span class="btn" @click="pageForm.other_words.push('')">
              <el-icon style="margin-right: 4px" size="16">
                <icon_add_outlined></icon_add_outlined>
              </el-icon>
              {{ $t('model.add') }}
            </span>
          </div>
        </template>
        <div class="synonyms-list">
          <el-scrollbar>
            <div v-for="(_, index) in pageForm.other_words" :key="index" class="scrollbar-item">
              <el-input
                v-model="pageForm.other_words[index]"
                style="width: 528px"
                :placeholder="
                  $t('datasource.please_enter') + $t('common.empty') + $t('professional.synonyms')
                "
                maxlength="100"
                clearable
              />
              <el-tooltip
                :offset="14"
                effect="dark"
                :content="$t('dashboard.delete')"
                placement="top"
              >
                <el-icon
                  class="hover-icon_with_bg"
                  size="16"
                  style="color: #646a73"
                  @click.stop="deleteHandlerItem(index)"
                >
                  <IconOpeDelete></IconOpeDelete>
                </el-icon>
              </el-tooltip>
            </div>
          </el-scrollbar>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <div v-loading="updateLoading" class="dialog-footer">
        <el-button secondary @click="onFormClose">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveHandler">
          {{ $t('common.save') }}
        </el-button>
      </div>
    </template>
  </el-drawer>
  <el-drawer
    v-model="rowInfoDialog"
    :title="$t('professional.professional_term_details')"
    destroy-on-close
    size="600px"
    :before-close="onRowFormClose"
    modal-class="professional-term_drawer"
  >
    <el-form label-width="180px" label-position="top" class="form-content_error" @submit.prevent>
      <el-form-item :label="t('professional.business_term')">
        <div class="content">
          {{ pageForm.word }}
        </div>
      </el-form-item>
      <el-form-item :label="t('professional.synonyms')">
        <div class="content">
          {{ pageForm.other_words.join(',') }}
        </div>
      </el-form-item>
      <el-form-item :label="t('training.effective_data_sources')">
        <div class="content">
          {{
            pageForm.specific_ds
              ? pageForm.datasource_names.join(',')
              : t('training.all_data_sources')
          }}
        </div>
      </el-form-item>
      <el-form-item :label="t('professional.term_description')">
        <div class="content">
          {{ pageForm.description }}
        </div>
      </el-form-item>
    </el-form>
  </el-drawer>
</template>

<style lang="less" scoped>
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
