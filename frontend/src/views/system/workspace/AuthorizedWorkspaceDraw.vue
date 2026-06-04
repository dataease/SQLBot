<template>
  <el-drawer
    v-model="drawerVisible"
    :title="$t('authorized_space.authorized_space_list')"
    size="840px"
    class="authorized-workspace-drawer"
    @closed="handleDrawerClosed"
  >
    <div v-loading="loading" class="drawer-body">
      <div class="top-row">
        <span class="lighter">
          {{ $t('authorized_space.workspaces_authorized', { num: filteredList.length }) }}
        </span>

        <div class="detail" @click="handleAddWorkspace">
          <el-icon style="margin-right: 4px" size="16">
            <icon_add_outlined></icon_add_outlined>
          </el-icon>
          {{ $t('authorized_space.authorized_space') }}
        </div>
      </div>

      <div class="search-row">
        <el-input
          v-model="keywords"
          clearable
          :placeholder="$t('datasource.search')"
          @input="onKeywordChange"
        >
          <template #prefix>
            <el-icon>
              <icon_searchOutline_outlined />
            </el-icon>
          </template>
        </el-input>
      </div>

      <div
        class="table-content"
        :class="{ 'show-pagination-height': multipleSelectionAll.length > 0 }"
      >
        <el-table
          ref="multipleTableRef"
          :data="pageList"
          :row-key="getRowId"
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" :reserve-selection="true" width="55" />
          <el-table-column prop="name" :label="$t('user.workspace')" min-width="220" />
          <el-table-column
            v-if="false"
            prop="memberCount"
            :label="$t('authorized_space.number_of_members')"
            width="140"
          />
          <el-table-column :label="t('ds.actions')" width="100" fixed="right">
            <template #default="scope">
              <div class="field-comment">
                <el-tooltip
                  :offset="14"
                  effect="dark"
                  :content="$t('workspace.remove')"
                  placement="top"
                >
                  <el-icon class="action-btn" size="16" @click="deleteHandler(scope.row)">
                    <icon_block_outlined />
                  </el-icon>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <EmptyBackground
              v-if="!oldKeywordsMember && !filteredList.length"
              :description="$t('authorized_space.no_workspace')"
              img-type="noneWhite"
            />

            <EmptyBackground
              v-if="!!oldKeywordsMember && !filteredList.length"
              :description="$t('datasource.relevant_content_found')"
              img-type="tree"
            />
          </template>
        </el-table>
      </div>

      <div v-if="filteredList.length" class="pagination-container">
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

        <el-button text @click="cancelDelete">{{ $t('common.cancel') }}</el-button>
      </div>
    </div>
  </el-drawer>

  <AuthorizedWorkspaceDialogForModelAdd
    ref="authorizedWorkspaceDialogForModelAdd"
    @refresh="refresh"
  />
</template>

<script lang="ts" setup>
import { ref, computed, reactive, nextTick } from 'vue'
import { workspaceModelMapping, workspaceModelMappingDelete, workspaceList } from '@/api/workspace'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import icon_block_outlined from '@/assets/svg/icon_block_outlined.svg'
import AuthorizedWorkspaceDialogForModelAdd from './AuthorizedWorkspaceDialogForModelAdd.vue'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { useI18n } from 'vue-i18n'

const emit = defineEmits<{
  (e: 'refresh'): void
}>()

const { t } = useI18n()

const drawerVisible = ref(false)
const loading = ref(false)
const keywords = ref('')
const oldKeywordsMember = ref('')
const aiModelId = ref<string | null>(null)

const rawList = ref<any[]>([])
const multipleSelectionAll = ref<any[]>([])
const multipleTableRef = ref()
const authorizedWorkspaceDialogForModelAdd = ref()
const selectionSyncing = ref(false)
const checkAll = ref(false)
const isIndeterminate = ref(false)
const selectedRowMap = ref<Map<string, any>>(new Map())

const pageInfo = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0,
})

const filteredList = computed(() => {
  if (!keywords.value) return rawList.value
  return rawList.value.filter((ele: any) =>
    `${ele.name || ''}`.toLowerCase().includes(keywords.value.toLowerCase())
  )
})

const pageList = computed(() => {
  const start = (pageInfo.currentPage - 1) * pageInfo.pageSize
  const end = start + pageInfo.pageSize
  return filteredList.value.slice(start, end)
})

const getRowId = (row: any) => `${row.id}`

const syncSelectedRows = () => {
  multipleSelectionAll.value = Array.from(selectedRowMap.value.values())
}

const setPageTotal = () => {
  pageInfo.total = filteredList.value.length
  const maxPage = Math.max(1, Math.ceil(pageInfo.total / pageInfo.pageSize))
  if (pageInfo.currentPage > maxPage) {
    pageInfo.currentPage = maxPage
  }
}

const refreshSelectionState = () => {
  const checkedCount = pageList.value.filter((row: any) =>
    selectedRowMap.value.has(getRowId(row))
  ).length
  checkAll.value = pageList.value.length > 0 && checkedCount === pageList.value.length
  isIndeterminate.value = checkedCount > 0 && checkedCount < pageList.value.length
}

const handleToggleRowSelection = (check = true) => {
  if (!multipleTableRef.value) return
  selectionSyncing.value = true
  multipleTableRef.value.clearSelection()
  if (check) {
    for (const row of pageList.value) {
      if (selectedRowMap.value.has(getRowId(row))) {
        multipleTableRef.value.toggleRowSelection(row, true)
      }
    }
  }
  selectionSyncing.value = false
  refreshSelectionState()
}

