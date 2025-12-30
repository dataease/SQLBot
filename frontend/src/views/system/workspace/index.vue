<script lang="ts" setup>
import { ref, computed, onMounted, reactive } from 'vue'
import {
  workspaceList,
  workspaceUserList,
  workspaceDelete,
  workspaceUwsDelete,
  workspaceCreate,
  workspaceUpdate,
  workspaceUwsUpdate,
} from '@/api/workspace'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import arrow_down from '@/assets/svg/arrow-down.svg'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import icon_form_outlined from '@/assets/svg/icon_moments-categories_outlined.svg'
import assigned from '@/assets/svg/icon_assigned_outlined.svg'
import AuthorizedWorkspaceDialog from './AuthorizedWorkspaceDialog.vue'
import rename from '@/assets/svg/icon_rename_outlined.svg'
import icon_member from '@/assets/svg/icon_member.svg'
import SuccessFilled from '@/assets/svg/gou_icon.svg'
import CircleCloseFilled from '@/assets/svg/icon_ban_filled.svg'
import { useI18n } from 'vue-i18n'
import delIcon from '@/assets/svg/icon_delete.svg'
import icon_more_outlined from '@/assets/svg/icon_more_outlined.svg'
import icon_done_outlined from '@/assets/svg/icon_done_outlined.svg'

import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const { t } = useI18n()
const multipleSelectionAll = ref<any[]>([])
const tableList = ref([] as any[])
const keyword = ref('')
const keywordsMember = ref('')
const oldKeywordsMember = ref('')
const workspaceFormRef = ref()
const authorizedWorkspaceDialog = ref()
const tableListWithSearch = computed(() => {
  if (!keyword.value) return tableList.value
  return tableList.value.filter((ele) =>
    ele.name.toLowerCase().includes(keyword.value.toLowerCase())
  )
})
const workspaceForm = reactive({
  name: '',
  id: '',
})

const userTypeList = [
  {
    name: t('workspace.administrator'),
    value: 1,
  },
  {
    name: t('workspace.ordinary_member'),
    value: 0,
  },
]

const handleUserTypeChange = (val: any, row: any) => {
  workspaceUwsUpdate({
    uid: row.id,
    oid: currentTable.value.id,
    weight: val,
  }).then(() => {
    ElMessage({
      type: 'success',
      message: t('common.save_success'),
    })
    search()
  })
}

const rules = {
  name: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('workspace.workspace_name'),
      trigger: 'blur',
    },
  ],
}
const fieldListWithSearch = computed(() => {
  if (!keyword.value) return fieldList.value
  return fieldList.value.filter((ele: any) =>
    ele.name.toLowerCase().includes(keywordsMember.value.toLowerCase())
  )
})
const currentTable = ref<any>({ id: 1, name: '' })
const init = () => {
  workspaceList().then((res) => {
    tableList.value = res
    if (currentTable.value.id) {
      tableList.value.forEach((ele: any) => {
        if (ele.id === currentTable.value.id) {
          currentTable.value.name = ele.name
          clickTable(ele)
        }
      })
    }
  })
}

const duplicateName = async () => {
  const res = await workspaceList()
  const names = res.filter((ele: any) => ele.id !== workspaceForm.id).map((ele: any) => ele.name)
  if (names.includes(workspaceForm.name)) {
    ElMessage.error(t('embedded.duplicate_name'))
    return
  }

  const req = workspaceForm.id ? workspaceUpdate : workspaceCreate
  req(workspaceForm).then(() => {
    ElMessage({
      type: 'success',
      message: t('common.save_success'),
    })
    init()
    fieldDialog.value = false
  })
}

