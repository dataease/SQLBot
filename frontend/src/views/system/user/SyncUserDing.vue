<template>
  <el-dialog
    v-model="centerDialogVisible"
    :title="$t(dialogTitle)"
    modal-class="sync-user_ding"
    width="840"
  >
    <div v-loading="loading" class="flex border" style="height: 428px; border-radius: 6px">
      <div class="p-16 border-r">
        <el-input
          v-model="search"
          :validate-event="false"
          :placeholder="$t('datasource.search')"
          style="width: 364px; margin-left: 16px"
          clearable
        >
          <template #prefix>
            <el-icon>
              <Search></Search>
            </el-icon>
          </template>
        </el-input>
        <div class="mt-8 max-height_workspace">
          <el-tree
            ref="organizationUserRef"
            style="max-width: 426px"
            class="checkbox-group-block"
            :data="organizationUserList"
            :filter-node-method="filterNode"
            show-checkbox
            :default-checked-keys="defaultCheckedKeys"
            @check="handleCheck"
            :props="defaultProps"
            node-key="id"
            default-expand-all
            :expand-on-click-node="false"
          >
            <template #default="{ node, data }">
              <div class="custom-tree-node flex">
                <el-icon size="28">
                  <avatar_organize v-if="!data.options.is_user"></avatar_organize>
                  <avatar_personal v-else></avatar_personal>
                </el-icon>
                <span class="ml-8 ellipsis" style="max-width: 40%" :title="node.label">
                  {{ node.label }}</span
                >
                <span class="account ellipsis ml-8" style="max-width: 40%" :title="data.id"
                  >({{ data.id }})</span
                >
              </div>
            </template>

            <template #empty>
              {{ $t(!!search ? 'dashboard.no_data' : 'qa.no_data') }}
            </template>
          </el-tree>
        </div>
      </div>
      <div class="p-16 w-full">
        <div class="flex-between mb-16" style="margin: 0 16px">
          <span class="lighter">
            {{ $t('workspace.selected_2_people', { msg: checkTableList.length }) }}
          </span>

          <el-button text @click="clearWorkspaceAll">
            {{ $t('workspace.clear') }}
          </el-button>
        </div>
        <div
          v-for="ele in checkTableList"
          :key="ele.name"
          style="margin: 0 16px; position: relative"
          class="flex-between align-center hover-bg_select"
        >
          <div
            :title="`${ele.name}(${ele.id})`"
            class="flex align-center ellipsis"
            style="width: 100%"
          >
            <el-icon size="28">
              <avatar_personal></avatar_personal>
            </el-icon>
            <span class="ml-8 lighter ellipsis" style="max-width: 40%" :title="ele.name">{{
              ele.name
            }}</span>
            <span class="account ellipsis ml-8" style="max-width: 40%" :title="ele.id"
              >({{ ele.id }})</span
            >
          </div>
          <el-button class="close-btn" text>
            <el-icon size="16" @click="clearWorkspace(ele)"><Close /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <template #footer>
      <el-checkbox style="float: left" v-model="existingUser">
        {{ $t('sync.the_existing_user') }}
      </el-checkbox>
      <el-button secondary @click="centerDialogVisible = false">
        {{ $t('common.cancel') }}</el-button
      >
      <el-button v-if="!checkTableList.length" disabled type="info">{{
        $t('common.confirm2')
      }}</el-button>
      <el-button v-else type="primary" @click="handleConfirm">
        {{ $t('common.confirm2') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script lang="ts" setup>
import { ref, computed, watch, nextTick } from 'vue'
import { modelApi } from '@/api/system'
import { ElLoading } from 'element-plus-secondary'
import avatar_personal from '@/assets/svg/avatar_personal.svg'
import avatar_organize from '@/assets/svg/avatar_organize.svg'
import Close from '@/assets/svg/icon_close_outlined_w.svg'
import Search from '@/assets/svg/icon_search-outline_outlined.svg'
import type { CheckboxValueType } from 'element-plus-secondary'
import type { FilterNodeMethodFunction } from 'element-plus-secondary'
import { cloneDeep } from 'lodash-es'
const checkAll = ref(false)
const existingUser = ref(false)
const isIndeterminate = ref(false)
const checkedWorkspace = ref<any[]>([])
const workspace = ref<any[]>([])
const search = ref('')
const dialogTitle = ref('')
const organizationUserRef = ref()
const defaultCheckedKeys = ref<any[]>([])
const defaultProps = {
  children: 'children',
  label: 'name',
}
let rawTree: any = []
const organizationUserList = ref<any[]>([])
const loading = ref(false)
const centerDialogVisible = ref(false)
const checkTableList = ref([] as any[])

const workspaceWithKeywords = computed(() => {
  return workspace.value.filter((ele: any) =>
    (ele.name.toLowerCase() as string).includes(search.value.toLowerCase())
  )
})

const dfsTree = (arr: any) => {
  return arr.filter((ele: any) => {
    if (ele.children?.length) {
      ele.children = dfsTree(ele.children)
    }
    if (
      (ele.name.toLowerCase() as string).includes(search.value.toLowerCase()) ||
      ele.children?.length
    ) {
      return true
    }
    return false
  })
}

const dfsTreeIds = (arr: any, ids: any) => {
  return arr.filter((ele: any) => {
    if (ele.children?.length) {
      ele.children = dfsTreeIds(ele.children, ids)
    }
    if (
      (ele.name.toLowerCase() as string).includes(search.value.toLowerCase()) ||
      ele.children?.length
    ) {
      ids.push(ele.id)
      return true
    }
    return false
  })
}

watch(search, () => {
  organizationUserList.value = dfsTree(cloneDeep(rawTree))
  nextTick(() => {
    organizationUserRef.value.setCheckedKeys(checkTableList.value.map((ele: any) => ele.id))
  })
})

const filterNode: FilterNodeMethodFunction = (value: string, data: any) => {
  if (!value) return true
  return data.name.includes(value)
}

function isLeafNode(node: any) {
  return node.options.is_user
}

const handleCheck = () => {
  const treeIds: any = []
  dfsTreeIds(cloneDeep(rawTree), treeIds)
  const checkNodes = organizationUserRef.value.getCheckedNodes()
  const checkNodesIds = checkNodes.map((ele: any) => ele.id)
  checkTableList.value = checkTableList.value.filter(
    (ele: any) =>
      !treeIds.includes(ele.id) || (treeIds.includes(ele.id) && checkNodesIds.includes(ele.id))
  )
  const userList = [...checkNodes, ...checkTableList.value]
  let idArr = [...new Set(userList.map((ele: any) => ele.id))]

  checkTableList.value = userList.filter((ele: any) => {
    if (idArr.includes(ele.id) && isLeafNode(ele)) {
      idArr = idArr.filter((itx: any) => itx !== ele.id)
      return true
    }
    return false
  })
}

const handleCheckedWorkspaceChange = (value: CheckboxValueType[]) => {
  const checkedCount = value.length
  checkAll.value = checkedCount === workspaceWithKeywords.value.length
  isIndeterminate.value = checkedCount > 0 && checkedCount < workspaceWithKeywords.value.length
  const tableNameArr = workspaceWithKeywords.value.map((ele: any) => ele.name)
  checkTableList.value = [
    ...new Set([
      ...checkTableList.value.filter((ele: any) => !tableNameArr.includes(ele.name)),
      ...value,
    ]),
  ]
  organizationUserRef.value.setCheckedKeys(checkTableList.value.map((ele: any) => ele.id))
}
let oid: any = null

const open = async (id: any, title: any) => {
  dialogTitle.value = title
  loading.value = true
  search.value = ''
  oid = id
  checkedWorkspace.value = []
  checkTableList.value = []
  checkAll.value = false
  isIndeterminate.value = false
  const loadingInstance = ElLoading.service({ fullscreen: true })
  const systemWorkspaceList = await modelApi.platform(id)
  organizationUserList.value = systemWorkspaceList.tree || []
  rawTree = cloneDeep(systemWorkspaceList.tree)
  loadingInstance?.close()
  loading.value = false
  centerDialogVisible.value = true
}
const emits = defineEmits(['refresh'])
const handleConfirm = () => {
  modelApi
    .userSync({
      user_list: checkTableList.value.map((ele: any) => ({
        id: ele.id,
        name: ele.name,
        email: ele.options.email || '',
      })),
      origin: oid,
      cover: existingUser.value,
    })
    .then((res: any) => {
      centerDialogVisible.value = false
      emits('refresh', res)
    })
}

const clearWorkspace = (val: any) => {
  checkedWorkspace.value = checkedWorkspace.value.filter((ele: any) => ele.id !== val.id)
  checkTableList.value = checkTableList.value.filter((ele: any) => ele.id !== val.id)
  handleCheckedWorkspaceChange(checkedWorkspace.value)
}

const clearWorkspaceAll = () => {
  checkedWorkspace.value = []
  checkTableList.value = []
  handleCheckedWorkspaceChange([])
}

defineExpose({
  open,
})
</script>
<style lang="less">
.sync-user_ding {
  .mb-8 {
    margin-bottom: 8px;
  }

  .ed-checkbox {
    margin-right: 0;
    position: relative;
  }

  .hover-bg,
  .hover-bg_select {
    &:hover {
      &::after {
        content: '';
        height: 44px;
        width: calc(100% + 34px);
        background: #1f23291a;
        position: absolute;
        border-radius: 6px;
        top: 50%;
        transform: translateY(-50%);
        left: -8px;
        z-index: 1;
      }
    }
  }

  .hover-bg_select {
    &:hover {
      &::after {
        width: calc(100% + 16px);
      }
    }
  }

  .ed-tree__empty-block {
    margin-top: 147px;
    color: #646a73;
  }

  .mt-16 {
    margin-top: 16px;
  }

  .p-16 {
    padding: 16px 0;
  }

  .lighter {
    font-weight: 400;
    font-size: 14px;
    line-height: 22px;
  }

  .checkbox-group-block {
    margin: 0 8px;
    --ed-tree-node-content-height: 44px;
  }

  .ed-tree-node__content {
    border-radius: 6px;
  }

  .custom-tree-node {
    width: 82%;
    align-items: center;

    .account {
      color: #8f959e;
    }
  }

  .close-btn {
    position: relative;
    z-index: 10;
    height: 24px;
    line-height: 24px;
    &:hover,
    &:active,
    &:focus {
      background: #1f23291a !important;
    }
  }

  .border {
    border: 1px solid #dee0e3;
  }

  .w-full {
    height: 100%;
    width: 50%;
    overflow-y: auto;

    .flex-between {
      height: 44px;
    }
  }

  .mt-8 {
    margin-top: 8px;
  }

  .max-height_workspace {
    max-height: calc(100% - 24px);
    overflow-y: auto;
  }

  .align-center {
    align-items: center;
  }

  .flex-between {
    display: flex;
    justify-content: space-between;
  }

  .ml-4 {
    margin-left: 4px;
  }

  .ml-8 {
    margin-left: 8px;
  }

  .flex {
    display: flex;
    .account {
      color: #8f959e;
    }
  }

  .border-r {
    border-right: 1px solid #dee0e3;
    width: 50%;
    overflow: hidden;
  }
}
</style>
