<script setup lang="ts">
import type { ChatMessage } from '@/api/chat.ts'
import DisplayChartBlock from '@/views/chat/component/DisplayChartBlock.vue'
import ChartPopover from '@/views/chat/chat-block/ChartPopover.vue'
import { computed, ref, watch } from 'vue'
import { useClipboard } from '@vueuse/core'
import { concat } from 'lodash-es'
import type { ChartTypes } from '@/views/chat/component/BaseChart.ts'
import ICON_BAR from '@/assets/svg/chart/icon_bar_outlined.svg'
import ICON_COLUMN from '@/assets/svg/chart/icon_dashboard_outlined.svg'
import ICON_LINE from '@/assets/svg/chart/icon_chart-line.svg'
import ICON_PIE from '@/assets/svg/chart/icon_pie_outlined.svg'
import ICON_TABLE from '@/assets/svg/chart/icon_form_outlined.svg'
import icon_sql_outlined from '@/assets/svg/icon_sql_outlined.svg'
import icon_export_outlined from '@/assets/svg/icon_export_outlined.svg'
import icon_file_image_colorful from '@/assets/svg/icon_file-image_colorful.svg'
import icon_file_excel_colorful from '@/assets/svg/icon_file-excel_colorful.svg'
import icon_into_item_outlined from '@/assets/svg/icon_into-item_outlined.svg'
import icon_window_max_outlined from '@/assets/svg/icon_window-max_outlined.svg'
import icon_window_mini_outlined from '@/assets/svg/icon_window-mini_outlined.svg'
import icon_copy_outlined from '@/assets/svg/icon_copy_outlined.svg'
import { useI18n } from 'vue-i18n'
import SQLComponent from '@/views/chat/component/SQLComponent.vue'
import { useAssistantStore } from '@/stores/assistant'
import AddViewDashboard from '@/views/dashboard/common/AddViewDashboard.vue'
import html2canvas from 'html2canvas'
import { chatApi } from '@/api/chat'

const props = withDefaults(
  defineProps<{
    message: ChatMessage
    isPredict?: boolean
    chatType?: ChartTypes
    enlarge?: boolean
  }>(),
  {
    isPredict: false,
    chatType: undefined,
    enlarge: false,
  }
)

const { copy } = useClipboard({ legacy: true })
const loading = ref<boolean>(false)
const { t } = useI18n()
const addViewRef = ref(null)
const emits = defineEmits(['exitFullScreen'])

const dataObject = computed<{
  fields: Array<string>
  data: Array<{ [key: string]: any }>
  limit: number | undefined
}>(() => {
  if (props.message?.record?.data) {
    if (typeof props.message?.record?.data === 'string') {
      return JSON.parse(props.message.record.data)
    } else {
      return props.message.record.data
    }
  }
  return {}
})
const assistantStore = useAssistantStore()
const isCompletePage = computed(() => !assistantStore.getAssistant || assistantStore.getEmbedded)

const isAssistant = computed(() => assistantStore.getAssistant)

const chartId = computed(() => props.message?.record?.id + (props.enlarge ? '-fullscreen' : ''))

const data = computed(() => {
  if (props.isPredict) {
    let _list = []
    if (
      props.message?.record?.predict_data &&
      typeof props.message?.record?.predict_data === 'string'
    ) {
      if (
        props.message?.record?.predict_data.length > 0 &&
        props.message?.record?.predict_data.trim().startsWith('[') &&
        props.message?.record?.predict_data.trim().endsWith(']')
      ) {
        try {
          _list = JSON.parse(props.message?.record?.predict_data)
        } catch (e) {
          console.error(e)
        }
      }
    } else {
      if (props.message?.record?.predict_data?.length > 0) {
        _list = props.message?.record?.predict_data
      }
    }
    if (_list.length == 0) {
      return _list
    }

    if (dataObject.value.data && dataObject.value.data?.length > 0) {
      return concat(dataObject.value.data, _list)
    }
    return _list
  } else {
    return dataObject.value.data
  }
})

