<script setup lang="ts">
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import { treeDraggableChart } from '@/views/dashboard/utils/treeDraggableChart'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import icon_folder from '@/assets/svg/icon_folder.svg'
import ope_add from '@/assets/svg/operate/ope-add.svg'
import icon_dashboard from '@/assets/permission/icon_dashboard.svg'
import icon_edit_outlined from '@/assets/svg/icon_edit_outlined.svg'
import icon_rename from '@/assets/svg/icon_rename.svg'
import icon_delete from '@/assets/svg/icon_delete.svg'
import icon_more_outlined from '@/assets/svg/icon_more_outlined.svg'
import dv_sort_asc from '@/assets/svg/dv-sort-asc.svg'
import dv_sort_desc from '@/assets/svg/dv-sort-desc.svg'
import { onMounted, reactive, ref, watch, nextTick, computed } from 'vue'
import { ElIcon, ElScrollbar } from 'element-plus-secondary'
import { Icon } from '@/components/icon-custom'
import { type SQTreeNode } from '@/views/dashboard/utils/treeNode'
import _ from 'lodash'
import router from '@/router'
import { dashboardStoreWithOut } from '@/stores/dashboard/dashboard.ts'
import ResourceGroupOpt from '@/views/dashboard/common/ResourceGroupOpt.vue'
import { dashboardApi } from '@/api/dashboard.ts'
import HandleMore from '@/views/dashboard/common/HandleMore.vue'
import { useI18n } from 'vue-i18n'
import treeSort from '@/views/dashboard/utils/treeSortUtils.ts'
import { useCache } from '@/utils/useCache.ts'
const { wsCache } = useCache()

const { t } = useI18n()
const dashboardStore = dashboardStoreWithOut()
const resourceGroupOptRef = ref(null)

defineProps({
  curCanvasType: {
    type: String,
    required: true,
  },
  showPosition: {
    required: false,
    type: String,
    default: 'preview',
  },
  resourceTable: {
    required: false,
    type: String,
    default: 'core',
  },
})
const defaultProps = {
  children: 'children',
  label: 'name',
}
const mounted = ref(false)
const selectedNodeKey: any = ref(null)
const filterText = ref(null)
const expandedArray = ref([])
const resourceListTree = ref()
const returnMounted = ref(false)
const state = reactive({
  curSortType: 'name_asc',
  curSortTypePrefix: 'name',
  curSortTypeSuffix: '_asc',
  resourceTree: [] as SQTreeNode[],
  originResourceTree: [] as SQTreeNode[],
  sortType: [],
  templateCreatePid: 0,
  menuList: [
    {
      label: t('dashboard.edit'),
      command: 'edit',
      svgName: icon_edit_outlined,
    },
    {
      label: t('dashboard.rename'),
      command: 'rename',
      svgName: icon_rename,
    },
    {
      label: t('dashboard.delete'),
      command: 'delete',
      svgName: icon_delete,
      divided: true,
    },
  ],
})

const { handleDrop, handleDragStart } = treeDraggableChart(state, 'resourceTree', 'dashboard')

const routerDashboardId = router.currentRoute.value.query.dashboardId
if (routerDashboardId) {
  selectedNodeKey.value = routerDashboardId
  returnMounted.value = true
}
const nodeExpand = (data: any) => {
  if (data.id) {
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    expandedArray.value.push(data.id)
  }
}

const nodeCollapse = (data: any) => {
  if (data.id) {
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    expandedArray.value.splice(expandedArray.value.indexOf(data.id), 1)
  }
}

const filterNode = (value: string, data: SQTreeNode) => {
  if (!value) return true
  return data.name?.toLocaleLowerCase().includes(value.toLocaleLowerCase())
}

const nodeClick = (data: SQTreeNode, node: any) => {
  dashboardStore.setCurComponent({ component: null, index: null })
  if (node.disabled) {
    nextTick(() => {
      const currentNode = resourceListTree.value.$el.querySelector('.is-current')
      if (currentNode) {
        currentNode.classList.remove('is-current')
      }
      return
    })
  } else {
    selectedNodeKey.value = data.id
    if (data.node_type === 'leaf') {
      emit('nodeClick', data)
    } else {
      resourceListTree.value.setCurrentKey(null)
    }
  }
}

