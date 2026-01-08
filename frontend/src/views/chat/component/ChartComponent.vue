<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted } from 'vue'
import { getChartInstance } from '@/views/chat/component/index.ts'
import type { BaseChart, ChartAxis, ChartData } from '@/views/chat/component/BaseChart.ts'
import { useEmitt } from '@/utils/useEmitt.ts'

const params = withDefaults(
  defineProps<{
    id: string | number
    type: string
    data?: Array<ChartData>
    columns?: Array<ChartAxis>
    x?: Array<ChartAxis>
    y?: Array<ChartAxis>
    series?: Array<ChartAxis>
    multiQuotaName?: string | undefined
  }>(),
  {
    data: () => [],
    columns: () => [],
    x: () => [],
    y: () => [],
    series: () => [],
    multiQuotaName: undefined,
  }
)

const chartId = computed(() => {
  return 'chart-component-' + params.id
})

const axis = computed(() => {
  const _list: Array<ChartAxis> = []
  params.columns.forEach((column) => {
    _list.push({ name: column.name, value: column.value })
  })
  params.x.forEach((column) => {
    _list.push({ name: column.name, value: column.value, type: 'x' })
  })
  params.y.forEach((column) => {
    _list.push({
      name: column.name,
      value: column.value,
      type: 'y',
      'multi-quota': column['multi-quota'],
    })
  })
  params.series.forEach((column) => {
    _list.push({ name: column.name, value: column.value, type: 'series' })
  })
  if (params.multiQuotaName) {
    _list.push({ name: params.multiQuotaName, value: params.multiQuotaName, type: 'other-info' })
  }
  return _list
})

let chartInstance: BaseChart | undefined

function renderChart() {
  chartInstance = getChartInstance(params.type, chartId.value)
  if (chartInstance) {
    chartInstance.init(axis.value, params.data)
    chartInstance.render()
  }
}

function destroyChart() {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = undefined
  }
}

function getExcelData() {
  return {
    axis: axis.value,
    data: params.data,
  }
}

useEmitt({
  name: 'view-render-all',
  callback: renderChart,
})

useEmitt({
  name: `view-render-${params.id}`,
  callback: renderChart,
})

defineExpose({
  renderChart,
  destroyChart,
  getExcelData,
})

onMounted(() => {
  nextTick(() => {
    renderChart()
  })
})

onUnmounted(() => {
  destroyChart()
})
</script>

<template>
  <div :id="chartId" class="chart-container"></div>
</template>

<style scoped lang="less">
.chart-container {
  height: 100%;
  width: 100%;
}
</style>