const chartRef = ref()

const chartObject = computed<{
  type: ChartTypes
  title: string
  axis: {
    x: { name: string; value: string }
    y: { name: string; value: string }
    series: { name: string; value: string }
  }
  columns: Array<{ name: string; value: string }>
}>(() => {
  if (props.message?.record?.chart) {
    return JSON.parse(props.message.record.chart)
  }
  return {}
})

const currentChartType = ref<ChartTypes | undefined>(
  props.chatType ?? chartObject.value.type ?? 'table'
)

const chartType = computed<ChartTypes>({
  get() {
    if (currentChartType.value) {
      return currentChartType.value
    }
    return props.chatType ?? chartObject.value.type ?? 'table'
  },
  set(v) {
    currentChartType.value = v
  },
})

const chartTypeList = computed(() => {
  const _list = []
  if (chartObject.value) {
    switch (chartObject.value.type) {
      case 'table':
        break
      case 'column':
      case 'bar':
      case 'line':
        _list.push({
          value: 'column',
          name: t('chat.chart_type.column'),
          icon: ICON_COLUMN,
        })
        _list.push({
          value: 'bar',
          name: t('chat.chart_type.bar'),
          icon: ICON_BAR,
        })
        _list.push({
          value: 'line',
          name: t('chat.chart_type.line'),
          icon: ICON_LINE,
        })
        break
      case 'pie':
        _list.push({
          value: 'pie',
          name: t('chat.chart_type.pie'),
          icon: ICON_PIE,
        })
    }
  }

  return _list
})

function changeTable() {
  onTypeChange('table')
}

function onTypeChange(val: any) {
  chartType.value = val
  chartRef.value?.onTypeChange()
}

function reloadChart() {
  chartRef.value?.onTypeChange()
}

const dialogVisible = ref(false)

function openFullScreen() {
  dialogVisible.value = true
}

function closeFullScreen() {
  emits('exitFullScreen')
}

function onExitFullScreen() {
  dialogVisible.value = false
}

const sqlShow = ref(false)

function showSql() {
  sqlShow.value = true
}

function addToResource() {
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  const readyData = {
    eventName: 'sqlbot_add_to_resource',
    busi: props.message?.record?.sql_prase,
    ready: true,
    messageId: 100001,
  }
  console.log('sqlbot-readyData', JSON.stringify(readyData))
  window.parent.postMessage(readyData, '*')
}

function addToDashboard() {
  const recordeInfo = {
    id: '1-1',
    data: {
      data: data.value,
    },
    chart: {},
  }
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  const chartBaseInfo = JSON.parse(props.message?.record?.chart)
  recordeInfo['chart'] = {
    type: currentChartType.value,
    title: chartBaseInfo.title,
    columns: chartBaseInfo.columns,
    xAxis: chartBaseInfo.axis?.x ? [chartBaseInfo.axis.x] : [],
    yAxis: chartBaseInfo.axis?.y ? [chartBaseInfo.axis.y] : [],
    series: chartBaseInfo.axis?.series ? [chartBaseInfo.axis.series] : [],
  }
  // @ts-expect-error eslint-disable-next-line @typescript-eslint/ban-ts-comment
  addViewRef.value?.optInit(recordeInfo)
}

function copyText() {
  if (props.message?.record?.sql) {
    copy(props.message.record.sql).then(() => {
      ElMessage.success(t('embedded.copy_successful'))
    })
  }
}

const exportRef = ref()

