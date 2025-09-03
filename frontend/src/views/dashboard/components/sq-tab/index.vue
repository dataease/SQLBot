<script setup lang="ts">
import {
  computed,
  type PropType,
  reactive,
  ref,
  toRefs,
  nextTick,
  getCurrentInstance,
  onMounted,
} from 'vue'
import CustomTab from '@/views/dashboard/components/sq-tab/CustomTab.vue'
import { guid, type CanvasItem } from '@/utils/canvas.ts'
import DragHandle from '@/views/dashboard/canvas/DragHandle.vue'
import { ArrowDown } from '@element-plus/icons-vue'
import DashboardEditor from '@/views/dashboard/editor/DashboardEditor.vue'

const showTabTitleFlag = ref(true)
// @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
let currentInstance
import _ from 'lodash'
import SQPreview from '@/views/dashboard/preview/SQPreview.vue'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const emits = defineEmits(['parentAddItemBox'])

const tabBaseMatrixCount = {
  x: 36,
  y: 12,
}

const props = defineProps({
  configItem: {
    type: Object as PropType<CanvasItem>,
    required: true,
  },
  canvasViewInfo: {
    type: Object,
    required: true,
  },
  showPosition: {
    required: false,
    type: String,
    default: 'preview',
  },
  canvasId: {
    type: String,
    default: 'canvas-main',
  },
})

const { configItem } = toRefs(props)

const state = reactive({
  curItem: { title: '' },
  textarea: '',
  dialogVisible: false,
  tabShow: true,
  hoverFlag: false,
  headFontColor: '#OOOOOO',
  headFontActiveColor: '#OOOOOO',
  headBorderColor: '#OOOOOO',
  headBorderActiveColor: '#OOOOOO',
})

function addTab() {
  const newTab = {
    name: guid('tab'),
    title: t('dashboard.new_tab'),
    componentData: [],
    closable: true,
  }
  configItem.value.propValue.push(newTab)
  configItem.value.activeSubTabIndex = configItem.value.propValue.length - 1
  configItem.value.activeTabName = newTab.name
}

function deleteCur(param: any) {
  state.curItem = param
  let len = configItem.value.propValue.length
  while (len--) {
    if (configItem.value.propValue[len].name === param.name) {
      configItem.value.propValue.splice(len, 1)
      const activeIndex =
        (len - 1 + configItem.value.propValue.length) % configItem.value.propValue.length
      configItem.value.activeTabName = configItem.value.propValue[activeIndex].name
      configItem.value.activeSubTabIndex = configItem.value.propValue.length - 1
      state.tabShow = false
      nextTick(() => {
        state.tabShow = true
      })
    }
  }
}

function editCurTitle(param: any) {
  configItem.value.activeTabName = param.name
  state.curItem = param
  state.textarea = param.title
  state.dialogVisible = true
}

function handleCommand(command: any) {
  switch (command.command) {
    case 'editTitle':
      editCurTitle(command.param)
      break
    case 'deleteCur':
      deleteCur(command.param)
      break
  }
}

const beforeHandleCommand = (item: any, param: any) => {
  return {
    command: item,
    param: param,
  }
}
const isEditMode = computed(() => props.showPosition === 'canvas')
const outResizeEnd = () => {
  state.tabShow = false
  nextTick(() => {
    state.tabShow = true
  })
}
const addTabItem = (item: CanvasItem) => {
  // do addTabItem
  const index = configItem.value.propValue.findIndex(
    // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
    (tabItem) => configItem.value.activeTabName === tabItem.name
  )
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  const refInstance = currentInstance.refs['tabEditorRef_' + index][0]
  const newTabItem = _.cloneDeep(item)
  newTabItem.sizeX = 10
  newTabItem.sizeY = 10
  newTabItem.x = 1
  newTabItem.y = 1
  refInstance.addItemToBox(newTabItem)
}

function sureCurTitle() {
  state.curItem.title = state.textarea
  state.dialogVisible = false
}

const titleValid = computed(() => {
  return !!state.textarea && !!state.textarea.trim()
})

const titleStyle = (itemName: string) => {
  let style = {}
  if (configItem.value.activeTabName === itemName) {
    style = {
      fontSize: '16px',
    }
  } else {
    style = {
      fontSize: '14px',
    }
  }
  return style
}

onMounted(() => {
  currentInstance = getCurrentInstance()
  if (configItem.value.propValue.length > 0 && !configItem.value.activeTabName) {
    configItem.value.activeTabName = configItem.value.propValue[0].name
  }
})

