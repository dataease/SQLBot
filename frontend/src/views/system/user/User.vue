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

        <el-tooltip
          v-if="!platformType.length && showSyncBtn"
          effect="dark"
          :content="$t('sync.integration')"
          placement="left"
        >
          <el-button disabled secondary>
            <template #icon>
              <icon_replace_outlined />
            </template>
            {{ t('sync.sync_users') }}
          </el-button>
        </el-tooltip>

        <el-popover
          v-if="platformType.length && showSyncBtn"
          popper-class="sync-platform"
          placement="bottom-start"
        >
          <template #reference>
            <el-button secondary>
              <template #icon>
                <icon_replace_outlined />
              </template>
              {{ t('sync.sync_users') }}
            </el-button></template
          >
          <div class="popover">
            <div class="popover-content">
              <div
                v-for="ele in platformType"
                :key="ele.name"
                class="popover-item"
                @click="handleSyncUser(ele)"
              >
                <img height="24" width="24" :src="ele.icon" />
                <div class="model-name">{{ $t(ele.name) }}</div>
              </div>
            </div>
          </div>
        </el-popover>
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
      <el-form-item>
        <template #label>
          <div style="display: flex; align-items: center; height: 22px">
            <span>{{ t('variables.system_variables') }}</span>
            <span
              class="btn"
              @click="
                state.form.system_variables.push({
                  variableId: '',
                  variableValues: [],
                  variableValue: '',
                })
              "
            >
              <el-icon style="margin-right: 4px" size="16">
                <icon_add_outlined></icon_add_outlined>
              </el-icon>
              {{ $t('model.add') }}
            </span>
          </div>
        </template>
        <div v-if="!!state.form.system_variables.length" class="value-list">
          <div class="title">
            <span style="width: calc(48% - 2px)">{{ t('variables.variables') }}</span>
            <span>{{ t('variables.variable_value') }}</span>
          </div>
          <div v-for="(_, index) in state.form.system_variables" class="item">
            <el-select
              v-model="state.form.system_variables[index].variableId"
              style="width: 236px"
              :placeholder="$t('datasource.Please_select')"
            >
              <el-option
                v-for="item in variables"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              >
              </el-option>
            </el-select>
            <el-select
              v-if="!state.form.system_variables[index].variableId"
              v-model="state.form.system_variables[index].variableValues"
              multiple
              style="width: 236px"
              :placeholder="$t('datasource.Please_select')"
            >
              <el-option v-for="item in []" :key="item" :label="item" :value="item"> </el-option>
            </el-select>
            <el-select
              v-else-if="
                variableValueMap[state.form.system_variables[index].variableId].var_type === 'text'
              "
              v-model="state.form.system_variables[index].variableValues"
              multiple
              style="width: 236px"
              :placeholder="$t('datasource.Please_select')"
            >
              <el-option
                v-for="item in variableValueMap[state.form.system_variables[index].variableId]
                  .value"
                :key="item"
                :label="item"
                :value="item"
              >
              </el-option>
            </el-select>
            <el-input
              v-else-if="
                variableValueMap[state.form.system_variables[index].variableId].var_type ===
                'number'
              "
              v-model.number="state.form.system_variables[index].variableValue"
              style="width: 236px"
              :placeholder="$t('variables.please_enter_value')"
              autocomplete="off"
              maxlength="50"
              clearable
            />
            <el-date-picker
              v-else
              v-model="state.form.system_variables[index].variableValues"
              type="daterange"
              style="max-width: 236px"
              value-format="YYYY-MM-DD"
              range-separator=""
              :start-placeholder="$t('variables.start_date')"
              :end-placeholder="$t('variables.end_date')"
            />
            <el-tooltip
              :offset="14"
              effect="dark"
              :content="$t('dashboard.delete')"
              placement="top"
            >
              <el-icon class="action-btn" size="16" @click="deleteValues(index as number)">
                <IconOpeDelete></IconOpeDelete>
              </el-icon>
            </el-tooltip>
          </div>
        </div>
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
  <SyncUserDing ref="syncUserRef" @refresh="refresh"></SyncUserDing>
</template>