const handleSelectionChange = (val: any[]) => {
  if (selectionSyncing.value) return
  const pageIdSet = new Set(pageList.value.map((row: any) => getRowId(row)))
  for (const id of pageIdSet) {
    selectedRowMap.value.delete(id)
  }
  for (const row of val) {
    selectedRowMap.value.set(getRowId(row), row)
  }
  syncSelectedRows()
  refreshSelectionState()
}

const handleCheckAllChange = (val: boolean) => {
  for (const row of pageList.value) {
    const id = getRowId(row)
    if (val) {
      selectedRowMap.value.set(id, row)
    } else {
      selectedRowMap.value.delete(id)
    }
  }
  syncSelectedRows()
  handleToggleRowSelection()
}

const cancelDelete = () => {
  selectedRowMap.value.clear()
  multipleSelectionAll.value = []
  checkAll.value = false
  isIndeterminate.value = false
  handleToggleRowSelection(false)
}

const toMemberCount = (row: any) => {
  return row.memberCount ?? row.member_count ?? row.userCount ?? row.user_count ?? row.count ?? 0
}

const loadData = async () => {
  if (!aiModelId.value) return
  loading.value = true
  try {
    const [mappingResult, workspaceResult] = await Promise.all([
      workspaceModelMapping(aiModelId.value),
      workspaceList(),
    ])
    const ids = new Set((mappingResult || []).map((id: any) => `${id}`))
    rawList.value = (workspaceResult || [])
      .filter((ele: any) => ids.has(`${ele.id}`))
      .map((ele: any) => ({
        ...ele,
        memberCount: toMemberCount(ele),
      }))
    const latestRowMap = new Map(rawList.value.map((row: any) => [getRowId(row), row]))
    for (const id of Array.from(selectedRowMap.value.keys())) {
      const latest = latestRowMap.get(id)
      if (!latest) {
        selectedRowMap.value.delete(id)
      } else {
        selectedRowMap.value.set(id, latest)
      }
    }
    syncSelectedRows()
    setPageTotal()
    await nextTick()
    handleToggleRowSelection()
  } finally {
    loading.value = false
  }
}

const deleteByIds = (ids: string[]) => {
  if (!aiModelId.value || !ids.length) return
  workspaceModelMappingDelete(aiModelId.value, ids).then(async () => {
    ElMessage({
      type: 'success',
      message: t('workspace.removed_successfully'),
    })
    for (const id of ids) {
      selectedRowMap.value.delete(id)
    }
    syncSelectedRows()
    await loadData()
  })
}

const deleteHandler = (row: any) => {
  ElMessageBox.confirm(t('authorized_space.delete_workspace', { msg: row.name }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('workspace.remove'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    deleteByIds([`${row.id}`])
  })
}

const deleteBatchUser = () => {
  ElMessageBox.confirm(
    t('authorized_space.delete_selected_workspaces', { msg: multipleSelectionAll.value.length }),
    {
      confirmButtonType: 'danger',
      confirmButtonText: t('workspace.remove'),
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
    }
  ).then(() => {
    deleteByIds(multipleSelectionAll.value.map((ele: any) => `${ele.id}`))
  })
}

const handleSizeChange = (val: number) => {
  pageInfo.pageSize = val
  pageInfo.currentPage = 1
  setPageTotal()
  nextTick(() => handleToggleRowSelection())
}

const handleCurrentChange = (val: number) => {
  pageInfo.currentPage = val
  nextTick(() => handleToggleRowSelection())
}

const onKeywordChange = () => {
  pageInfo.currentPage = 1
  setPageTotal()
  oldKeywordsMember.value = keywords.value
  nextTick(() => {
    handleToggleRowSelection()
  })
}

const handleAddWorkspace = () => {
  authorizedWorkspaceDialogForModelAdd.value?.open(aiModelId.value)
}

const refresh = () => {
  loadData()
}

const handleDrawerClosed = () => {
  emit('refresh')
}

const open = async (id: string | number) => {
  aiModelId.value = `${id}`
  keywords.value = ''
  oldKeywordsMember.value = ''
  selectedRowMap.value.clear()
  multipleSelectionAll.value = []
  checkAll.value = false
  isIndeterminate.value = false
  pageInfo.currentPage = 1
  drawerVisible.value = true
  await loadData()
}

defineExpose({
  open,
})
</script>

<style lang="less" scoped>
.authorized-workspace-drawer {
  .drawer-body {
    height: 100%;
    display: flex;
    flex-direction: column;
    position: relative;
  }

  .top-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;

    .detail {
      cursor: pointer;
      margin-left: auto;
      display: flex;
      align-items: center;
      position: relative;
      font-size: 14px;
      line-height: 22px;
      &:hover {
        &::after {
          content: '';
          background: #1f23291a;
          border-radius: 6px;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 84px;
          height: 26px;
          position: absolute;
        }
      }
    }

    .lighter {
      font-weight: 500;
      font-size: 14px;
      line-height: 22px;
    }
  }

  .search-row {
    margin-bottom: 12px;
  }

  .table-content {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding-bottom: 64px;

    &.show-pagination-height {
      padding-bottom: 0;
    }
  }

  .pagination-container {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
    margin-bottom: 64px;
  }

  .action-btn {
    cursor: pointer;
  }

  .field-comment {
    height: 24px;

    .action-btn {
      position: relative;
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

  .empty-text {
    padding: 20px 0;
    text-align: center;
    color: #8f959e;
  }

  .bottom-select {
    position: absolute;
    height: 64px;
    width: calc(100% + 48px);
    left: -24px;
    bottom: -79px;
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
      color: #646a73;
      font-size: 14px;
      line-height: 22px;
    }

    .ed-button {
      margin-left: 12px;
    }
  }
}
</style>
