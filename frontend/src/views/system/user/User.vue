<template>
  <div class="sqlbot-table-container professional-container">
    <div class="tool-left">
      <span class="page-title">{{ $t('user.user_management') }}</span>
      <div class="search-bar">
        <el-input
          v-model="keyword"
          style="width: 240px; margin-right: 12px"
          :placeholder="$t('user.name_account_email')"
          clearable
          @keydown.enter.exact.prevent="handleSearch"
        >
          <template #prefix>
            <el-icon>
              <icon_searchOutline_outlined />
            </el-icon>
          </template>
        </el-input>

        <el-button secondary @click="drawerMainOpen">
          <template #icon>
            <iconFilter></iconFilter>
          </template>
          {{ $t('user.filter') }}
        </el-button>
        <!--  <el-button secondary @click="handleUserImport">
          <template #icon>
            <ccmUpload></ccmUpload>
          </template>
          {{ $t('user.batch_import') }}
        </el-button> -->
        <el-button type="primary" @click="editHandler(null)">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('user.add_users') }}
        </el-button>
      </div>
    </div>
    <div
      class="sqlbot-table_user"
      :class="[
        state.filterTexts.length && 'is-filter',
        multipleSelectionAll.length && 'show-pagination_height',
      ]"
    >
      <filter-text
        :total="state.pageInfo.total"
        :filter-texts="state.filterTexts"
        @clear-filter="clearFilter"
      />
      <el-table
        ref="multipleTableRef"
        :data="state.tableData"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" show-overflow-tooltip :label="$t('user.name')" width="280" />
        <el-table-column
          prop="account"
          show-overflow-tooltip
          :label="$t('user.account')"
          width="280"
        />
        <el-table-column prop="status" :label="$t('user.user_status')" width="180">
          <template #default="scope">
            <div class="user-status-container" :class="[scope.row.status ? 'active' : 'disabled']">
              <el-icon size="16">
                <SuccessFilled v-if="scope.row.status" />
                <CircleCloseFilled v-else />
              </el-icon>
              <span>{{ $t(`user.${scope.row.status ? 'enabled' : 'disabled'}`) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" show-overflow-tooltip :label="$t('user.email')" />
        <!-- <el-table-column prop="phone" :label="$t('user.phone_number')" width="280" /> -->
        <el-table-column prop="origin" :label="$t('user.user_source')" width="120">
          <template #default="scope">
            <span>{{ formatUserOrigin(scope.row.origin) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          show-overflow-tooltip
          prop="oid_list"
          :label="$t('user.workspace')"
          width="280"
        >
          <template #default="scope">
            <span>{{ formatSpaceName(scope.row.oid_list) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="create_time" width="180" sortable :label="$t('user.creation_time')">
          <template #default="scope">
            <span>{{ formatTimestamp(scope.row.create_time, 'YYYY-MM-DD HH:mm:ss') }}</span>
          </template>
        </el-table-column>
        <el-table-column fixed="right" width="150" :label="$t('ds.actions')">
          <template #default="scope">
            <div class="table-operate">
              <el-switch
                v-model="scope.row.status"
                :active-value="1"
                :inactive-value="0"
                size="small"
                @change="statusHandler(scope.row)"
              />
              <div class="line"></div>
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
                :content="$t('common.reset_password')"
                placement="top"
              >
                <el-icon
                  :ref="
                    (el: any) => {
                      setButtonRef(el, scope.row)
                    }
                  "
                  v-click-outside="() => onClickOutside(scope.row)"
                  class="action-btn"
                  size="16"
                >
                  <IconLock></IconLock>
                </el-icon>
              </el-tooltip>
              <el-popover
                :ref="
                  (el: any) => {
                    setPopoverRef(el, scope.row)
                  }
                "
                placement="right"
                virtual-triggering
                :width="300"
                :virtual-ref="scope.row.buttonRef"
                trigger="click"
                show-arrow
              >
                <div class="reset-pwd-confirm">
                  <div class="confirm-header">
                    <span class="icon-span">
                      <el-icon size="24">
                        <icon_warning_filled class="svg-icon" />
                      </el-icon>
                    </span>
                    <span class="header-span">{{ t('datasource.the_original_one') }}</span>
                  </div>
                  <div class="confirm-content">
                    <span>{{ defaultPwd }}</span>
                    <el-button style="margin-left: 4px" text @click="copyText">{{
                      t('datasource.copy')
                    }}</el-button>
                  </div>
                  <div class="confirm-foot">
                    <el-button secondary @click="closeResetInfo(scope.row)">{{
                      t('common.cancel')
                    }}</el-button>
                    <el-button type="primary" @click="handleEditPassword(scope.row.id)">
                      {{ t('datasource.confirm') }}
                    </el-button>
                  </div>
                </div>
              </el-popover>

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
            v-if="!!keyword && !state.tableData.length"
            :description="$t('datasource.relevant_content_found')"
            img-type="tree"
          />
        </template>
      </el-table>
    </div>
    <div v-if="state.tableData.length" class="pagination-container">
      <el-pagination
        v-model:current-page="state.pageInfo.currentPage"
        v-model:page-size="state.pageInfo.pageSize"
        :page-sizes="[10, 20, 30]"
        :background="true"
        layout="total, sizes, prev, pager, next, jumper"
        :total="state.pageInfo.total"
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
    modal-class="user-add-class"
    size="600px"
    :before-close="onFormClose"
  >
    <div style="margin-bottom: 12px" class="down-template">
      <span class="icon-span">
        <el-icon>
          <Icon name="icon_warning_filled"><icon_warning_filled class="svg-icon" /></Icon>
        </el-icon>
      </span>
      <div class="down-template-content" style="align-items: center">
        <span>{{ t('prompt.default_password', { msg: defaultPwd }) }}</span>
        <el-button style="margin-left: 4px" size="small" text @click="copyPassword">{{
          t('datasource.copy')
        }}</el-button>
      </div>
    </div>
    <el-form
      ref="termFormRef"
      :model="state.form"
      label-width="180px"
      label-position="top"
      :rules="rules"
      class="form-content_error"
      @submit.prevent
    >
      <el-form-item prop="name" :label="t('user.name')">
        <el-input
          v-model="state.form.name"
          :placeholder="$t('datasource.please_enter') + $t('common.empty') + $t('user.name')"
          autocomplete="off"
          maxlength="50"
          clearable
        />
      </el-form-item>
      <el-form-item prop="account" :label="t('user.account')">
        <el-input
          v-model="state.form.account"
          :disabled="!!state.form.id"
          :placeholder="$t('datasource.please_enter') + $t('common.empty') + $t('user.account')"
          autocomplete="off"
          maxlength="50"
          clearable
        />
      </el-form-item>
      <el-form-item prop="email" :label="$t('user.email')">
        <el-input
          v-model="state.form.email"
          :placeholder="$t('datasource.please_enter') + $t('common.empty') + $t('user.email')"
          autocomplete="off"
          clearable
        />
      </el-form-item>
      <!-- <el-form-item :label="$t('user.phone_number')">
        <el-input
          v-model="state.form.phoneNumber"
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('user.phone_number')
          "
          autocomplete="off"
        />
      </el-form-item> -->

      <el-form-item :label="$t('user.workspace')">
        <el-select
          v-model="state.form.oid_list"
          multiple
          :placeholder="$t('datasource.Please_select') + $t('common.empty') + $t('user.workspace')"
        >
          <el-option v-for="item in options" :key="item.id" :label="item.name" :value="item.id">
            <div class="ellipsis" :title="item.name" style="max-width: 500px; padding-right: 30px">
              {{ item.name }}
            </div>
          </el-option>
        </el-select>
      </el-form-item>
      <el-form-item :label="$t('user.user_status')">
        <el-switch v-model="state.form.status" :active-value="1" :inactive-value="0" />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button secondary @click="closeForm">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveHandler">
          {{ state.form.id ? $t('common.save') : $t('model.add') }}
        </el-button>
      </div>
    </template>
  </el-drawer>
  <el-dialog
    v-model="dialogVisiblePassword"
    :title="$t('user.change_password')"
    width="500"
    :before-close="handleClosePassword"
  >
    <el-form
      ref="passwordRef"
      :model="password"
      label-width="180px"
      label-position="top"
      :rules="passwordRules"
      class="form-content_error"
      @submit.prevent
    >
      <el-form-item prop="new" :label="t('user.new_password')">
        <el-input
          v-model="password.new"
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('user.new_password')
          "
          autocomplete="off"
          clearable
        />
      </el-form-item>
      <el-form-item prop="old" :label="t('user.confirm_password')">
        <el-input
          v-model="password.old"
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('user.confirm_password')
          "
          autocomplete="off"
          clearable
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button secondary @click="handleClosePassword">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleConfirmPassword">
          {{ $t('common.save') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
  <UserImport ref="userImportRef" @refresh-grid="search"></UserImport>
  <drawer-main
    ref="drawerMainRef"
    :filter-options="filterOption"
    @trigger-filter="searchCondition"
  />
</template>

<script setup lang="ts">
import { ref, unref, reactive, onMounted, nextTick } from 'vue'
import UserImport from './UserImport.vue'
import SuccessFilled from '@/assets/svg/gou_icon.svg'
import CircleCloseFilled from '@/assets/svg/icon_ban_filled.svg'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import { useI18n } from 'vue-i18n'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { convertFilterText, FilterText } from '@/components/filter-text'

import IconLock from '@/assets/svg/icon-key_outlined.svg'
import IconOpeEdit from '@/assets/svg/icon_edit_outlined.svg'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import iconFilter from '@/assets/svg/icon-filter_outlined.svg'
// import ccmUpload from '@/assets/svg/icon_ccm-upload_outlined.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import { userApi } from '@/api/user'
import { workspaceList } from '@/api/workspace'
import { formatTimestamp } from '@/utils/date'
import { ClickOutside as vClickOutside } from 'element-plus-secondary'
import icon_warning_filled from '@/assets/svg/icon_warning_filled.svg'
import { useClipboard } from '@vueuse/core'

const { copy } = useClipboard({ legacy: true })

const { t } = useI18n()
const defaultPwd = ref('SQLBot@123456')
const keyword = ref('')
const dialogFormVisible = ref(false)
const termFormRef = ref()
const checkAll = ref(false)
const dialogVisiblePassword = ref(false)
const isIndeterminate = ref(true)
const drawerMainRef = ref()
const userImportRef = ref()
const selectionLoading = ref(false)
const filterOption = ref<any[]>([
  {
    type: 'enum',
    option: [
      { id: 1, name: t('user.enable') },
      { id: 0, name: t('user.disable') },
    ],
    field: 'status',
    title: t('user.user_status'),
    operate: 'in',
  },
  {
    type: 'enum',
    option: [
      { id: '0', name: t('user.local_creation') },
      { id: '1', name: 'CAS' },
      { id: '2', name: 'OIDC' },
      { id: '3', name: 'LDAP' },
      { id: '4', name: 'OAuth2' },
      /* { id: '5', name: 'SAML2' }, */
    ],
    field: 'origins',
    title: t('user.user_source'),
    operate: 'in',
  },
  {
    type: 'select',
    option: [],
    field: 'oidlist',
    title: t('user.workspace'),
    operate: 'in',
    property: { placeholder: t('common.empty') + t('user.workspace') },
  },
])

const defaultForm = {
  id: '',
  name: '',
  account: '',
  oid: 0,
  email: '',
  status: 1,
  phoneNumber: '',
  oid_list: [],
}
const options = ref<any[]>([])
const state = reactive<any>({
  tableData: [],
  filterTexts: [],
  conditions: [],
  form: { ...defaultForm },
  pageInfo: {
    currentPage: 1,
    pageSize: 20,
    total: 0,
  },
})
const rules = {
  name: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('user.name'),
      trigger: 'blur',
    },
  ],
  account: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('user.account'),
      trigger: 'blur',
    },
  ],
  email: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('user.email'),
      trigger: 'blur',
    },
    {
      required: true,
      pattern: /^[a-zA-Z0-9_._-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$/,
      message: t('datasource.incorrect_email_format'),
      trigger: 'blur',
    },
  ],
}

const passwordRules = {
  new: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('user.new_password'),
      trigger: 'blur',
    },
  ],
  old: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('user.confirm_password'),
      trigger: 'blur',
    },
  ],
}