const getTree = async () => {
  state.originResourceTree = []
  const params = {}
  dashboardApi.list_resource(params).then((res: SQTreeNode[]) => {
    state.originResourceTree = res || []
    state.resourceTree = _.cloneDeep(state.originResourceTree)
    handleSortTypeChange('name_asc')
    afterTreeInit()
  })
}

const hasData = computed<boolean>(() => state.resourceTree.length > 0)

const afterTreeInit = () => {
  mounted.value = true
  if (selectedNodeKey.value && returnMounted.value) {
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    expandedArray.value = getDefaultExpandedKeys()
    returnMounted.value = false
  }
  nextTick(() => {
    resourceListTree.value.setCurrentKey(selectedNodeKey.value)
    resourceListTree.value.filter(filterText.value)
    nextTick(() => {
      // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
      document.querySelector('.is-current')?.firstChild?.click()
    })
  })
}

const copyLoading = ref(false)
const emit = defineEmits(['nodeClick', 'deleteCurResource'])

function createNewObject() {
  addOperation({ opt: 'newLeaf' })
}

// @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
const resourceEdit = (resourceId) => {
  window.open(`#/canvas?resourceId=${resourceId}`, '_self')
}

// @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
const getParentKeys = (tree: any, targetKey: any, parentKeys = []) => {
  for (const node of tree) {
    if (node.id === targetKey) {
      return parentKeys
    }
    if (node.children) {
      const newParentKeys = [...parentKeys, node.id]
      // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
      const result = getParentKeys(node.children, targetKey, newParentKeys)
      if (result) {
        return result
      }
    }
  }
  return null
}

const getDefaultExpandedKeys = () => {
  const parentKeys = getParentKeys(state.resourceTree, selectedNodeKey.value)
  if (parentKeys) {
    return [selectedNodeKey.value, ...parentKeys]
  } else {
    return []
  }
}

watch(filterText, (val) => {
  resourceListTree.value.filter(val)
})

const loadInit = () => {}
onMounted(() => {
  loadInit()
  getTree()
})

const addOperation = (params: any) => {
  if (params.opt === 'newLeaf') {
    const newCanvasUrl = '#/canvas?opt=create' + (params?.id ? `&pid=${params?.id}` : '')
    window.open(newCanvasUrl, '_self')
    dashboardStore.canvasDataInit()
  } else {
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    resourceGroupOptRef.value?.optInit(params)
  }
}

const operation = (opt: string, data: SQTreeNode) => {
  if (opt === 'delete') {
    const msg = data.node_type === 'leaf' ? '' : t('dashboard.delete_tips')
    ElMessageBox.confirm(t('dashboard.delete_dashboard_warn', [data.name]), {
      confirmButtonType: 'danger',
      type: 'warning',
      tip: msg,
      autofocus: false,
      showClose: false,
    }).then(() => {
      dashboardApi.delete_resource({ id: data.id, name: data.name }).then(() => {
        ElMessage.success(t('dashboard.delete_success'))
        getTree()
        dashboardStore.canvasDataInit()
        emit('deleteCurResource')
      })
    })
  } else if (opt === 'rename') {
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    resourceGroupOptRef.value?.optInit({ opt: 'rename', id: data.id, name: data.name })
  } else if (opt === 'edit') {
    resourceEdit(data.id)
  }
}

const baseInfoChangeFinish = () => {
  getTree()
}

const handleSortTypeChange = (menuSortType: string) => {
  state.curSortTypePrefix = ['name', 'time'].includes(menuSortType)
    ? menuSortType
    : state.curSortTypePrefix
  state.curSortTypeSuffix = ['_asc', '_desc'].includes(menuSortType)
    ? menuSortType
    : state.curSortTypeSuffix
  const curMenuSortType = state.curSortTypePrefix + state.curSortTypeSuffix
  state.resourceTree = treeSort(state.originResourceTree, curMenuSortType)
  state.curSortType = curMenuSortType
  wsCache.set('TreeSort-dashboard', state.curSortType)
}

const sortColumnList = [
  {
    name: t('dashboard.time'),
    value: 'time',
  },
  {
    name: t('dashboard.name'),
    value: 'name',
    divided: true,
  },
]

const sortTypeList = [
  {
    name: t('dashboard.sort_asc'),
    value: '_asc',
  },
  {
    name: t('dashboard.sort_desc'),
    value: '_desc',
  },
]

