import type { ChartAxis, ChartData } from '@/views/chat/component/BaseChart.ts'

/**
 * 为数值添加千分符，保持原有小数位数不变
 * 纯字符串处理，避免精度丢失
 * 支持：正负整数、小数、字符串格式的数值
 */
export function formatNumber(value: any): string | number {
  if (value === null || value === undefined || value === '') {
    return value
  }

  let str: string
  if (typeof value === 'string') {
    str = value.trim()
  } else if (typeof value === 'number') {
    str = String(value)
  } else {
    return value
  }

  const match = str.match(/^([+-])?(\d+)(\.(\d+))?$/)
  if (!match) {
    return value
  }

  const sign = match[1] || ''
  const intPart = match[2]
  const decPart = match[3] || ''

  const formattedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')

  return sign + formattedInt + decPart
}

export function getAxesWithFilter(axes: ChartAxis[]): {
  x: ChartAxis[]
  y: ChartAxis[] // 过滤后的 y
  series: ChartAxis[]
  multiQuota: boolean
  multiQuotaName?: string
} {
  const groups = {
    x: [] as ChartAxis[],
    y: [] as ChartAxis[],
    series: [] as ChartAxis[],
    multiQuota: false,
    multiQuotaName: undefined as string | undefined,
  }

  // 分组
  axes.forEach((axis) => {
    if (axis.type === 'x') groups.x.push(axis)
    else if (axis.type === 'y') groups.y.push(axis)
    else if (axis.type === 'series') groups.series.push(axis)
    else if (axis.type === 'other-info') groups.multiQuotaName = axis.value
  })

  // 应用过滤规则
  if (groups.series.length > 0) {
    groups.y = groups.y.slice(0, 1)
  } else {
    const multiQuotaY = groups.y.filter((item) => item['multi-quota'] === true)
    if (multiQuotaY.length > 0) {
      groups.multiQuota = true
      groups.y = multiQuotaY
    }
  }

  return groups
}

// Keep the original metric on folded rows, even when two metrics share a display name.
const metricIndex = Symbol('metricIndex')

function isPercentField(field: string, rows: ChartData[]) {
  const firstNonZero = rows.find((row) => {
    const value = row?.[field]
    return value != null && String(value).trim() !== '' && Number(value) !== 0
  })
  return String(firstNonZero?.[field]).trim().endsWith('%')
}

function plotValue(value: unknown, percent: boolean) {
  if (!percent || typeof value !== 'string' || !value.trim().endsWith('%')) return value
  const number = Number(value.trim().slice(0, -1))
  return Number.isNaN(number) ? 0 : number
}

export function prepareChartData(axes: ReturnType<typeof getAxesWithFilter>, rows: ChartData[]) {
  const metrics = (axes.multiQuota ? axes.y : axes.y.slice(0, 1)).map((axis) => ({
    axis,
    percent: isPercentField(axis.value, rows),
  }))
  const valueField = axes.multiQuota ? 'sqlbot_auto_quota' : axes.y[0].value

  function formatValue(row: ChartData & { [metricIndex]?: number }) {
    const { axis, percent } = metrics[row[metricIndex] ?? 0]
    const value = row[valueField]
    return `${axis.formatNumber ? formatNumber(value) : value}${percent ? '%' : ''}`
  }

  if (!axes.multiQuota) {
    return {
      y: axes.y,
      series: axes.series,
      data: rows.map((row) => ({
        ...row,
        [valueField]: plotValue(row?.[valueField], metrics[0].percent),
      })),
      formatValue,
    }
  }

  const data = rows.flatMap((row) => {
    const dimensions: ChartData = {}
    for (const axis of axes.x) dimensions[axis.value] = row[axis.value]
    return metrics.map(({ axis, percent }, index) => ({
      ...dimensions,
      [valueField]: plotValue(row[axis.value], percent),
      sqlbot_auto_series: axis.name,
      [metricIndex]: index,
    }))
  })
  return {
    y: [{ name: valueField, value: valueField, type: 'y' } as ChartAxis],
    series: [
      {
        name: axes.multiQuotaName ?? 'sqlbot_auto_series',
        value: 'sqlbot_auto_series',
        type: 'series',
      } as ChartAxis,
    ],
    data,
    formatValue,
  }
}