const closeResetInfo = (row: any) => {
  row.popoverRef?.hide()
  row.resetInfoShow = false
}
const setPopoverRef = (el: any, row: any) => {
  row.popoverRef = el
}

const copyText = () => {
  copy(defaultPwd.value)
    .then(function () {
      ElMessage.success(t('embedded.copy_successful'))
    })
    .catch(function () {
      ElMessage.error(t('embedded.copy_failed'))
    })
}

const copyPassword = () => {
  copy(defaultPwd.value)
    .then(function () {
      ElMessage.success(t('embedded.copy_successful'))
    })
    .catch(function () {
      ElMessage.error(t('embedded.copy_failed'))
    })
}

const setButtonRef = (el: any, row: any) => {
  row.buttonRef = el
}
const onClickOutside = (row: any) => {
  if (row.popoverRef) {
    unref(row.popoverRef).popperRef?.delayHide?.()
  }
}

const multipleTableRef = ref()
const multipleSelectionAll = ref<any[]>([])
const dialogTitle = ref('')
const passwordRef = ref()
const password = ref({
  new: '',
  old: '',
  id: '',
})

const handleClosePassword = () => {
  dialogVisiblePassword.value = false
}

const handleEditPassword = (id: any) => {
  userApi.pwd(id).then(() => {
    ElMessage({
      type: 'success',
      message: t('common.password_reset_successful'),
    })
  })
}

