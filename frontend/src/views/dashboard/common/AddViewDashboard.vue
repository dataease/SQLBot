<script lang="ts" setup>
import { reactive, ref, h } from 'vue'
import { ElButton, ElMessage } from 'element-plus-secondary'
import {
  findNextComponentIndex,
  saveDashboardResourceTarget,
} from '@/views/dashboard/utils/canvasUtils.ts'
import { useI18n } from 'vue-i18n'
import { dashboardApi } from '@/api/dashboard.ts'
import type { SQTreeNode } from '@/views/dashboard/utils/treeNode.ts'
import cloneDeep from 'lodash/cloneDeep'
import { findNewComponentFromList } from '@/views/dashboard/components/component-list.ts'
import { guid } from '@/utils/canvas.ts'

const { t } = useI18n()
const resource = ref(null)

const optInit = (viewInfo: any) => {
  initDashboardList()
  resourceDialogShow.value = true
  state.viewInfo = viewInfo
}
const state = reactive({
  dashboardList: [] as SQTreeNode[],
  viewInfo: null,
})

const resourceDialogShow = ref(false)
const loading = ref(false)
const resourceForm = reactive({
  addType: 'history',
  dashboardId: '',
  dashboardName: '',
})

const resourceFormRulesNew = ref({
  dashboardName: [
    {
      required: true,
      min: 1,
      max: 64,
      message: t('dashboard.length_limit64'),
      trigger: 'change',
    },
  ],
})

const resourceFormRulesHistory = ref({
  dashboardId: [
    {
      required: true,
      min: 1,
      max: 64,
      message: '请选择仪表板',
      trigger: 'change',
    },
  ],
})

const resetForm = () => {
  resourceForm.dashboardId = ''
  resourceForm.dashboardName = ''
  resourceDialogShow.value = false
}

const saveResourcePrepare = () => {
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  resource.value?.validate((result) => {
    if (result) {
      const component = cloneDeep(findNewComponentFromList('SQView'))
      const newComponentId = guid()
      // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
      state.viewInfo.chart['id'] = newComponentId
      // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
      state.viewInfo['id'] = newComponentId
      if (resourceForm.addType === 'history' && component) {
        findNextComponentIndex({ id: resourceForm.dashboardId }, (result: any) => {
          const {
            bottomPosition,
            dashboardInfo,
            canvasDataResult,
            canvasStyleResult,
            canvasViewInfoPreview,
          } = result
          const params = {
            opt: 'updateLeaf',
            pid: 'root',
            id: resourceForm.dashboardId,
            name: dashboardInfo.name,
          }
          component['id'] = newComponentId
          component['y'] = bottomPosition
          canvasDataResult.push(component)
          canvasViewInfoPreview[newComponentId] = state.viewInfo
          const commonParams = {
            componentData: canvasDataResult,
            canvasStyleData: canvasStyleResult,
            canvasViewInfo: canvasViewInfoPreview,
          }
          saveResource(params, commonParams)
        })
      } else if (resourceForm.addType === 'new' && component) {
        const params = {
          opt: 'newLeaf',
          pid: 'root',
          name: resourceForm.dashboardName,
          level: 1,
          node_type: 'leaf',
          type: 'dashboard',
        }
        component['id'] = newComponentId
        const canvasViewInfo = {}
        // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
        canvasViewInfo[newComponentId] = state.viewInfo
        const commonParams = {
          componentData: [component],
          canvasStyleData: {},
          canvasViewInfo: canvasViewInfo,
        }
        saveResource(params, commonParams)
      }
    }
  })
}

const saveResource = (params: any, commonParams: any) => {
  saveDashboardResourceTarget(params, commonParams, (res: any) => {
    const messageTips = t('dashboard.add_success')
    openMessageLoading(messageTips, 'success', res?.id, callbackExportSuc)
    resetForm()
  })
}

const callbackExportSuc = (curOptDashboardIdValue: any) => {
  // do open dashboard
  const url = `#/canvas?resourceId=${curOptDashboardIdValue}`
  window.open(url, '_self')
}

// eslint-disable-next-line @typescript-eslint/no-unsafe-function-type
const openMessageLoading = (text: string, type = 'success', dvId: any, cb: Function) => {
  // success error loading
  const customClass = `sq-message-${type || 'success'} sq-message-export`
  ElMessage({
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    message: h('p', null, [
      h(
        'span',
        {
          title: t(text),
          class: 'ellipsis m50-export',
        },
        t(text)
      ),
      h(
        ElButton,
        {
          text: true,
          size: 'small',
          class: 'btn-text',
          onClick: () => {
            cb(dvId)
          },
        },
        t('dashboard.open_dashboard')
      ),
    ]),
    type,
    showClose: true,
    duration: 2000,
    customClass,
  })
}

const initDashboardList = () => {
  state.dashboardList = []
  const params = {}
  dashboardApi.list_resource(params).then((res: SQTreeNode[]) => {
    state.dashboardList = res || []
  })
}

defineExpose({
  optInit,
})
</script>

<template>
  <el-dialog
    v-model="resourceDialogShow"
    class="create-dialog"
    :title="t('chat.add_to_dashboard')"
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
      :rules="resourceForm.addType === 'new' ? resourceFormRulesNew : resourceFormRulesHistory"
      @submit.prevent
    >
      <el-form-item :label="t('dashboard.dashboard_name')" required prop="addType">
        <el-radio-group v-model="resourceForm.addType">
          <el-radio value="history">{{ t('dashboard.existing_dashboard') }}</el-radio>
          <el-radio value="new">{{ t('dashboard.new_dashboard') }}</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item
        v-if="resourceForm.addType === 'new'"
        :label="t('dashboard.dashboard')"
        required
        prop="dashboardName"
      >
        <el-input
          v-model="resourceForm.dashboardName"
          clearable
          :placeholder="t('dashboard.add_dashboard_name_tips')"
          @keydown.stop
          @keyup.stop
        />
      </el-form-item>
      <el-form-item
        v-if="resourceForm.addType === 'history'"
        :label="t('dashboard.dashboard')"
        required
        prop="dashboardId"
      >
        <el-select
          v-model="resourceForm.dashboardId"
          filterable
          :placeholder="t('dashboard.select_dashboard')"
        >
          <el-option
            v-for="item in state.dashboardList"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button secondary @click="resetForm()">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" @click="saveResourcePrepare()">{{ t('common.confirm') }}</el-button>
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