onMounted(() => {
  init()
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

const clickTable = (table: any) => {
  currentTable.value = table
  pageInfo.currentPage = 1
  search()
}
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
      oid: currentTable.value.id,
    }).then(() => {
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
  ElMessageBox.confirm(t('workspace.member_feng_yibudao', { msg: row.name }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('workspace.remove'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    workspaceUwsDelete({
      uid_list: [row.id],
      oid: currentTable.value.id,
    }).then(() => {
      ElMessage({
        type: 'success',
        message: t('dashboard.delete_success'),
      })
      search()
    })
  })
}
const handleSelectionChange = (val: any[]) => {
  const ids = fieldList.value.map((ele: any) => ele.id)
  multipleSelectionAll.value = [
    ...multipleSelectionAll.value.filter((ele) => !ids.includes(ele.id)),
    ...val,
  ]
  isIndeterminate.value = !(val.length === 0 || val.length === fieldList.value.length)
  checkAll.value = val.length === fieldList.value.length
}
const handleCheckAllChange = (val: any) => {
  isIndeterminate.value = false
  handleSelectionChange(val ? fieldList.value : [])
  if (val) {
    handleToggleRowSelection()
  } else {
    multipleTableRef.value.clearSelection()
  }
}

const handleToggleRowSelection = (check: boolean = true) => {
  let i = 0
  const ids = multipleSelectionAll.value.map((ele: any) => ele.id)
  for (const key in fieldList.value) {
    if (ids.includes((fieldList.value[key] as any).id)) {
      i += 1
      multipleTableRef.value.toggleRowSelection(fieldList.value[key], check)
    }
  }
  checkAll.value = i === fieldList.value.length
  isIndeterminate.value = !(i === 0 || i === fieldList.value.length)
}

const handleAddMember = () => {
  authorizedWorkspaceDialog.value.open(currentTable.value.id)
}

const refresh = () => {
  search()
}
const search = ($event: any = {}) => {
  if ($event?.isComposing) {
    return
  }
  workspaceUserList(
    { oid: currentTable.value.id, keyword: keywordsMember.value },
    pageInfo.currentPage,
    pageInfo.pageSize
  ).then((res) => {
    fieldList.value = res.items.sort((a: any, b: any) => b.weight - a.weight)
    pageInfo.total = res.total
    oldKeywordsMember.value = keywordsMember.value
  })
}

const closeField = () => {
  fieldDialog.value = false
}

const saveField = () => {
  workspaceFormRef.value.validate((res: any) => {
    if (res) {
      duplicateName()
    }
  })
}

const delWorkspace = (row: any) => {
  ElMessageBox.confirm(t('workspace.workspace_de_workspace', { msg: row.name }), {
    confirmButtonType: 'danger',
    tip: t('workspace.operate_with_caution'),
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    workspaceDelete(row.id).then(async () => {
      ElMessage({
        type: 'success',
        message: t('dashboard.delete_success'),
      })
      init()
      if (row.id === currentTable.value.id) {
        currentTable.value = {}
      }
      if (row.id === userStore.getOid) {
        userStore.setOid('1')
        await userStore.info()
      }
    })
  })
}

const addWorkspace = (row: any) => {
  if (row) {
    workspaceForm.name = row.name
    workspaceForm.id = row.id
  } else {
    workspaceForm.name = ''
    workspaceForm.id = ''
  }
  fieldDialog.value = true
}

const handleSizeChange = (val: number) => {
  pageInfo.pageSize = val
  pageInfo.currentPage = 1
  search()
}
const handleCurrentChange = (val: number) => {
  pageInfo.currentPage = val
  search()
}
</script>

<template>
  <div class="workspace no-padding">
    <div class="side-list">
      <div class="select-table_top">
        {{ $t('user.workspace') }}

        <el-tooltip
          :offset="12"
          effect="dark"
          :content="$t('workspace.add_workspace')"
          placement="top"
        >
          <el-icon size="18" @click="addWorkspace">
            <icon_add_outlined></icon_add_outlined>
          </el-icon>
        </el-tooltip>
      </div>
      <el-input
        v-model="keyword"
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

      <div class="list-content">
        <el-scrollbar>
          <div
            v-for="ele in tableListWithSearch"
            :key="ele.name"
            class="model"
            :class="currentTable.name === ele.name && 'isActive'"
            :title="ele.name"
            @click="clickTable(ele)"
          >
            <el-icon size="16">
              <icon_form_outlined></icon_form_outlined>
            </el-icon>
            <span class="name">{{ ele.name }}</span>

            <el-popover
              trigger="click"
              :teleported="false"
              popper-class="popover-card_workspack"
              placement="bottom"
            >
              <template #reference>
                <el-icon
                  class="more"
                  size="16"
                  style="margin-left: auto; color: #646a73"
                  @click.stop
                >
                  <icon_more_outlined></icon_more_outlined>
                </el-icon>
              </template>
              <div class="content">
                <div class="item" @click.stop="addWorkspace(ele)">
                  <el-icon size="16">
                    <rename></rename>
                  </el-icon>
                  {{ $t('dashboard.rename') }}
                </div>
                <div v-if="ele.id !== 1" class="item" @click.stop="delWorkspace(ele)">
                  <el-icon size="16">
                    <delIcon></delIcon>
                  </el-icon>
                  {{ $t('dashboard.delete') }}
                </div>
              </div>
            </el-popover>
          </div>
        </el-scrollbar>

        <div v-if="!!keyword && !tableListWithSearch.length" class="no-result">
          {{ $t('workspace.relevant_content_found') }}
        </div>
      </div>
      <EmptyBackground
        v-if="!!keyword && !tableListWithSearch.length"
        :description="$t('datasource.relevant_content_found')"
        img-type="tree"
        style="width: 100%"
      />
    </div>

    <div v-if="currentTable.name" class="info-table">
      <div class="table-name">
        <div class="name">
          {{ currentTable.name }}
          <span class="line"></span>
          <el-icon style="margin: 0 4px 0 8px" size="16">
            <icon_member></icon_member>
          </el-icon>
          {{ pageInfo.total }}
        </div>
        <div class="notes">
          <el-button type="primary" @click="handleAddMember">
            <template #icon>
              <icon_add_outlined></icon_add_outlined>
            </template>
            {{ $t('workspace.add_member') }}
          </el-button>
          <el-input
            v-model="keywordsMember"
            clearable
            style="width: 232px"
            :placeholder="$t('workspace.name_username_email')"
            @keydown.enter.exact.prevent="search"
          >
            <template #prefix>
              <el-icon>
                <icon_searchOutline_outlined class="svg-icon" />
              </el-icon>
            </template>
          </el-input>
        </div>
      </div>
      <div class="table-content" :class="multipleSelectionAll.length && 'show-pagination_height'">
        <div class="preview-or-schema">
          <el-table
            ref="multipleTableRef"
            :data="fieldListWithSearch"
            style="width: 100%"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="55" />
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
            <el-table-column
              class-name="user-source"
              prop="weight"
              :label="$t('workspace.member_type')"
              width="120"
            >
              <template #default="scope">
                <el-popover popper-class="system-workspace_user" placement="bottom">
                  <template #reference>
                    <div style="display: flex; align-items: center; justify-content: space-between">
                      <span>{{
                        scope.row.weight === 1
                          ? t('workspace.administrator')
                          : t('workspace.ordinary_member')
                      }}</span>
                      <el-icon style="display: none" size="16">
                        <arrow_down></arrow_down>
                      </el-icon>
                    </div>
                  </template>
                  <div class="popover">
                    <div class="popover-content">
                      <div
                        v-for="ele in userTypeList"
                        :key="ele.name"
                        class="popover-item"
                        :class="ele.name === scope.row.user_source && 'isActive'"
                        @click="handleUserTypeChange(ele.value, scope.row)"
                      >
                        <div class="model-name">{{ ele.name }}</div>
                        <el-icon size="16" class="done">
                          <icon_done_outlined></icon_done_outlined>
                        </el-icon>
                      </div>
                    </div>
                  </div>
                </el-popover>
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
                    <el-icon class="action-btn" size="16" @click="deleteHandler(scope.row)">
                      <assigned></assigned>
                    </el-icon>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
            <template #empty>
              <EmptyBackground
                v-if="!oldKeywordsMember && !fieldListWithSearch.length"
                :description="$t('workspace.no_user')"
                img-type="noneWhite"
              />

              <EmptyBackground
                v-if="!!oldKeywordsMember && !fieldListWithSearch.length"
                :description="$t('datasource.relevant_content_found')"
                img-type="tree"
              />
            </template>
          </el-table>
        </div>
      </div>
      <div v-if="fieldListWithSearch.length" class="pagination-container">
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
  </div>
  <AuthorizedWorkspaceDialog
    ref="authorizedWorkspaceDialog"
    @refresh="refresh"
  ></AuthorizedWorkspaceDialog>
  <el-dialog
    v-model="fieldDialog"
    :title="$t(workspaceForm.id ? 'workspace.rename_a_workspace' : 'workspace.add_workspace')"
    width="420"
    destroy-on-close
    :close-on-click-modal="false"
    @before-closed="closeField"
  >
    <el-form
      ref="workspaceFormRef"
      :model="workspaceForm"
      label-width="180px"
      label-position="top"
      :rules="rules"
      class="form-content_error"
      @submit.prevent
    >
      <el-form-item prop="name" :label="t('workspace.workspace_name')">
        <el-input
          v-model="workspaceForm.name"
          clearable
          maxlength="50"
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('workspace.workspace_name')
          "
        />
      </el-form-item>
    </el-form>

    <div style="display: flex; justify-content: flex-end; margin-top: 20px">
      <el-button secondary @click="closeField">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" @click="saveField">{{
        t(workspaceForm.id ? 'common.save' : 'model.add')
      }}</el-button>
    </div>
  </el-dialog>