/* const handleUserImport = () => {
  userImportRef.value.showDialog()
} */

const handleConfirmPassword = () => {
  passwordRef.value.validate((val: any) => {
    if (val) {
      console.info(val)
    }
  })
  dialogVisiblePassword.value = false
}

const handleSelectionChange = (val: any[]) => {
  if (selectionLoading.value) return
  const ids = state.tableData.map((ele: any) => ele.id)
  multipleSelectionAll.value = [
    ...multipleSelectionAll.value.filter((ele) => !ids.includes(ele.id)),
    ...val,
  ]
  isIndeterminate.value = !(val.length === 0 || val.length === state.tableData.length)
  checkAll.value = val.length === state.tableData.length
}
const handleCheckAllChange = (val: any) => {
  isIndeterminate.value = false
  handleSelectionChange(val ? state.tableData : [])
  if (val) {
    handleToggleRowSelection()
  } else {
    multipleTableRef.value.clearSelection()
  }
}

const handleToggleRowSelection = (check: boolean = true) => {
  let i = 0
  const ids = multipleSelectionAll.value.map((ele: any) => ele.id)
  for (const key in state.tableData) {
    if (ids.includes((state.tableData[key] as any).id)) {
      i += 1
      multipleTableRef.value.toggleRowSelection(state.tableData[key], check)
    }
  }
  checkAll.value = i === state.tableData.length
  isIndeterminate.value = !(i === 0 || i === state.tableData.length)
  selectionLoading.value = false
}
const handleSearch = ($event: any = {}) => {
  if ($event?.isComposing) {
    return
  }
  state.pageInfo.currentPage = 1
  search()
}
const fillFilterText = () => {
  const textArray = state.conditions?.length
    ? convertFilterText(state.conditions, filterOption.value)
    : []
  state.filterTexts = [...textArray]
  Object.assign(state.filterTexts, textArray)
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
const searchCondition = (conditions: any) => {
  state.conditions = conditions
  fillFilterText()
  search()
  drawerMainClose()
}
const drawerMainOpen = async () => {
  drawerMainRef.value.init()
}
const drawerMainClose = () => {
  drawerMainRef.value.close()
}
const editHandler = (row: any) => {
  if (row) {
    state.form = { ...row }
  }
  dialogFormVisible.value = true
  dialogTitle.value = row?.id ? t('user.edit_user') : t('user.add_users')
}

const statusHandler = (row: any) => {
  /* state.form = { ...row }
  editTerm() */
  const param = {
    id: row.id,
    status: row.status,
  }
  userApi.status(param)
}

const cancelDelete = () => {
  handleToggleRowSelection(false)
  multipleSelectionAll.value = []
  checkAll.value = false
  isIndeterminate.value = false
}
const deleteBatchUser = () => {
  ElMessageBox.confirm(t('user.selected_2_users', { msg: multipleSelectionAll.value.length }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    userApi.deleteBatch(multipleSelectionAll.value.map((ele) => ele.id)).then(() => {
      multipleSelectionAll.value = []
      ElMessage({
        type: 'success',
        message: t('dashboard.delete_success'),
      })
      search()
    })
  })
}
const deleteHandler = (row: any) => {
  ElMessageBox.confirm(t('user.del_user', { msg: row.name }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    userApi.delete(row.id).then(() => {
      multipleSelectionAll.value = multipleSelectionAll.value.filter((ele) => ele.id !== row.id)
      ElMessage({
        type: 'success',
        message: t('dashboard.delete_success'),
      })
      search()
    })
  })
}

const closeForm = () => {
  dialogFormVisible.value = false
}
const onFormClose = () => {
  state.form = { ...defaultForm }
  dialogFormVisible.value = false
}

const configParams = () => {
  let str = ''
  if (keyword.value) {
    str += `keyword=${keyword.value}`
  }

  state.conditions.forEach((ele: any) => {
    if (ele.field === 'status' && ele.value.length === 2) {
      return
    }
    ele.value.forEach((itx: any) => {
      str += str ? `&${ele.field}=${itx}` : `${ele.field}=${itx}`
    })
  })

  if (str.length) {
    str = `?${str}`
  }

  return str
}

const search = () => {
  userApi
    .pager(configParams(), state.pageInfo.currentPage, state.pageInfo.pageSize)
    .then((res: any) => {
      state.tableData = res.items
      state.pageInfo.total = res.total
      selectionLoading.value = true
      nextTick(() => {
        handleToggleRowSelection()
      })
    })
}
const addTerm = () => {
  const { account, email, name, oid, status, oid_list } = state.form
  userApi.add({ account, email, name, oid, status, oid_list }).then(() => {
    onFormClose()
    search()
    ElMessage({
      type: 'success',
      message: t('common.save_success'),
    })
  })
}
const editTerm = () => {
  const { account, id, create_time, email, language, name, oid, oid_list, origin, status } =
    state.form
  userApi
    .edit({ account, id, create_time, email, language, name, oid, oid_list, origin, status })
    .then(() => {
      onFormClose()
      search()
      ElMessage({
        type: 'success',
        message: t('common.save_success'),
      })
    })
}

const duplicateName = () => {
  if (state.form.id) {
    editTerm()
  } else {
    addTerm()
  }
}

const saveHandler = () => {
  termFormRef.value.validate((res: any) => {
    if (res) {
      duplicateName()
    }
  })
}
const handleSizeChange = (val: number) => {
  state.pageInfo.pageSize = val
  state.pageInfo.currentPage = 1
  search()
}
const handleCurrentChange = (val: number) => {
  state.pageInfo.currentPage = val
  search()
}
const formatSpaceName = (row_oid_list: Array<any>) => {
  if (!row_oid_list?.length) {
    return '-'
  }
  const wsMap: Record<string, string> = {}
  options.value.forEach((option: any) => {
    wsMap[option.id] = option.name
  })
  return row_oid_list.map((id: any) => wsMap[id]).join(',')
}
const loadDefaultPwd = () => {
  userApi.defaultPwd().then((res) => {
    if (res) {
      defaultPwd.value = res
    }
  })
}
const formatUserOrigin = (origin?: number) => {
  if (!origin) {
    return t('user.local_creation')
  }
  const originArray = ['CAS', 'OIDC', 'LDAP', 'OAuth2', 'SAML2']
  return originArray[origin - 1]
}
onMounted(() => {
  workspaceList().then((res) => {
    options.value = res || []
    filterOption.value[2].option = [...options.value]
  })
  search()
  loadDefaultPwd()
})
</script>

<style lang="less" scoped>
.sqlbot-table-container {
  width: 100%;
  height: 100%;
  position: relative;
  .bottom-select {
    position: absolute;
    height: 64px;
    width: calc(100% + 48px);
    left: -24px;
    background-color: #fff;
    bottom: -16px;
    border-top: 1px solid #1f232926;
    display: flex;
    align-items: center;
    padding-left: 24px;
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
  .sqlbot-table_user {
    width: 100%;
    max-height: calc(100vh - 150px);
    overflow-y: auto;

    &.show-pagination_height {
      max-height: calc(100vh - 215px);
    }

    :deep(.ed-popper.is-dark) {
      max-width: 400px;
    }
    :deep(.ed-table) {
      --el-table-header-bg-color: #f5f7fa;
      --el-table-border-color: #ebeef5;
      --el-table-header-text-color: #606266;

      th {
        font-weight: 600;
        height: 48px;
      }

      td {
        height: 52px;
      }
    }
    .table-operate {
      display: flex;
      align-items: center;
      height: 24px;
      line-height: 24px;
      .ed-icon + .ed-icon {
        margin-left: 12px;
      }

      .line {
        margin: 0 10px 0 12px;
        height: 16px;
        width: 1px;
        background-color: #1f232926;
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

  .pagination-container {
    display: flex;
    justify-content: end;
    align-items: center;
    margin-top: 16px;
  }
}

.user-status-container {
  display: flex;
  align-items: center;
  font-weight: 400;
  font-size: 14px;
  line-height: 22px;

  .ed-icon {
    margin-right: 8px;
  }
}
</style>

<style lang="less">
.reset-pwd-confirm {
  padding: 5px 15px;
  .confirm-header {
    width: 100%;
    min-height: 40px;
    line-height: 40px;
    display: flex;
    flex-direction: row;
    .icon-span {
      color: var(--ed-color-warning);
      font-size: 22px;
      i {
        top: 3px;
      }
    }
    .header-span {
      font-size: 16px;
      font-weight: bold;
      margin-left: 10px;
      white-space: pre-wrap;
      word-break: keep-all;
    }
  }
  .confirm-foot {
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    align-items: center;
    margin-top: 15px;
    .ed-button {
      min-width: 48px;
      height: 28px;
      line-height: 28px;
      font-size: 12px;
    }
  }
  .confirm-warning {
    font-size: 12px;
    color: var(--ed-color-danger);
    margin-left: 33px;
  }
  .confirm-content {
    margin-left: 33px;
    display: flex;
    align-items: center;
  }
}
.user-add-class {
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
}
</style>
