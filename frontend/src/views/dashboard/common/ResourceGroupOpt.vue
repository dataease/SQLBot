<script lang="ts" setup>
import folder from '@/assets/svg/folder.svg'
import { type SQTreeNode } from '@/views/dashboard/utils/treeNode'
import { reactive, ref } from 'vue'
import { saveDashboardResource } from '@/views/dashboard/utils/canvasUtils.ts'
import { dashboardApi } from '@/api/dashboard.ts'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const emits = defineEmits(['finish'])
const resource = ref(null)
const state = reactive({
  id: null,
  opt: null,
  placeholder: '',
  nodeType: 'folder',
  parentSelect: false,
  resourceFormNameLabel: t('dashboard.dashboard_name'),
  dialogTitle: '',
  tData: [],
  tDataSource: [],
  nameList: [],
  targetInfo: null,
  attachParams: null,
})

const getTitle = (opt: string) => {
  switch (opt) {
    case 'newLeaf':
      return t('dashboard.new_dashboard')
    case 'newFolder':
      return t('dashboard.new_folder')
    case 'rename':
      return t('dashboard.rename_dashboard')
    default:
      return
  }
}

const getResourceNewName = (opt: string) => {
  switch (opt) {
    case 'newLeaf':
      return 'New Dashboard'
    case 'newFolder':
      return 'New Folder'
    default:
      return
  }
}

const getTree = async () => {
  const params = { node_type: 'folder' }
  dashboardApi.list_resource(params).then((res) => {
    state.tData = res || []
    state.tDataSource = [...state.tData]
  })
}

const optInit = (params: any) => {
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  state.dialogTitle = getTitle(params.opt)
  state.opt = params.opt
  state.id = params.id
  state.parentSelect = params.parentSelect
  state.targetInfo = params.data
  state.nodeType = params.nodeType || 'folder'
  resourceDialogShow.value = true
  resourceForm.name = params.name || getResourceNewName(params.opt)
  resourceForm.pid = params.pid || 'root'
  if (params.parentSelect) {
    getTree()
  }
}

const resourceDialogShow = ref(false)
const loading = ref(false)
const resourceForm = reactive({
  id: null,
  pid: '',
  pName: '',
  name: 'New Dashboard',
})

const resourceFormRules = ref({
  name: [
    {
      required: true,
      min: 1,
      max: 64,
      message: t('dashboard.length_limit64'),
      trigger: 'change',
    },
  ],
  pid: [
    {
      required: true,
      message: 'Please select',
      trigger: 'blur',
    },
  ],
})

const resetForm = () => {
  state.dialogTitle = ''
  resourceForm.name = ''
  resourceForm.pid = ''
  resourceDialogShow.value = false
}

const propsTree = {
  value: 'id',
  label: 'name',
  children: 'children',
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  isLeaf: (node) => !node.children?.length,
}

const showPid = false

const saveResource = () => {
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  resource.value?.validate((result) => {
    if (result) {
      const params = {
        id: state.id,
        node_type: state.nodeType,
        name: resourceForm.name,
        opt: state.opt,
        pid: resourceForm.pid,
        type: 'dashboard',
        level: state.nodeType === 'folder' ? 0 : 1,
      }
      saveDashboardResource(params, function (rsp: any) {
        const messageTips = t('common.save_success')
        ElMessage({
          type: 'success',
          message: messageTips,
        })
        emits('finish', { opt: state.opt, resourceId: rsp.id })
        resetForm()
      })
    }
  })
}

const nodeClick = (data: SQTreeNode) => {
  resourceForm.pid = data.id as string
  resourceForm.pName = data.name as string
}

const filterMethod = (value: any) => {
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  state.tData = state.tDataSource.filter((item) => item.name.includes(value))
}

defineExpose({
  optInit,
})
</script>

<template>
  <el-dialog
    v-model="resourceDialogShow"
    class="create-dialog"
    :title="state.dialogTitle"
    width="420px"
    :before-close="resetForm"
    append-to-body
    @submit.prevent
  >
    <el-form
      ref="resource"
      v-loading="loading"
      label-position="top"
      require-asterisk-position="right"
      :model="resourceForm"
      :rules="resourceFormRules"
      class="last"
      @submit.prevent
    >
      <el-form-item :label="state.resourceFormNameLabel" prop="name">
        <el-input
          v-model="resourceForm.name"
          :placeholder="state.placeholder"
          clearable
          @keydown.stop
          @keyup.stop
        />
      </el-form-item>
      <el-form-item v-if="showPid" :label="'Folder'" prop="pid">
        <el-tree-select
          v-model="resourceForm.pid"
          style="width: 100%"
          :data="state.tData"
          :props="propsTree"
          :filter-method="filterMethod"
          :render-after-expand="false"
          filterable
          @keydown.stop
          @keyup.stop
          @node-click="nodeClick"
        >
          <template #default="{ data: { name } }">
            <span class="custom-tree-node">
              <el-icon>
                <Icon name="dv-folder"><folder class="svg-icon custom-tree-folder" /></Icon>
              </el-icon>
              <span :title="name">{{ name }}</span>
            </span>
          </template>
        </el-tree-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button secondary @click="resetForm()">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" @click="saveResource()">{{ t('common.confirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<style lang="less" scoped>
.tree-content {
  width: 552px;
  height: 380px;
  border: 1px solid #dee0e3;
  border-radius: 6px;
  padding: 8px;
  overflow-y: auto;

  .empty-search {
    width: 100%;
    margin-top: 57px;
    display: flex;
    flex-direction: column;
    align-items: center;

    img {
      width: 100px;
      height: 100px;
      margin-bottom: 8px;
    }

    span {
      font-family: var(--de-custom_font, 'PingFang');
      font-size: 14px;
      font-weight: 400;
      line-height: 22px;
      color: #646a73;
    }
  }
}

.custom-tree-node {
  display: flex;
  align-items: center;

  span {
    margin-left: 8.75px;
    width: 120px;
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
  }
}

.custom-tree-folder {
  color: rgb(255, 198, 10);
}
</style>