</template>

<style lang="less" scoped>
.workspace {
  height: 100%;
  position: relative;
  .side-list {
    width: 280px;
    padding: 8px 16px;
    height: 100%;
    border-right: 1px solid #1f232926;
    position: relative;
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
        position: relative;

        &:hover {
          &::after {
            display: block;
          }
        }

        &::after {
          content: '';
          display: none;
          position: absolute;
          width: 26px;
          height: 26px;
          background: var(--ed-color-primary-1a, #1cba901a);
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          border-radius: 6px;
        }
      }
    }

    .ed-input {
      margin: 8px;
    }

    .list-content {
      height: calc(100% - 100px);
      position: absolute;
      bottom: 0;
      left: 0;
      width: 100%;
      padding-left: 16px;

      .more {
        display: none;
        &.ed-icon {
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

          &:hover {
            &::after {
              display: block;
            }
          }
        }
      }

      .no-result {
        margin-top: 72px;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        text-align: center;
        color: #646a73;
      }
      .model {
        width: calc(100% - 16px);
        height: 40px;
        display: flex;
        align-items: center;
        padding-left: 8px;
        border-radius: 4px;
        cursor: pointer;
        padding-right: 8px;
        margin-bottom: 2px;

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
          .more {
            display: block;
          }
        }

        &.isActive {
          background: var(--ed-color-primary-1a, #1cba901a);
          color: var(--ed-color-primary);
        }
      }
    }
  }
  .info-table {
    position: absolute;
    right: 0;
    top: 0;
    width: calc(100% - 280px);
    height: 100%;
    .table-name {
      padding: 16px 24px 0 24px;

      .name {
        font-weight: 500;
        font-size: 16px;
        line-height: 24px;
        display: flex;
        align-items: center;
        .line {
          height: 16px;
          width: 1px;
          background: #bbbfc4;
          margin-left: 8px;
        }
      }

      .notes {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: 16px 0;
      }
    }

    .pagination-container {
      display: flex;
      justify-content: end;
      align-items: center;
      margin-top: 16px;
    }

    .table-content {
      padding: 0 24px 16px 24px;
      height: calc(100% - 168px);
      overflow-y: auto;

      &.show-pagination_height {
        height: calc(100% - 220px);
      }

      .preview-or-schema {
        :deep(.user-source) {
          cursor: pointer;
          &:hover {
            .ed-icon {
              display: block !important;
              transform: rotate(180deg);
            }
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
      }
    }

    .bottom-select {
      position: absolute;
      height: 64px;
      width: 100%;
      left: 0;
      bottom: 0;
      border-top: 1px solid #1f232926;
      display: flex;
      align-items: center;
      background-color: #fff;
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
  }
}
</style>
<style lang="less">
.popover-card_workspack.popover-card_workspack.popover-card_workspack {
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border-radius: 4px;
  border: 1px solid #dee0e3;
  width: fit-content !important;
  min-width: 120px !important;
  padding: 0;
  .content {
    position: relative;
    &::after {
      position: absolute;
      content: '';
      top: 40px;
      left: 0;
      width: 100%;
      height: 1px;
      background: #dee0e3;
    }
    .item {
      position: relative;
      padding: 0 12px;
      height: 40px;
      display: flex;
      align-items: center;
      cursor: pointer;
      .ed-icon {
        margin-right: 8px;
        color: #646a73;
      }
      &:hover {
        &::after {
          display: block;
        }
      }

      &::after {
        content: '';
        width: calc(100% - 8px);
        height: 32px;
        border-radius: 4px;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: #1f23291a;
        display: none;
      }
    }
  }
}

.system-workspace_user.system-workspace_user {
  padding: 0;
  width: 120px !important;
  min-width: 120px !important;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border: 1px solid #dee0e3;

  .popover {
    .popover-content {
      padding: 4px;
      position: relative;
      &::after {
        position: absolute;
        content: '';
        left: 0;
        top: 40px;
        width: 100%;
        height: 1px;
        background: #1f232926;
      }
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
      &:hover {
        background: #1f23291a;
      }

      &:nth-child(2) {
        margin: 9px 0 0 0;
      }

      .model-name {
        margin-left: 8px;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
      }

      .done {
        margin-left: auto;
        display: none;
      }

      &.isActive {
        color: var(--ed-color-primary);

        .done {
          display: block;
        }
      }
    }
  }
}
</style>