<script setup lang="ts">
import { ref, unref, reactive, onMounted, nextTick, h, shallowRef } from 'vue'
import UserImport from './UserImport.vue'
import SuccessFilled from '@/assets/svg/gou_icon.svg'
import icon_replace_outlined from '@/assets/svg/icon_replace_outlined.svg'
import CircleCloseFilled from '@/assets/svg/icon_ban_filled.svg'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import { useI18n } from 'vue-i18n'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { convertFilterText, FilterText } from '@/components/filter-text'
import SyncUserDing from './SyncUserDing.vue'
import IconLock from '@/assets/svg/icon-key_outlined.svg'
import IconOpeEdit from '@/assets/svg/icon_edit_outlined.svg'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import iconFilter from '@/assets/svg/icon-filter_outlined.svg'
import logo_dingtalk from '@/assets/img/dingtalk.png'
import logo_lark from '@/assets/img/lark.png'
import logo_wechat_work from '@/assets/img/wechat.png'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import { userApi } from '@/api/user'
import { request } from '@/utils/request'
import { workspaceList } from '@/api/workspace'
import { variablesApi } from '@/api/variables'
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
const syncUserRef = ref()
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
      { id: '6', name: t('user.wecom') },
      { id: '7', name: t('user.dingtalk') },
      { id: '8', name: t('user.lark') },
      /* { id: '9', name: t('user.larksuite') }, */
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
  system_variables: [],
}
const options = ref<any[]>([])
const variables = shallowRef<any[]>([])
const variableValueMap = shallowRef<any>({})
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

const currentPlatform = ref<any>({})
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

const platformType = ref<any[]>([
  {
    icon: logo_wechat_work,
    value: 6,
    name: 'sync.sync_wechat_users',
  },
  {
    icon: logo_dingtalk,
    value: 7,
    name: 'sync.sync_dingtalk_users',
  },
  {
    icon: logo_lark,
    value: 8,
    name: 'sync.sync_lark_users',
  },
])

const refresh = (res: any) => {
  showTips(res.successCount, res.errorCount, res.dataKey)
  if (res.successCount) {
    search()
  }
}