const sortList = [
  {
    name: t('dashboard.time_asc'),
    value: 'time_asc',
  },
  {
    name: t('dashboard.time_desc'),
    value: 'time_desc',
    divided: true,
  },
  {
    name: t('dashboard.name_asc'),
    value: 'name_asc',
  },
  {
    name: t('dashboard.name_desc'),
    value: 'name_desc',
  },
]

const sortTypeTip = computed(() => {
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  return sortList.find((ele) => ele.value === state.curSortType).name
})

defineExpose({
  hasData,
  createNewObject,
  mounted,
})
</script>

<template>
  <div class="resource-tree">
    <div class="tree-header">
      <div class="icon-methods">
        <span class="title">{{ t('dashboard.dashboard') }} </span>
        <el-tooltip
          :offset="12"
          :content="t('dashboard.new_dashboard')"
          placement="top"
          effect="dark"
        >
          <el-icon
            class="custom-icon btn hover-icon_with_bg primary-icon"
            @click="addOperation({ opt: 'newLeaf', type: 'dashboard' })"
          >
            <Icon name="dv-new-folder">
              <ope_add class="svg-icon" />
            </Icon>
          </el-icon>
        </el-tooltip>
      </div>
      <el-input
        v-model="filterText"
        :placeholder="t('dashboard.search')"
        clearable
        class="search-bar"
      >
        <template #prefix>
          <el-icon>
            <Icon name="icon_search-outline_outlined">
              <icon_searchOutline_outlined class="svg-icon" />
            </Icon>
          </el-icon>
        </template>
      </el-input>
      <el-dropdown
        popper-class="tree-sort-menu-custom"
        trigger="click"
        placement="bottom-end"
        @command="handleSortTypeChange"
      >
        <el-icon class="filter-icon-span" :class="state.curSortType !== 'name_asc' && 'active'">
          <el-tooltip :offset="16" effect="dark" :content="sortTypeTip" placement="top">
            <Icon v-if="state.curSortType.includes('asc')" name="dv-sort-asc" class="opt-icon"
              ><dv_sort_asc class="svg-icon opt-icon"
            /></Icon>
          </el-tooltip>
          <el-tooltip :offset="16" effect="dark" :content="sortTypeTip" placement="top">
            <Icon v-if="state.curSortType.includes('desc')" name="dv-sort-desc" class="opt-icon"
              ><dv_sort_desc class="svg-icon opt-icon"
            /></Icon>
          </el-tooltip>
        </el-icon>
        <template #dropdown>
          <el-dropdown-menu style="width: 120px">
            <span class="sort_menu">{{ t('dashboard.sort_column') }}</span>
            <template v-for="ele in sortColumnList" :key="ele.value">
              <el-dropdown-item
                class="ed-select-dropdown__item"
                :class="state.curSortType.includes(ele.value) && 'selected'"
                :command="ele.value"
              >
                {{ ele.name }}
              </el-dropdown-item>
              <li v-if="ele.divided" class="ed-dropdown-menu__item--divided"></li>
            </template>
            <span class="sort_menu">{{ t('dashboard.sort_type') }}</span>
            <template v-for="ele in sortTypeList" :key="ele.value">
              <el-dropdown-item
                class="ed-select-dropdown__item"
                :class="state.curSortType.includes(ele.value) && 'selected'"
                :command="ele.value"
              >
                {{ ele.name }}
              </el-dropdown-item>
            </template>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
    <el-scrollbar v-loading="copyLoading" class="custom-tree">
      <el-tree
        ref="resourceListTree"
        style="overflow-x: hidden"
        menu
        :empty-text="t('dashboard.no_dashboard')"
        :default-expanded-keys="expandedArray"
        :data="state.resourceTree"
        :props="defaultProps"
        node-key="id"
        highlight-current
        :expand-on-click-node="true"
        :filter-node-method="filterNode"
        draggable
        @node-expand="nodeExpand"
        @node-collapse="nodeCollapse"
        @node-click="nodeClick"
        @node-drag-start="handleDragStart"
        @node-drop="handleDrop"
      >
        <template #default="{ node, data }">
          <span class="custom-tree-node">
            <el-icon v-if="data.node_type !== 'leaf'" style="font-size: 18px">
              <Icon name="icon_folder"><icon_folder class="svg-icon" /></Icon>
            </el-icon>
            <el-icon v-else class="icon-primary" style="font-size: 18px">
              <Icon name="icon_dashboard"><icon_dashboard class="svg-icon" /></Icon>
            </el-icon>
            <span :title="node.label" class="label-tooltip">
              {{ node.label }}
            </span>
            <div class="icon-more">
              <el-icon
                v-if="data.node_type !== 'leaf'"
                class="hover-icon"
                @click.stop
                @click="addOperation({ opt: 'newLeaf', type: 'dashboard', id: data.id })"
              >
                <Icon><icon_add_outlined class="svg-icon" /></Icon>
              </el-icon>
              <HandleMore
                :menu-list="state.menuList"
                :icon-name="icon_more_outlined"
                placement="bottom-end"
                @handle-command="(opt: string) => operation(opt, data)"
              ></HandleMore>
            </div>
          </span>
        </template>
      </el-tree>
    </el-scrollbar>
    <ResourceGroupOpt ref="resourceGroupOptRef" @finish="baseInfoChangeFinish"></ResourceGroupOpt>
  </div>
