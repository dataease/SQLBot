<script setup lang="ts">
import { dashboardStoreWithOut } from '@/stores/dashboard/dashboard.ts'
import { storeToRefs } from 'pinia'
import ComponentButtonLabel from '@/views/dashboard/components/button-label/ComponentButtonLabel.vue'
import dvTab from '@/assets/svg/dv-tab.svg'
import dvText from '@/assets/svg/dv-text.svg'
import dvView from '@/assets/svg/dv-view.svg'
import ResourceGroupOpt from '@/views/dashboard/common/ResourceGroupOpt.vue'
import { ref, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { snapshotStoreWithOut } from '@/stores/dashboard/snapshot.ts'
import icon_undo_outlined from '@/assets/svg/icon_undo_outlined.svg'
import icon_redo_outlined from '@/assets/svg/icon_redo_outlined.svg'
import icon_arrow_left_outlined from '@/assets/svg/icon_arrow-left_outlined.svg'
import { saveDashboardResource } from '@/views/dashboard/utils/canvasUtils.ts'
import ChatChartSelection from '@/views/dashboard/editor/ChatChartSelection.vue'
import icon_pc_outlined from '@/assets/svg/icon_pc_outlined.svg'
const fullScreeRef = ref(null)
const { t } = useI18n()
const dashboardStore = dashboardStoreWithOut()
const { dashboardInfo, fullscreenFlag } = storeToRefs(dashboardStore)

const snapshotStore = snapshotStoreWithOut()
const { snapshotIndex } = storeToRefs(snapshotStore)
const emits = defineEmits(['addComponents'])
const resourceGroupOptRef = ref(null)
const chatChartSelectionRef = ref(null)
const openViewDialog = () => {
  // @ts-expect-error  @typescript-eslint/ban-ts-comment
  chatChartSelectionRef.value?.dialogInit()
}

import cloneDeep from 'lodash/cloneDeep'
import SQFullscreen from '@/views/dashboard/common/SQFullscreen.vue'

let nameEdit = ref(false)
let inputName = ref('')
let nameInput = ref(null)

const onDvNameChange = () => {}

const saveCanvasWithCheck = () => {
  if (dashboardInfo.value.dataState === 'prepare') {
    const createParams = {
      name: dashboardInfo.value.name,
      pid: props.baseParams?.pid,
      opt: 'newLeaf',
      nodeType: 'leaf',
      parentSelect: true,
    }
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    resourceGroupOptRef.value?.optInit(createParams)
  } else if (dashboardInfo.value.id) {
    const updateParams = {
      opt: 'updateLeaf',
      id: dashboardInfo.value.id,
      name: dashboardInfo.value.name,
      pid: 'root',
    }
    saveDashboardResource(updateParams, function () {
      ElMessage({
        type: 'success',
        message: t('common.save_success'),
      })
    })
  }
}

const props = defineProps({
  baseParams: {
    type: Object,
    required: false,
    default: null,
  },
})

const groupOptFinish = (result: any) => {
  let url = window.location.href
  url = url.replace(/(#\/[^?]*)(?:\?[^#]*)?/, `$1?resourceId=${result.resourceId}`)
  window.history.replaceState({ path: url }, '', url)
}

const chartSelectionFinish = () => {}

const editCanvasName = () => {
  nameEdit.value = true
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  inputName.value = dashboardInfo.value.name
  nextTick(() => {
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    nameInput.value?.focus()
  })
}
const handleEnterEditCanvasName = (event: Event) => {
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  event.target?.blur()
}
const closeEditCanvasName = () => {
  nameEdit.value = false
  if (!inputName.value || !inputName.value.trim()) {
    ElMessage.warning(t('dashboard.length_1_64_characters'))
    return
  }
  if (inputName.value.trim() === dashboardInfo.value.name) {
    return
  }
  if (inputName.value.trim().length > 64 || inputName.value.trim().length < 1) {
    ElMessage.warning(t('dashboard.length_1_64_characters'))
    editCanvasName()
    return
  }
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  dashboardInfo.value.name = inputName.value
  inputName.value = ''
}

const undo = () => {
  if (snapshotIndex.value > 0) {
    snapshotStore.undo()
  }
}

const redo = () => {
  if (snapshotIndex.value !== snapshotStore.snapshotData.length - 1) {
    snapshotStore.redo()
  }
}

const backToMain = () => {
  let url = '#/dashboard/index'
  if (dashboardInfo.value.id) {
    url = url + '?resourceId=' + dashboardInfo.value.id
  }
  if (history.state.back) {
    history.back()
  } else {
    window.open(url, '_self')
  }
}

const addChatChart = (views: any) => {
  emits('addComponents', 'SQView', views)
  views.forEach((view: any) => {
    const target = cloneDeep(view)
    delete target.chart.sourceType
    emits('addComponents', 'SQView', target)
  })
  ElMessage({
    type: 'success',
    message: t('dashboard.add_success'),
  })
}

const previewInner = () => {
  if (fullScreeRef.value) {
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    fullScreeRef.value.toggleFullscreen()
  }
}
</script>

<template>
  <div class="toolbar-main" :class="{ 'toolbar-main-hidden': fullscreenFlag }">
    <el-icon class="custom-el-icon back-icon" @click="backToMain()">
      <Icon name="icon_left_outlined">
        <icon_arrow_left_outlined class="toolbar-hover-icon toolbar-icon" />
      </Icon>
    </el-icon>
    <div class="left-area">
      <span id="canvas-name" class="name-area" @dblclick="editCanvasName">
        {{ dashboardInfo.name }}
      </span>
      <div class="opt-area">
        <el-tooltip effect="dark" :content="t('dashboard.undo')" placement="bottom">
          <el-icon
            class="toolbar-hover-icon"
            :class="{ 'toolbar-icon-disabled': snapshotIndex < 1 }"
            :disabled="snapshotIndex < 1"
            @click="undo()"
          >
            <Icon name="icon_undo_outlined">
              <icon_undo_outlined class="svg-icon" />
            </Icon>
          </el-icon>
        </el-tooltip>

        <el-tooltip effect="dark" :content="t('dashboard.reduction')" placement="bottom">
          <el-icon
            class="toolbar-hover-icon opt-icon-redo"
            :class="{
              'toolbar-icon-disabled': snapshotIndex === snapshotStore.snapshotData.length - 1,
            }"
            @click="redo()"
          >
            <Icon name="icon_redo_outlined">
              <icon_redo_outlined class="svg-icon" />
            </Icon>
          </el-icon>
        </el-tooltip>
      </div>
    </div>
    <div class="core-toolbar">
      <component-button-label
        :icon-name="dvView"
        :title="t('dashboard.add_view')"
        themes="light"
        is-label
        show-split-line
        @custom-click="openViewDialog"
      ></component-button-label>
      <component-button-label
        :icon-name="dvText"
        :title="t('dashboard.text')"
        themes="light"
        is-label
        @custom-click="() => emits('addComponents', 'SQText')"
      ></component-button-label>
      <component-button-label
        :icon-name="dvTab"
        title="Tab"
        themes="light"
        is-label
        @custom-click="() => emits('addComponents', 'SQTab')"
      >
      </component-button-label>
    </div>
    <div class="right-toolbar">
      <el-button secondary @click="previewInner">
        <template #icon>
          <icon name="icon_pc_outlined">
            <icon_pc_outlined class="svg-icon" />
          </icon>
        </template>
        {{ t('dashboard.preview') }}
      </el-button>
      <el-button
        style="float: right; margin-right: 12px"
        type="primary"
        @click="saveCanvasWithCheck()"
      >
        {{ t('common.save') }}
      </el-button>
    </div>
    <Teleport v-if="nameEdit" :to="'#canvas-name'">
      <input
        ref="nameInput"
        v-model="inputName"
        @keydown.enter="handleEnterEditCanvasName"
        @change="onDvNameChange"
        @blur="closeEditCanvasName"
      />
    </Teleport>
    <ResourceGroupOpt ref="resourceGroupOptRef" @finish="groupOptFinish"></ResourceGroupOpt>
    <ChatChartSelection
      ref="chatChartSelectionRef"
      @add-chat-chart="addChatChart"
      @finish="chartSelectionFinish"
    ></ChatChartSelection>
    <SQFullscreen ref="fullScreeRef" show-position="edit"></SQFullscreen>
  </div>
</template>

<style scoped lang="less">
.toolbar-main-hidden {
  display: none !important;
}
.toolbar-main {
  width: 100%;
  height: 56px;
  display: flex;
  align-items: center;
  background: #fff;
  padding-left: 24px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.15);

  .left-area {
    margin-left: 12px;
    width: 300px;
    display: flex;
    flex-direction: column;

    .name-area {
      position: relative;
      line-height: 24px;
      height: 24px;
      font-size: 16px;
      width: 300px;
      font-weight: 500;
      overflow: hidden;
      cursor: pointer;
      color: #1f2329;

      input {
        position: absolute;
        left: 0;
        width: 100%;
        background-color: #f5f6f7;
        outline: none;
        font-size: 16px;
        border: 1px solid var(--ed-color-primary);
        border-radius: 4px;
        padding-left: 4px;
        height: 100%;
      }
    }

    .opt-area {
      width: 300px;
      text-align: left;
      color: #a6a6a6;
      display: none;

      .opt-icon-redo {
        margin-left: 12px;
      }
    }
  }

  .core-toolbar {
    display: flex;
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
  }

  .right-toolbar {
    display: flex;
    position: absolute;
    right: 12px;
  }
}

.toolbar-icon {
  width: 20px;
  height: 20px;
  color: #fff;
}

.back-icon {
  width: 20px;
  height: 20px;
}

.toolbar-hover-icon {
  cursor: pointer;
  font-size: 18px !important;
  width: 26px !important;
  height: 26px !important;
  color: rgba(255, 255, 255, 1);
  border-radius: 4px;

  &:hover {
    background: rgba(235, 235, 235, 0.1);
  }

  &:active {
    background: transparent;
  }
}
</style>