const handleSyncUser = (ele: any) => {
  currentPlatform.value = ele
  syncUserRef.value.open(ele.value, ele.name)
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

const loadData = () => {
  const url = '/system/platform'
  request.get(url).then((res: any) => {
    const idArr = res.filter((card: any) => card.valid && card.enable).map((ele: any) => ele.id)
    platformType.value = platformType.value.filter((card: any) => idArr.includes(card.value))
  })
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

const deleteValues = (index: number) => {
  state.form.system_variables.splice(index, 1)
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
  variablesApi.listAll().then((res: any) => {
    variables.value = res.filter((ele: any) => ele.type === 'custom')
    variableValueMap.value = variables.value.reduce((pre, next) => {
      pre[next.id] = {
        value: next.value,
        var_type: next.var_type,
        name: next.name,
      }
      return pre
    }, {})

    if (row) {
      state.form = {
        ...row,
        system_variables: (row.system_variables || []).map((ele: any) => ({
          ...ele,
          variableValue: ele.variableValues[0],
        })),
      }
    }
  })
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

const formatVariableValues = () => {
  if (!state.form.system_variables?.length) return []
  return state.form.system_variables.map((ele: any) => ({
    variableId: ele.variableId,
    variableValues:
      variableValueMap.value[ele.variableId].var_type === 'number'
        ? [ele.variableValue]
        : ele.variableValues,
  }))
}

const addTerm = () => {
  const { account, email, name, oid, status, oid_list } = state.form
  userApi
    .add({ account, email, name, oid, status, oid_list, system_variables: formatVariableValues() })
    .then(() => {
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
    .edit({
      account,
      id,
      create_time,
      email,
      language,
      name,
      oid,
      oid_list,
      origin,
      status,
      system_variables: formatVariableValues(),
    })
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

const validateSystemVariables = () => {
  const { system_variables = [] } = state.form
  if (system_variables?.length) {
    return system_variables.some((ele: any) => {
      const obj = variableValueMap.value[ele.variableId]
      if (obj.var_type !== 'number' && !ele.variableValues.length) {
        ElMessage.error(t('variables.​​cannot_be_empty'))
        return true
      }

      if (obj.var_type === 'number' && !ele.variableValue) {
        ElMessage.error(t('variables.​​cannot_be_empty'))
        return true
      }

      if (obj.var_type === 'number') {
        const [min, max] = obj.value
        if (ele.variableValue > max || ele.variableValue < min) {
          ElMessage.error(t('variables.1_to_100', { name: obj.name, min, max }))
          return true
        }
      }

      if (obj.var_type === 'datetime') {
        const [min, max] = obj.value
        const [minVal, maxVal] = ele.variableValues
        if (
          +new Date(minVal) > +new Date(max) ||
          +new Date(maxVal) < +new Date(min) ||
          +new Date(maxVal) > +new Date(max) ||
          +new Date(minVal) < +new Date(min)
        ) {
          ElMessage.error(
            t('variables.1_to_100_de', {
              name: obj.name,
              min,
              max,
            })
          )
          return true
        }
      }
    })
  }

  return false
}

const saveHandler = () => {
  termFormRef.value.validate((res: any) => {
    if (res) {
      if (validateSystemVariables()) return
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
  const originArray = [
    'CAS',
    'OIDC',
    'LDAP',
    'OAuth2',
    'SAML2',
    t('user.wecom'),
    t('user.dingtalk'),
    t('user.lark'),
    t('user.larksuite'),
  ]
  return originArray[origin - 1]
}

const showSyncBtn = ref(false)
onMounted(() => {
  // eslint-disable-next-line no-undef
  const obj = LicenseGenerator.getLicense()
  if (obj?.status === 'valid') {
    showSyncBtn.value = true
    loadData()
  } else {
    platformType.value = []
  }

  workspaceList().then((res) => {
    options.value = res || []
    filterOption.value[2].option = [...options.value]
  })
  search()
  loadDefaultPwd()
})
const downErrorExcel = (dataKey: any) => {
  userApi.errorRecord(dataKey).then((res: any) => {
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
  })
}

const showTips = (successCount: any, errorCount: any, dataKey: any) => {
  let title = successCount ? t('sync.sync_complete') : t('sync.sync_failed')
  const childrenDomList = [h('span', null, t('sync.synced_10_users', { num: successCount }))]
  const contentDomList = h(
    'div',
    {
      style: 'display: flex;align-items: center;',
    },
    childrenDomList
  )
  const headerDomList = [
    h(
      'div',
      {
        style: 'font-weight: 500;font-size: 16px;line-height: 24px;margin-bottom: 24px',
      },
      title
    ),

    contentDomList,
  ]

  if (successCount && errorCount) {
    childrenDomList.pop()
    const halfCountDom = h(
      'span',
      null,
      t('sync.failed_3_users', { success: successCount, failed: errorCount })
    )
    childrenDomList.push(halfCountDom)
  }

  if (!successCount && errorCount) {
    const errorCountDom = h('span', null, t('sync.failed_10_users', { num: errorCount }))
    childrenDomList.pop()
    childrenDomList.push(errorCountDom)
  }

  if (errorCount) {
    const errorDom = h('div', { class: 'error-record-tip flex-align-center' }, [
      h(
        ElButton,
        {
          onClick: () => downErrorExcel(dataKey),
          text: true,
          class: 'down-button',
        },
        t('sync.download_failure_list')
      ),
    ])

    childrenDomList.push(errorDom)
  }
  ElMessageBox.confirm('', {
    confirmButtonType: 'primary',
    autofocus: false,
    dangerouslyUseHTMLString: true,
    message: h(
      'div',
      { class: 'sync-tip-box' },

      headerDomList
    ),
    cancelButtonText: t('sync.return_to_view'),
    confirmButtonText: t('sync.continue_syncing'),
  })
    .then(() => {
      const { value, name } = currentPlatform.value
      syncUserRef.value.open(value, name)
    })
    .catch(() => {
      currentPlatform.value = null
    })
}
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
.ed-message-box:has(.sync-tip-box) {
  padding: 24px;
}
.sync-tip-box {
  .error-record-tip {
    display: inline-block;
  }
}
.sync-platform.sync-platform {
  padding: 4px 0;
  width: 180px !important;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border: 1px solid #dee0e3;

  .popover {
    .popover-content {
      padding: 4px;
      max-height: 300px;
      overflow-y: auto;
    }
    .popover-item {
      height: 32px;
      display: flex;
      align-items: center;
      padding-left: 12px;
      padding-right: 8px;
      position: relative;
      border-radius: 4px;
      cursor: pointer;

      &:not(:last-child) {
        margin-bottom: 2px;
      }

      &:hover {
        background: #1f23291a;
      }

      .model-name {
        margin-left: 8px;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        max-width: 220px;
      }
    }
  }
}
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
  .ed-form-item__label:has(.btn) {
    padding-right: 0;
    width: 100%;
    margin-bottom: 8px;
  }
  .value-list {
    width: 100%;
    padding: 16px;
    border-radius: 6px;
    background-color: #f5f6f7;
    .title {
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;
      margin-bottom: 8px;
      display: flex;
    }
    .item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;

      &:not(:last-child) {
        margin-bottom: 8px;
      }

      .action-btn {
        width: 24px;
        height: 24px;
        border-radius: 6px;
        cursor: pointer;
        color: #646a73;

        &:hover {
          background-color: #1f23291a;
        }
      }
    }
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