defineExpose({
  addTabItem,
  outResizeEnd,
})
</script>

<template>
  <div :class="{ 'tab-moveout': configItem.moveOutActive }">
    <drag-handle></drag-handle>
    <custom-tab
      v-model="configItem.activeTabName"
      :addable="isEditMode"
      :font-color="state.headFontColor"
      :active-color="state.headFontActiveColor"
      :border-color="state.headBorderColor"
      :border-active-color="state.headBorderActiveColor"
      :hide-title="!showTabTitleFlag"
      @tab-add="addTab"
    >
      <template v-for="tabItem in configItem.propValue" :key="tabItem.name">
        <el-tab-pane
          class="el-tab-pane-custom"
          :lazy="isEditMode"
          :label="tabItem.title"
          :name="tabItem.name"
        >
          <template #label>
            <div class="custom-tab-title" @mousedown.stop>
              <span class="title-inner" :style="titleStyle(tabItem.name)"
                >{{ tabItem.title }}
                <span v-if="isEditMode">
                  <el-dropdown
                    popper-class="custom-de-tab-dropdown"
                    trigger="click"
                    @command="handleCommand"
                  >
                    <span class="el-dropdown-link">
                      <el-icon v-if="isEditMode" style="margin-top: 5px"><ArrowDown /></el-icon>
                    </span>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item :command="beforeHandleCommand('editTitle', tabItem)">
                          {{ t('dashboard.edit') }}
                        </el-dropdown-item>
                        <el-dropdown-item
                          v-if="configItem.propValue.length > 1"
                          :command="beforeHandleCommand('deleteCur', tabItem)"
                        >
                          {{ t('dashboard.delete') }}
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </span>
              </span>
            </div>
          </template>
        </el-tab-pane>
      </template>
      <template v-if="state.tabShow">
        <div
          v-for="(tabItem, index) in configItem.propValue"
          :key="tabItem.name + '-content'"
          class="tab-content-custom"
          :class="{ 'switch-hidden': configItem.activeTabName !== tabItem.name }"
        >
          <SQPreview
            v-if="showPosition === 'preview'"
            :ref="'tabPreviewRef_' + index"
            class="tab-dashboard-preview"
            :component-data="tabItem.componentData"
            :canvas-view-info="canvasViewInfo"
            :base-matrix-count="tabBaseMatrixCount"
            :canvas-id="tabItem.name"
          ></SQPreview>
          <DashboardEditor
            v-else
            :ref="'tabEditorRef_' + index"
            class="tab-dashboard-editor-main"
            :canvas-component-data="tabItem.componentData"
            :canvas-view-info="canvasViewInfo"
            :move-in-active="configItem.moveInActive"
            :base-matrix-count="tabBaseMatrixCount"
            :canvas-id="tabItem.name"
            :parent-config-item="configItem"
            @parent-add-item-box="(item) => emits('parentAddItemBox', item)"
          >
          </DashboardEditor>
        </div>
      </template>
    </custom-tab>
    <el-dialog
      v-model="state.dialogVisible"
      :title="t('dashboard.edit_title')"
      :append-to-body="true"
      width="30%"
      :show-close="false"
      :close-on-click-modal="false"
      center
    >
      <el-input
        v-model="state.textarea"
        maxlength="50"
        clearable
        :placeholder="t('common.input_content')"
      />
      <template #footer>
        <span class="dialog-footer">
          <el-button secondary @click="state.dialogVisible = false">{{
            t('common.cancel')
          }}</el-button>
          <el-button :disabled="!titleValid" type="primary" @click="sureCurTitle">{{
            t('common.confirm')
          }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="less">
::v-deep(.ed-tabs__header) {
  margin: 0 40px 0 12px !important;
}
::v-deep(.ed-tabs__nav-scroll) {
  margin: 0 12px !important;
}
.ed-dropdown-link {
  margin-top: 3px !important;
}

.tab-content-custom {
  position: absolute;
  width: 100%;
  height: 100%;
  margin: 2px !important; // border size
  div::-webkit-scrollbar {
    width: 0 !important;
    height: 0 !important;
  }
}

.tab-dashboard-preview {
  background: #ffffff !important;
}

.tab-dashboard-editor-main {
  height: 100% !important;
}

.tab-moveout {
  ::v-deep(.ed-tabs__content) {
    overflow: visible !important;
  }

  ::v-deep(.dashboard-editor-main) {
    overflow: visible !important;
  }
}

.custom-tab-title {
  padding: 0 8px 0 4px !important;
}

.switch-hidden {
  opacity: 0;
  z-index: -1;
}
</style>