</template>
<style lang="less" scoped>
.filter-icon-span {
  border: 1px solid #d9dcdf;
  width: 32px;
  height: 32px;
  border-radius: 4px;
  color: #1f2329;
  padding: 8px;
  margin-left: 8px;
  font-size: 16px;
  cursor: pointer;

  .opt-icon:focus {
    outline: none !important;
  }

  &:hover,
  &:focus {
    background: #f5f6f7;
  }

  &:active {
    background: #eff0f1;
  }

  &.active {
    border: 1px solid var(--ed-color-primary);
    color: var(--ed-color-primary);

    &:hover,
    &:focus {
      background: var(--ed-color-primary-80, #d2f1e9);
    }

    &:active {
      background: var(--ed-color-primary-60, #a4e3d3);
    }
  }
}

.resource-tree {
  padding: 16px 0 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;

  .tree-header {
    padding: 0 16px;
  }

  .icon-methods {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 20px;
    font-weight: 500;
    color: var(--TextPrimary, #1f2329);
    padding-bottom: 16px;

    .title {
      margin-right: auto;
      font-size: 16px;
      font-style: normal;
      font-weight: 500;
      line-height: 24px;
    }

    .custom-icon {
      font-size: 20px;

      &.btn {
        color: var(--ed-color-primary);
      }

      &:hover {
        cursor: pointer;
      }
    }
  }

  .search-bar {
    padding-bottom: 10px;
    width: calc(100% - 40px);
  }
}

.title-area {
  margin-left: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.title-area-outer {
  display: flex;
  flex: 1 1 0%;
  width: 0px;
}

.custom-tree-node-list {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  padding: 0 8px;
}

.father .child {
  visibility: hidden;
}

.father:hover .child {
  visibility: visible;
}

:deep(.ed-input__wrapper) {
  width: 80px;
}

.custom-tree {
  height: calc(100vh - 148px);
  padding: 0 8px;
  :deep(.ed-tree-node) {
    margin-bottom: 2px;
  }
}

.custom-tree-node {
  width: calc(100% - 30px);
  display: flex;
  align-items: center;
  box-sizing: content-box;
  padding-right: 12px;

  .label-tooltip {
    width: 100%;
    margin-left: 8.75px;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .icon-more {
    margin-left: auto;
    display: none;
    color: #bbbfc4;
  }

  &:hover {
    .label-tooltip {
      width: calc(100% - 78px);
    }

    .icon-more {
      display: inline-flex;
    }
  }

  .icon-screen-new {
    border-radius: 4px;
    color: #fff;
    padding: 3px;
  }
}
</style>

<style lang="less">
.tree-sort-menu-custom {
  padding: 4px !important;
  li {
    border-radius: 4px;
    padding: 0 8px !important;
  }
  .ed-dropdown-menu__item:not(.is-disabled):not(.selected):hover {
    color: #1f2329;
  }
}
.menu-outer-dv_popper {
  min-width: 140px;
  margin-top: -2px !important;

  .ed-icon {
    border-radius: 4px;
  }
}

.sort-type-normal {
  i {
    display: none;
  }
}

.sort-type-checked {
  color: var(--ed-color-primary);

  i {
    display: block;
  }
}

.node-disabled-custom {
  color: rgba(187, 191, 196, 1);
  cursor: not-allowed;
}

.color-dataV-disabled {
  background: #bbbfc4 !important;
}

.sort_menu {
  color: rgba(143, 149, 158, 1);
  font-size: 14px;
  margin-left: 8px;
}
</style>