function exportToExcel() {
  if (chartRef.value) {
    loading.value = true
    chatApi
      .export2Excel({ ...chartRef.value?.getExcelData(), name: chartObject.value.title })
      .then((res) => {
        const blob = new Blob([res], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        const link = document.createElement('a')
        link.href = URL.createObjectURL(blob)
        link.download = `${chartObject.value.title ?? 'Excel'}.xlsx`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      })
      .catch(async (error) => {
        if (error.response) {
          try {
            let text = await error.response.data.text()
            try {
              text = JSON.parse(text)
            } finally {
              ElMessage({
                message: text,
                type: 'error',
                showClose: true,
              })
            }
          } catch (e) {
            console.error('Error processing error response:', e)
          }
        } else {
          console.error('Other error:', error)
          ElMessage({
            message: error,
            type: 'error',
            showClose: true,
          })
        }
      })
      .finally(() => {
        loading.value = false
      })
    exportRef.value?.hide()
  }
}

function exportToImage() {
  const obj = document.getElementById('chart-component-' + chartId.value)
  if (obj) {
    html2canvas(obj).then((canvas) => {
      canvas.toBlob(function (blob) {
        if (blob) {
          const link = document.createElement('a')
          link.download = (chartObject.value.title ?? 'chart') + '.png' // Specify filename
          link.href = URL.createObjectURL(blob)
          document.body.appendChild(link) // Append to body to make it clickable
          link.click() // Programmatically click the link
          document.body.removeChild(link) // Clean up
          URL.revokeObjectURL(link.href) // Release the object URL
        }
      }, 'image/png')
    })
  }
  exportRef.value?.hide()
}

defineExpose({
  reloadChart,
})

watch(
  () => chartObject.value?.type,
  (val) => {
    if (val) {
      currentChartType.value = val
    }
  }
)
</script>

<template>
  <div
    v-if="
      !message.isTyping &&
      ((!isPredict && (message?.record?.sql || message?.record?.chart)) ||
        (isPredict && message?.record?.chart && data.length > 0))
    "
    v-loading.fullscreen.lock="loading"
    class="chart-component-container"
    :class="{ 'full-screen': enlarge }"
  >
    <div class="header-bar">
      <div class="title">
        {{ chartObject.title }}
      </div>
      <div class="buttons-bar">
        <div class="chart-select-container">
          <el-tooltip effect="dark" :offset="8" :content="t('chat.type')" placement="top">
            <ChartPopover
              v-if="chartTypeList.length > 0"
              :chart-type-list="chartTypeList"
              :chart-type="chartType"
              :title="t('chat.type')"
              @type-change="onTypeChange"
            ></ChartPopover>
          </el-tooltip>

          <el-tooltip
            effect="dark"
            :offset="8"
            :content="t('chat.chart_type.table')"
            placement="top"
          >
            <el-button
              class="tool-btn"
              :class="{ 'chart-active': currentChartType === 'table' }"
              text
              @click="changeTable"
            >
              <el-icon size="16">
                <ICON_TABLE />
              </el-icon>
            </el-button>
          </el-tooltip>
        </div>

        <div v-if="message?.record?.sql">
          <el-tooltip effect="dark" :offset="8" :content="t('chat.show_sql')" placement="top">
            <el-button class="tool-btn" text @click="showSql">
              <el-icon size="16">
                <icon_sql_outlined />
              </el-icon>
            </el-button>
          </el-tooltip>
        </div>
        <div v-if="message?.record?.chart">
          <el-popover
            ref="exportRef"
            trigger="click"
            popper-class="export_to_select"
            placement="bottom"
          >
            <template #reference>
              <div>
                <el-tooltip
                  effect="dark"
                  :offset="8"
                  :content="t('chat.export_to')"
                  placement="top"
                >
                  <el-button class="tool-btn" text>
                    <el-icon size="16">
                      <icon_export_outlined />
                    </el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </template>
            <div class="popover">
              <div class="popover-content">
                <div class="title">{{ t('chat.export_to') }}</div>
                <div class="popover-item" @click="exportToExcel">
                  <el-icon size="16">
                    <icon_file_excel_colorful />
                  </el-icon>
                  <div class="model-name">{{ t('chat.excel') }}</div>
                </div>
                <div
                  v-if="currentChartType !== 'table'"
                  class="popover-item"
                  @click="exportToImage"
                >
                  <el-icon size="16">
                    <icon_file_image_colorful />
                  </el-icon>
                  <div class="model-name">{{ t('chat.picture') }}</div>
                </div>
              </div>
            </div>
          </el-popover>
        </div>
        <div v-if="message?.record?.sql_prase">
          <el-tooltip effect="dark" :content="t('chat.add_to_dataV')" placement="top">
            <el-button class="tool-btn" text @click="addToResource">
              <el-icon size="16">
                <icon_into_item_outlined />
              </el-icon>
            </el-button>
          </el-tooltip>
        </div>
        <div v-if="message?.record?.chart && !isAssistant">
          <el-tooltip effect="dark" :content="t('chat.add_to_dashboard')" placement="top">
            <el-button class="tool-btn" text @click="addToDashboard">
              <el-icon size="16">
                <icon_into_item_outlined />
              </el-icon>
            </el-button>
          </el-tooltip>
        </div>
        <div class="divider" />
        <div v-if="!enlarge">
          <el-tooltip
            effect="dark"
            :offset="8"
            :content="!isCompletePage ? $t('common.zoom_in') : t('chat.full_screen')"
            placement="top"
          >
            <el-button class="tool-btn" text @click="openFullScreen">
              <el-icon size="16">
                <icon_window_max_outlined />
              </el-icon>
            </el-button>
          </el-tooltip>
        </div>
        <div v-else>
          <el-tooltip
            effect="dark"
            :offset="8"
            :content="!isCompletePage ? $t('common.zoom_out') : t('chat.exit_full_screen')"
            placement="top"
          >
            <el-button class="tool-btn" text @click="closeFullScreen">
              <el-icon size="16">
                <icon_window_mini_outlined />
              </el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>
    </div>

    <template v-if="message?.record?.chart">
      <div class="chart-block">
        <DisplayChartBlock
          :id="chartId"
          ref="chartRef"
          :chart-type="chartType"
          :message="message"
          :data="data"
        />
      </div>
      <div v-if="dataObject.limit" class="over-limit-hint">
        {{ t('chat.data_over_limit', [dataObject.limit]) }}
      </div>
    </template>

    <AddViewDashboard ref="addViewRef"></AddViewDashboard>
    <el-dialog
      v-if="!enlarge"
      v-model="dialogVisible"
      fullscreen
      :show-close="false"
      class="chart-fullscreen-dialog"
      header-class="chart-fullscreen-dialog-header"
      body-class="chart-fullscreen-dialog-body"
    >
      <ChartBlock
        v-if="dialogVisible"
        :message="message"
        :is-predict="isPredict"
        :chat-type="chartType"
        enlarge
        @exit-full-screen="onExitFullScreen"
      />
    </el-dialog>

    <el-drawer
      v-model="sqlShow"
      :size="!isCompletePage ? '100%' : '600px'"
      :title="t('chat.show_sql')"
      direction="rtl"
      body-class="chart-sql-drawer-body"
    >
      <div class="sql-block">
        <SQLComponent
          v-if="message.record?.sql"
          :sql="message.record?.sql"
          style="margin-top: 12px"
        />
        <el-button v-if="message.record?.sql" circle class="input-icon" @click="copyText">
          <el-icon size="16">
            <icon_copy_outlined />
          </el-icon>
        </el-button>
      </div>
    </el-drawer>
  </div>
</template>

<style lang="less">
.chart-fullscreen-dialog {
  padding: 0;
}

.chart-fullscreen-dialog-header {
  display: none;
}

.chart-fullscreen-dialog-body {
  padding: 0;
}

.chart-sql-drawer-body {
  padding: 24px;
}

.export_to_select.export_to_select {
  padding: 4px 0;
  width: 120px !important;
  min-width: 120px !important;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border: 1px solid #dee0e3;

  .popover {
    .popover-content {
      padding: 0 4px;
      max-height: 300px;
      overflow-y: auto;

      .title {
        width: 100%;
        height: 32px;
        margin-bottom: 2px;
        display: flex;
        align-items: center;
        padding-left: 8px;
        color: #8f959e;
      }
    }

    .popover-item {
      height: 32px;
      display: flex;
      align-items: center;
      padding-left: 12px;
      padding-right: 8px;
      margin-bottom: 2px;
      position: relative;
      border-radius: 4px;
      cursor: pointer;

      &:last-child {
        margin-bottom: 0;
      }

      &:hover {
        background: #1f23291a;
      }

      .model-name {
        margin-left: 8px;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        max-width: 220px;
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
<style scoped lang="less">
.chart-component-container {
  width: 100%;
  padding: 16px;
  display: flex;
  flex-direction: column;

  border: 1px solid rgba(222, 224, 227, 1);
  border-radius: 12px;

  &.full-screen {
    border: unset;
    border-radius: unset;
    padding: 0;

    .header-bar {
      border-bottom: 1px solid rgba(31, 35, 41, 0.15);
      height: 55px;
      padding: 16px 24px;
    }

    .chart-block {
      margin: unset;
      padding: 16px;

      height: calc(100vh - 56px);
    }
  }

  .header-bar {
    height: 32px;
    display: flex;

    align-items: center;
    flex-direction: row;
    gap: 16px;

    .tool-btn {
      width: 24px;
      height: 24px;

      font-size: 16px;
      font-weight: 400;
      line-height: 24px;
      border-radius: 6px;
      color: rgba(100, 106, 115, 1);

      .tool-btn-inner {
        display: flex;
        flex-direction: row;
        align-items: center;
      }

      &:hover {
        background: rgba(31, 35, 41, 0.1);
      }

      &:active {
        background: rgba(31, 35, 41, 0.1);
      }
    }

    .chart-active {
      background: var(--ed-color-primary-1a, rgba(28, 186, 144, 0.1));
      color: var(--ed-color-primary, rgba(28, 186, 144, 1));
      border-radius: 6px;

      :deep(.ed-select__wrapper) {
        background: transparent;
      }

      :deep(.ed-select__input) {
        color: var(--ed-color-primary, rgba(28, 186, 144, 1));
      }

      :deep(.ed-select__placeholder) {
        color: var(--ed-color-primary, rgba(28, 186, 144, 1));
      }

      :deep(.ed-select__caret) {
        color: var(--ed-color-primary, rgba(28, 186, 144, 1));
      }
    }

    .title {
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;

      color: rgba(31, 35, 41, 1);
      font-weight: 500;
      font-size: 16px;
      line-height: 24px;
    }

    .buttons-bar {
      display: flex;
      flex-direction: row;
      align-items: center;

      gap: 16px;

      .divider {
        width: 1px;
        height: 16px;
        border-left: 1px solid rgba(31, 35, 41, 0.15);
      }
    }

    .chart-select-container {
      padding: 3px;
      display: flex;
      flex-direction: row;
      gap: 4px;
      border-radius: 6px;

      border: 1px solid rgba(217, 220, 223, 1);

      .chart-select {
        min-width: 40px;
        width: 40px;
        height: 24px;

        :deep(.ed-select__wrapper) {
          padding: 4px;
          min-height: 24px;
          box-shadow: unset;
          border-radius: 6px;

          &:hover {
            background: rgba(31, 35, 41, 0.1);
          }

          &:active {
            background: rgba(31, 35, 41, 0.1);
          }
        }

        :deep(.ed-select__caret) {
          font-size: 12px !important;
        }
      }
    }
  }

  .chart-block {
    height: 352px;
    width: 100%;

    margin-top: 16px;
  }
  .over-limit-hint {
    min-height: 24px;
    line-height: 24px;
    font-size: 14px;
  }
}

.sql-block {
  position: relative;

  .input-icon {
    min-width: unset;
    position: absolute;
    top: 12px;
    right: 12px;
    color: #1f2329;
    display: none;
    background-color: transparent !important;

    border-color: #dee0e3;
    box-shadow: 0px 4px 8px 0px #1f23291a;

    &:hover,
    &:focus {
      color: var(--ed-color-primary);
    }

    &:active {
      color: var(--ed-color-primary-dark-2);
    }
  }

  &:hover {
    .input-icon {
      display: flex;
    }
  }
}
</style>
