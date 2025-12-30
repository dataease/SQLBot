<script lang="ts" setup>
import { ref, onMounted, reactive, nextTick } from 'vue'
import {
  uwsOption,
  workspaceUserList,
  workspaceUwsDelete,
  workspaceUwsCreate,
} from '@/api/workspace'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import assigned from '@/assets/svg/icon_assigned_outlined.svg'
import SuccessFilled from '@/assets/svg/gou_icon.svg'
import CircleCloseFilled from '@/assets/svg/icon_ban_filled.svg'
import { useUserStore } from '@/stores/user'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const multipleSelectionAll = ref<any[]>([])
const keywordsMember = ref('')
const userStore = useUserStore()
const searchLoading = ref(false)

const workspaceForm = reactive({
  name: '',
  id: '',
})
const selectable = (row: any) => {
  if (+userStore.getUid === 1) {
    return true
  }
  return ![userStore.getUid].includes(row.id) && row.weight !== 1
}
onMounted(() => {
  search()
})
const fieldDialog = ref<boolean>(false)
const multipleTableRef = ref()
const isIndeterminate = ref(true)
const checkAll = ref(false)
const fieldList = ref<any>([])
const pageInfo = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0,
})

const cancelDelete = () => {
  handleToggleRowSelection(false)
  multipleSelectionAll.value = []
  checkAll.value = false
  isIndeterminate.value = false
}
const deleteBatchUser = () => {
  ElMessageBox.confirm(
    t('workspace.selected_2_members', { msg: multipleSelectionAll.value.length }),
    {
      confirmButtonType: 'danger',
      confirmButtonText: t('workspace.remove'),
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
    }
  ).then(() => {
    workspaceUwsDelete({
      uid_list: multipleSelectionAll.value.map((ele) => ele.id),
    }).then(() => {
      ElMessage({
        type: 'success',
        message: t('workspace.removed_successfully'),
      })
      multipleSelectionAll.value = []
      search()
    })
  })
}
const deleteHandler = (row: any) => {
  if (row.weight === 1 && +userStore.getUid !== 1) return
  ElMessageBox.confirm(t('workspace.member_feng_yibudao', { msg: row.name }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('workspace.remove'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    workspaceUwsDelete({
      uid_list: [row.id],
    }).then(() => {
      multipleSelectionAll.value = multipleSelectionAll.value.filter((ele) => row.id !== ele.id)
      ElMessage({
        type: 'success',
        message: t('workspace.removed_successfully'),
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
    ...multipleSelectionAll.value.filter((ele) => !ids.includes(ele.id)),
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
  workspaceUserList(
    keywordsMember.value ? { keyword: keywordsMember.value } : {},
    pageInfo.currentPage,
    pageInfo.pageSize
  )
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
      searchLoading.value = false
    })
}

const closeField = () => {
  fieldDialog.value = false
  afterFind.value = false
  userInfo.value.id = ''
  userInfo.value.name = ''
  userInfo.value.account = ''
}

const saveField = () => {
  workspaceUwsCreate({
    uid_list: [userInfo.value.id],
  }).then(() => {
    ElMessage({
      type: 'success',
      message: t('common.save_success'),
    })
    search()
    closeField()
  })
}

const userInfo = ref({
  id: '',
  name: '',
  account: '',
})
const afterFind = ref(false)
const findUser = () => {
  if (!workspaceForm.name) return
  uwsOption({ keyword: workspaceForm.name })
    .then((res: any) => {
      userInfo.value = res || {}
    })
    .finally(() => {
      afterFind.value = true
    })
}

const addWorkspace = () => {
  afterFind.value = false
  workspaceForm.name = ''
  fieldDialog.value = true
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
  <div v-loading="searchLoading" class="member">
    <div class="tool-left">
      <span class="page-title">{{ $t('workspace.member_management') }}</span>
      <div class="search-bar">
        <el-input
          v-model="keywordsMember"
          style="width: 240px; margin-right: 12px"
          :placeholder="$t('user.name_account_email')"
          clearable
          @keydown.enter.exact.prevent="search"
        >
          <template #prefix>
            <el-icon>
              <icon_searchOutline_outlined />
            </el-icon>
          </template>
        </el-input>

        <el-button type="primary" @click="addWorkspace()">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('workspace.add_member') }}
        </el-button>
      </div>
    </div>
    <div class="table-content" :class="multipleSelectionAll.length && 'show-pagination_height'">
      <div class="preview-or-schema">
        <el-table
          ref="multipleTableRef"
          :data="fieldList"
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
          <el-table-column :selectable="selectable" type="selection" width="55" />
          <el-table-column prop="name" :label="$t('user.name')" width="160" />
          <el-table-column prop="account" :label="$t('user.account')" width="160" />
          <el-table-column prop="status" :label="$t('user.user_status')">
            <template #default="scope">
              <div
                class="user-status-container"
                :class="[scope.row.status ? 'active' : 'disabled']"
              >
                <el-icon size="16">
                  <SuccessFilled v-if="scope.row.status" />
                  <CircleCloseFilled v-else />
                </el-icon>
                <span>{{ $t(`user.${scope.row.status ? 'enabled' : 'disabled'}`) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="email" :label="$t('user.email')" width="204" />
          <el-table-column prop="weight" :label="$t('workspace.member_type')" width="120">
            <template #default="scope">
              <span>{{
                scope.row.weight === 1
                  ? t('workspace.administrator')
                  : t('workspace.ordinary_member')
              }}</span>
            </template>
          </el-table-column>
          <el-table-column fixed="right" width="80" :label="t('ds.actions')">
            <template #default="scope">
              <div class="field-comment">
                <el-tooltip
                  :offset="14"
                  effect="dark"
                  :content="$t('workspace.remove')"
                  placement="top"
                >
                  <el-icon
                    class="action-btn"
                    :class="+userStore.getUid !== 1 && scope.row.weight === 1 && 'not-allow'"
                    size="16"
                    @click="deleteHandler(scope.row)"
                  >
                    <assigned></assigned>
                  </el-icon>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <EmptyBackground
              v-if="!keywordsMember && !fieldList.length"
              :description="$t('workspace.no_user')"
              img-type="noneWhite"
            />

            <EmptyBackground
              v-if="!!keywordsMember && !fieldList.length"
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

      <button class="danger-button" @click="deleteBatchUser">{{ $t('workspace.remove') }}</button>

      <span class="selected">{{
        $t('user.selected_2_items', { msg: multipleSelectionAll.length })
      }}</span>

      <el-button text @click="cancelDelete">
        {{ $t('common.cancel') }}
      </el-button>
    </div>
  </div>

  <el-dialog
    v-model="fieldDialog"
    :title="$t('workspace.add_member')"
    width="600"
    modal-class="add-user_dialog"
    destroy-on-close
    :close-on-click-modal="false"
    @before-closed="closeField"
  >
    <el-input
      v-model="workspaceForm.name"
      clearable
      :class="workspaceForm.name && 'value-input'"
      :placeholder="$t('workspace.id_account_to_add')"
    >
      <template #append>
        <span style="cursor: pointer" @click="findUser">{{ t('workspace.find_user') }}</span>
      </template>
    </el-input>
    <div class="user">
      <template v-if="userInfo.id">
        <div class="name">{{ userInfo.name }}</div>
        <div class="account">{{ userInfo.account }}</div>
      </template>
      <div v-else-if="afterFind" class="empty">{{ $t('common.may_not_exist') }}</div>
    </div>
    <div style="display: flex; justify-content: flex-end; margin-top: 20px">
      <el-button secondary @click="closeField">{{ t('common.cancel') }}</el-button>
      <el-button v-if="!userInfo.id" disabled type="info">{{ t('model.add') }}</el-button>
      <el-button v-else type="primary" @click="saveField">{{ t('model.add') }}</el-button>
    </div>
  </el-dialog>
</template>

<style lang="less" scoped>
.member {
  height: 100%;
  position: relative;
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
.add-user_dialog {
  .ed-input-group__append {
    background-color: #fff;
    padding: 0 12px;
  }

  .value-input {
    .ed-input-group__append {
      color: #1f2329;
      position: relative;
      &:hover {
        &::after {
          content: '';
          position: absolute;
          left: -1px;
          top: 0;
          width: calc(100% - 1px);
          height: calc(100% - 2px);
          background: var(--ed-color-primary-1a, #1cba901a);
          border: 1px solid var(--ed-color-primary);
          border-bottom-right-radius: 6px;
          border-top-right-radius: 6px;
          pointer-events: none;
        }
      }
    }
  }
  .user {
    height: 126px;
    font-weight: 400;
    padding-top: 16px;

    .name {
      font-size: 14px;
      line-height: 22px;
    }
    .account {
      color: #8f959e;
      font-size: 12px;
      line-height: 20px;
    }

    .empty {
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;
      color: #8f959e;
    }
  }
}
</style>
