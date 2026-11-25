<template>
  <div class="select-user_permission">
    <p class="lighter-bold">{{ $t('permission.select_restricted_user') }}</p>
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
          <el-checkbox
            v-model="checkAll"
            class="mb-8"
            style="margin-left: 16px"
            :indeterminate="isIndeterminate"
            @change="handleCheckAllChange"
          >
            {{ $t('datasource.select_all') }}
          </el-checkbox>
          <el-checkbox-group
            v-show="workspaceWithKeywords.length"
            v-model="checkedWorkspace"
            class="checkbox-group-block"
            @change="handleCheckedWorkspaceChange"
          >
            <el-checkbox
              v-for="space in workspaceWithKeywords"
              :key="space.id"
              :label="space.name"
              :value="space"
              class="hover-bg"
            >
              <div class="flex">
                <el-icon size="28">
                  <avatar_personal></avatar_personal>
                </el-icon>
                <span class="ml-4 ellipsis" style="max-width: 40%" :title="space.name">
                  {{ space.name }}</span
                >
                <span class="account ellipsis" style="max-width: 40%" :title="space.account"
                  >({{ space.account }})</span
                >
              </div>
            </el-checkbox>
          </el-checkbox-group>
          <div v-if="!workspaceWithKeywords.length" class="empty-members">
            {{ $t('permission.no_user_found') }}
          </div>
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
          :key="ele.id"
          style="margin: 0 16px; position: relative"
          class="flex-between align-center hover-bg_select"
        >
          <div class="flex align-center ellipsis" style="width: 100%">
            <el-icon size="28">
              <avatar_personal></avatar_personal>
            </el-icon>
            <span class="ml-4 lighter ellipsis" style="max-width: 40%" :title="ele.name">{{
              ele.name
            }}</span>
            <span class="account ellipsis" style="max-width: 40%" :title="ele.account"
              >({{ ele.account }})</span
            >
          </div>
          <el-button class="close-btn" text>
            <el-icon size="16" @click="clearWorkspace(ele)"><Close /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, watch } from 'vue'
import { workspaceUserList } from '@/api/workspace'
import avatar_personal from '@/assets/svg/avatar_personal.svg'
import Close from '@/assets/svg/icon_close_outlined_w.svg'
import Search from '@/assets/svg/icon_search-outline_outlined.svg'
import type { CheckboxValueType } from 'element-plus-secondary'
const checkAll = ref(false)
const isIndeterminate = ref(false)
const checkedWorkspace = ref<any[]>([])
const workspace = ref<any[]>([])
const search = ref('')
const loading = ref(false)
const centerDialogVisible = ref(false)
const checkTableList = ref([] as any[])

const workspaceWithKeywords = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) {
    return workspace.value
  }
  return workspace.value.filter((ele: any) =>
    [ele.name, ele.account].some((field) =>
      String(field ?? '')
        .toLowerCase()
        .includes(keyword)
    )
  )
})

const visibleIds = computed(() => new Set(workspaceWithKeywords.value.map((ele: any) => ele.id)))
const isVisibleUser = (ele: any) => visibleIds.value.has(ele.id)

const syncCheckedState = () => {
  const total = workspaceWithKeywords.value.length
  const checked = checkedWorkspace.value.length
  checkAll.value = total > 0 && checked === total
  isIndeterminate.value = checked > 0 && checked < total
}

watch(search, () => {
  checkedWorkspace.value = checkTableList.value.filter(isVisibleUser)
  syncCheckedState()
})
const handleCheckAllChange = (val: CheckboxValueType) => {
  const rest = checkTableList.value.filter((ele: any) => !isVisibleUser(ele))
  checkTableList.value = val ? [...rest, ...workspaceWithKeywords.value] : rest
  checkedWorkspace.value = val ? [...workspaceWithKeywords.value] : []
  syncCheckedState()
}
const handleCheckedWorkspaceChange = (value: CheckboxValueType[]) => {
  const rest = checkTableList.value.filter((ele: any) => !isVisibleUser(ele))
  const picked = (value as any[]).filter(isVisibleUser)
  checkTableList.value = [...rest, ...picked]
  checkedWorkspace.value = [...picked]
  syncCheckedState()
}

const USER_PAGE_SIZE = 500

const loadWorkspaceUsers = async () => {
  const users: any[] = []
  let page = 1
  let totalPages = 1
  do {
    const res: any = await workspaceUserList({}, page, USER_PAGE_SIZE)
    // json-bigint objects have no Object.prototype; keep checkbox values plain.
    users.push(
      ...res.items.map((user: any) => ({
        id: user.id,
        name: user.name,
        account: user.account,
      }))
    )
    totalPages = res.total_pages
    if (!res.items.length) break
    page += 1
  } while (page <= totalPages)
  return users
}

const open = async (user: any) => {
  loading.value = true
  search.value = ''
  checkedWorkspace.value = []
  checkAll.value = false
  checkTableList.value = []
  isIndeterminate.value = false
  workspace.value = await loadWorkspaceUsers()
  if (user?.length) {
    checkedWorkspace.value = workspace.value.filter((ele: any) => user.includes(ele.id))
    checkTableList.value = [...checkedWorkspace.value]
    handleCheckedWorkspaceChange(checkedWorkspace.value)
  }
  loading.value = false
  centerDialogVisible.value = true
}

const clearWorkspace = (val: any) => {
  checkedWorkspace.value = checkedWorkspace.value.filter((ele: any) => ele.id !== val.id)
  checkTableList.value = checkTableList.value.filter((ele: any) => ele.id !== val.id)
  handleCheckedWorkspaceChange(checkedWorkspace.value)
}

const clearWorkspaceAll = () => {
  checkTableList.value = []
  checkedWorkspace.value = []
  syncCheckedState()
}

defineExpose({
  open,
  checkTableList,
})
</script>
<style lang="less">
.select-user_permission {
  .lighter-bold {
    margin-bottom: 16px;
    font-weight: 500;
    font-size: 16px;
    line-height: 24px;
  }

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
    margin: 0 16px;
  }

  .checkbox-group-block {
    .ed-checkbox,
    .ed-checkbox__label,
    .flex {
      width: 96%;
      height: 44px;
    }

    .flex {
      align-items: center;
      .account {
        color: #8f959e;
      }
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

  .empty-members {
    height: 330px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #8f959e;
    font-size: 14px;
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

  .flex {
    display: flex;
  }

  .border-r {
    border-right: 1px solid #dee0e3;
    width: 50%;
    overflow: hidden;
  }
}
</style>
