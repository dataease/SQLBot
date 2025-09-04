<script setup lang="ts">
import { onMounted, ref, computed, reactive } from 'vue'
import Toolbar from '@/views/dashboard/editor/Toolbar.vue'
import DashboardEditor from '@/views/dashboard/editor/DashboardEditor.vue'
import { findNewComponentFromList } from '@/views/dashboard/components/component-list.ts'
import { guid } from '@/utils/canvas.ts'
import cloneDeep from 'lodash/cloneDeep'
import { storeToRefs } from 'pinia'
import { dashboardStoreWithOut } from '@/stores/dashboard/dashboard.ts'
import router from '@/router'
import { initCanvasData } from '@/views/dashboard/utils/canvasUtils.ts'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const dashboardStore = dashboardStoreWithOut()
const { componentData, canvasViewInfo, fullscreenFlag, baseMatrixCount } =
  storeToRefs(dashboardStore)

const dataInitState = ref(true)
const state = reactive({
  routerPid: null,
  resourceId: null,
  opt: null,
})

const dashboardEditorInnerRef = ref(null)
const addComponents = (componentType: string, views?: any) => {
  const component = cloneDeep(findNewComponentFromList(componentType))
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  component.x = findPositionX(component.sizeX)
  if (views) {
    views.forEach((view: any, index: number) => {
      const target = cloneDeep(view)
      delete target.chart.sourceType
      if (index > 0) {
        // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
        component.x = ((component.x + component?.sizeX - 1) % baseMatrixCount.value.x) + 1
      }
      addComponent(component, target)
    })
  } else {
    addComponent(component)
  }
}
const addComponent = (componentSource: any, viewInfo?: any) => {
  const component = cloneDeep(componentSource)
  if (component && dashboardEditorInnerRef.value) {
    component.id = guid()
    // add view
    if (component?.component === 'SQView' && !!viewInfo) {
      viewInfo['sourceId'] = viewInfo['id']
      viewInfo['id'] = component.id
      dashboardStore.addCanvasViewInfo(viewInfo)
    } else if (component.component === 'SQTab') {
      const subTabName = guid('tab')
      component.propValue[0].name = subTabName
      component.propValue[0].title = t('dashboard.new_tab')
      component.activeTabName = subTabName
    }
    component.y = maxYComponentCount() + 2
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    dashboardEditorInnerRef.value.addItemToBox(component)
  }
}

const maxYComponentCount = () => {
  if (componentData.value.length === 0) {
    return 1
  } else {
    return componentData.value
      .filter((item) => item['y'])
      .map((item) => item['y'] + item['sizeY']) // Calculate the y+sizeY of each element
      .reduce((max, current) => Math.max(max, current), 0)
  }
}

onMounted(() => {
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  state.opt = router.currentRoute.value.query.opt
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  state.resourceId = router.currentRoute.value.query.resourceId
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  state.routerPid = router.currentRoute.value.query.pid
  if (state.opt === 'create') {
    dashboardStore.updateDashboardInfo({
      dataState: 'prepare',
      name: t('dashboard.new_dashboard'),
      pid: state.routerPid,
    })
  } else if (state.resourceId) {
    dataInitState.value = false
    initCanvasData({ id: state.resourceId }, function () {
      dataInitState.value = true
    })
  }
})

const baseParams = computed(() => {
  return {
    opt: state.opt,
    resourceId: state.resourceId,
    pid: state.routerPid,
  }
})
const findPositionX = (width: number) => {
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  return dashboardEditorInnerRef.value.findPositionX(width)
}
</script>

<template>
  <div class="editor-content" :class="{ 'editor-content-fullscreen': fullscreenFlag }">
    <div class="editor-main">
      <Toolbar
        :base-params="baseParams"
        :find-position-x="findPositionX"
        @add-components="addComponents"
      ></Toolbar>
      <DashboardEditor
        v-if="dataInitState"
        ref="dashboardEditorInnerRef"
        :canvas-component-data="componentData"
        :canvas-view-info="canvasViewInfo"
      >
      </DashboardEditor>
    </div>
  </div>
</template>

<style scoped lang="less">
.editor-content {
  width: 100vw;
  height: 100vh;
  background: #fff;
  overflow: hidden;
}

.editor-content-fullscreen {
  padding: 0 !important;
}
.editor-main {
  position: relative;
  background: #f5f6f7;
  overflow: hidden;
  width: 100%;
  height: 100%;
}
</style>
