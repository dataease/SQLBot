<script lang="ts" setup>
import { ref, onMounted, reactive, unref, nextTick } from 'vue'
import icon_copy_outlined from '@/assets/svg/icon_copy_outlined.svg'
import { embeddedApi } from '@/api/embedded'
import info_yellow from '@/assets/embedded/info-yellow.svg'
import icon_invisible_outlined from '@/assets/embedded/icon_invisible_outlined.svg'
import icon_visible_outlined from '@/assets/embedded/icon_visible_outlined.svg'
import icon_refresh_outlined from '@/assets/embedded/icon_refresh_outlined.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import IconOpeEdit from '@/assets/svg/icon_edit_outlined.svg'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { useClipboard } from '@vueuse/core'
import { useI18n } from 'vue-i18n'
import { cloneDeep } from 'lodash-es'

defineProps({
  btnSelect: {
    type: String,
    default: '',
  },
})

interface Form {
  id?: string | null
  name: string | null
  domain: string | null
  type: number
  configuration?: string | null
  description?: string | null
}

// const emits = defineEmits(['btnSelectChange'])
const { t } = useI18n()
const multipleSelectionAll = ref<any[]>([])
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

const pwd = '**********'

const dialogTitle = ref('')
const defaultForm = {
  id: null,
  name: null,
  domain: null,
  type: 4,
  configuration: null,
  description: null,
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
    embeddedApi.deleteEmbedded(multipleSelectionAll.value.map((ele) => ele.id)).then(() => {
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
  ElMessageBox.confirm(t('embedded.delete', { msg: row.name }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    embeddedApi.deleteEmbedded([row.id]).then(() => {
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

const setButtonRef = (el: any, row: any) => {
  row.buttonRef = el
}
const onClickOutside = (row: any) => {
  if (row.popoverRef) {
    unref(row.popoverRef).popperRef?.delayHide?.()
  }
}

const setPopoverRef = (el: any, row: any) => {
  row.popoverRef = el
}

const cancelRefresh = (row: any) => {
  if (row.popoverRef) {
    unref(row.popoverRef).hide?.()
  }
}

const refresh = (row: any) => {
  embeddedApi
    .secret(row.id)
    .then(() => {
      ElMessage.success(t('common.update_success'))
    })
    .finally(() => {
      cancelRefresh(row)
      search()
    })
}

const search = ($event: any = {}) => {
  if ($event?.isComposing) {
    return
  }
  searchLoading.value = true
  embeddedApi
    .getList(pageInfo.currentPage, pageInfo.pageSize, { keyword: keywords.value })
    .then((res) => {
      toggleRowLoading.value = true
      fieldList.value = res.items
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
const splitString = (str: string) => {
  if (typeof str !== 'string') {
    return []
  }
  return str
    .split(/[,;]/)
    .map((item) => item.trim())
    .filter((item) => item !== '')
}
const termFormRef = ref()
const validateUrl = (_: any, value: any, callback: any) => {
  if (value === '') {
    callback(
      new Error(
        t('datasource.please_enter') + t('common.empty') + t('embedded.cross_domain_settings')
      )
    )
  } else {
    // var Expression = /(https?:\/\/)?([\da-z\.-]+)\.([a-z]{2,6})(:\d{1,5})?([\/\w\.-]*)*\/?(#[\S]+)?/ // eslint-disable-line
    splitString(value).forEach((tempVal: string) => {
      var Expression = /^https?:\/\/[^\s/?#]+(:\d+)?/i
      var objExp = new RegExp(Expression)
      if (objExp.test(tempVal) && !tempVal.endsWith('/')) {
        callback()
      } else {
        callback(t('embedded.format_is_incorrect', { msg: t('embedded.domain_format_incorrect') }))
      }
    })
  }
}
const rules = {
  name: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('embedded.application_name'),
    },
  ],
  domain: [
    {
      required: true,
      validator: validateUrl,
      trigger: 'blur',
    },
  ],
}

const saveHandler = () => {
  termFormRef.value.validate((res: any) => {
    if (res) {
      const obj = unref(pageForm)
      if (obj.id === '') {
        delete obj.id
      }
      const req = obj.id ? embeddedApi.updateEmbedded : embeddedApi.addEmbedded
      req(obj).then(() => {
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
    const { id, name, domain, type, configuration, description } = row
    pageForm.value.id = id
    pageForm.value.name = name
    pageForm.value.domain = domain
    pageForm.value.type = type
    pageForm.value.configuration = configuration
    pageForm.value.description = description
  }
  dialogTitle.value = row?.id ? t('embedded.edit_app') : t('embedded.create_application')
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
const { copy } = useClipboard({ legacy: true })

const copyCode = (row: any, key: any = 'app_secret') => {
  copy(row[key])
    .then(function () {
      ElMessage.success(t('embedded.copy_successful'))
    })
    .catch(function () {
      ElMessage.error(t('embedded.copy_failed'))
    })
}
</script>

<template>
  <div v-loading="searchLoading" class="embedded-page">
    <div class="tool-left">
      <span class="page-title">{{ t('embedded.embedded_management') }}</span>
      <!-- <div class="btn-select">
        <el-button
          :class="[btnSelect === 'd' && 'is-active']"
          text
          @click="emits('btnSelectChange', 'd')"
        >
          {{ t('embedded.embedded_assistant') }}
        </el-button>
        <el-button
          :class="[btnSelect === 'q' && 'is-active']"
          text
          @click="emits('btnSelectChange', 'q')"
        >
          {{ t('embedded.embedded_page') }}
        </el-button>
      </div> -->
      <div>
        <el-input
          v-model="keywords"
          style="width: 240px; margin-right: 12px"
          :placeholder="$t('dashboard.search')"
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
          {{ $t('embedded.create_application') }}
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
          :description="$t('embedded.no_application')"
          img-type="noneWhite"
        />

        <div style="text-align: center; margin-top: -10px">
          <el-button type="primary" @click="editHandler(null)">
            <template #icon>
              <icon_add_outlined></icon_add_outlined>
            </template>
            {{ $t('embedded.create_application') }}
          </el-button>
        </div>
      </template>
      <div v-else class="preview-or-schema">
        <el-table
          ref="multipleTableRef"
          :data="fieldList"
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
          <el-table-column :selectable="selectable" type="selection" width="55" />
          <el-table-column prop="name" :label="$t('embedded.application_name')" width="280" />
          <el-table-column prop="app_id" label="APP ID" width="240">
            <template #default="scope">
              <div class="user-status-container">
                <div :title="scope.row.app_id" class="ellipsis" style="max-width: 192px">
                  {{ scope.row.app_id }}
                </div>
                <el-tooltip
                  :offset="12"
                  effect="dark"
                  :content="t('datasource.copy')"
                  placement="top"
                >
                  <el-icon
                    size="16"
                    class="hover-icon_with_bg"
                    @click="copyCode(scope.row, 'app_id')"
                  >
                    <icon_copy_outlined></icon_copy_outlined>
                  </el-icon>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="app_secret" label="APP Secret" width="240">
            <template #default="scope">
              <div class="user-status-container">
                <div
                  :title="scope.row.showPwd ? scope.row.app_secret : pwd"
                  class="ellipsis"
                  style="max-width: 133px"
                >
                  {{ scope.row.showPwd ? scope.row.app_secret : pwd }}
                </div>
                <el-tooltip
                  :offset="12"
                  effect="dark"
                  :content="t('datasource.copy')"
                  placement="top"
                >
                  <el-icon class="hover-icon_with_bg" size="16" @click="copyCode(scope.row)">
                    <icon_copy_outlined></icon_copy_outlined>
                  </el-icon>
                </el-tooltip>

                <el-tooltip
                  v-if="scope.row.showPwd"
                  :offset="12"
                  effect="dark"
                  :content="t('embedded.click_to_hide')"
                  placement="top"
                >
                  <el-icon class="hover-icon_with_bg" size="16" @click="scope.row.showPwd = false">
                    <icon_visible_outlined></icon_visible_outlined>
                  </el-icon>
                </el-tooltip>

                <el-tooltip
                  v-if="!scope.row.showPwd"
                  :offset="12"
                  effect="dark"
                  :content="t('embedded.click_to_show')"
                  placement="top"
                >
                  <el-icon class="hover-icon_with_bg" size="16" @click="scope.row.showPwd = true">
                    <icon_invisible_outlined></icon_invisible_outlined>
                  </el-icon>
                </el-tooltip>
                <el-icon
                  :ref="
                    (el: any) => {
                      setButtonRef(el, scope.row)
                    }
                  "
                  v-click-outside="() => onClickOutside(scope.row)"
                  class="hover-icon_with_bg"
                  :offset="12"
                  size="16"
                >
                  <icon_refresh_outlined></icon_refresh_outlined>
                </el-icon>

                <el-popover
                  :ref="
                    (el: any) => {
                      setPopoverRef(el, scope.row)
                    }
                  "
                  :width="280"
                  :offset="12"
                  virtual-triggering
                  :virtual-ref="scope.row.buttonRef"
                  show-arrow
                  popper-class="box-item_refresh"
                  placement="bottom"
                >
                  <template #reference> </template>
                  <div class="title">
                    <el-icon class="hover-icon_with_bg" size="16">
                      <info_yellow></info_yellow>
                    </el-icon>
                    <span class="sure">{{ $t('embedded.your_app_secret') }}</span>
                  </div>
                  <div class="tips">{{ $t('embedded.proceed_with_caution') }}</div>
                  <div class="btns">
                    <el-button secondary @click="cancelRefresh(scope.row)">
                      {{ t('common.cancel') }}
                    </el-button>
                    <el-button type="primary" @click="refresh(scope.row)">
                      {{ t('common.confirm2') }}
                    </el-button>
                  </div>
                </el-popover>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="domain"
            :label="$t('embedded.cross_domain_settings')"
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
                  <el-icon class="action-btn" size="16" @click="editHandler(scope.row)">
                    <IconOpeEdit></IconOpeEdit>
                  </el-icon>
                </el-tooltip>
                <el-tooltip
                  :offset="14"
                  effect="dark"
                  :content="$t('dashboard.delete')"
                  placement="top"
                >
                  <el-icon class="action-btn" size="16" @click="deleteHandler(scope.row)">
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
      <el-form-item prop="name" :label="t('embedded.application_name')">
        <el-input
          v-model="pageForm.name"
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('embedded.application_name')
          "
          autocomplete="off"
          maxlength="50"
          clearable
        />
      </el-form-item>
      <el-form-item prop="domain" :label="t('embedded.cross_domain_settings')">
        <el-input
          v-model="pageForm.domain"
          type="textarea"
          :autosize="{ minRows: 2 }"
          :placeholder="$t('embedded.third_party_address')"
          autocomplete="off"
          clearable
        />
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
.embedded-page {
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

        .ed-icon + .ed-icon {
          margin-left: 12px;
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
.box-item_refresh {
  --ed-popover-padding: 20px 24px;
  .ed-popper__arrow {
    background: transparent !important;
    &::before {
      background: #fff;
    }
  }
  .title {
    display: flex;
    align-items: center;
    .sure {
      margin-left: 8px;
      font-weight: 500;
      font-size: 14px;
    }
  }

  .tips {
    font-weight: 400;
    font-size: 14px;
    line-height: 22px;
    margin: 4px 0 16px 0;
    padding-left: 24px;
  }

  .btns {
    text-align: right;
    .ed-button {
      min-width: 48px;
    }
  }
}
</style>
