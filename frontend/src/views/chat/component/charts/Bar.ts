import { BaseG2Chart } from '@/views/chat/component/BaseG2Chart.ts'
import type { ChartAxis, ChartData } from '@/views/chat/component/BaseChart.ts'
import type { G2Spec } from '@antv/g2'
import {
  formatNumber,
  getAxesWithFilter,
  prepareChartData,
} from '@/views/chat/component/charts/utils.ts'
import { some } from 'lodash-es'

export class Bar extends BaseG2Chart {
  constructor(id: string) {
    super(id, 'bar')
  }

  init(axis: Array<ChartAxis>, data: Array<ChartData>, formatNumberFields: Array<string>) {
    super.init(axis, data, formatNumberFields)

    const axes = getAxesWithFilter(this.axis)

    if (axes.x.length == 0 || axes.y.length == 0) {
      console.debug({ instance: this })
      return
    }

    const x = axes.x
    const { y, series, data: chartData, formatValue } = prepareChartData(axes, data)

    console.debug({
      'render-info': { x: x, y: y, series: series, data: chartData },
      instance: this,
    })

    const options: G2Spec = {
      ...this.chart.options(),
      type: 'interval',
      data: chartData,
      coordinate: { transform: [{ type: 'transpose' }] },
      encode: {
        x: x[0].value,
        y: y[0].value,
        color: series.length > 0 ? series[0].value : undefined,
      },
      style: {
        radiusTopLeft: (d: ChartData) => {
          if (d[y[0].value] && d[y[0].value] > 0) {
            return 4
          }
          return 0
        },
        radiusTopRight: (d: ChartData) => {
          if (d[y[0].value] && d[y[0].value] > 0) {
            return 4
          }
          return 0
        },
        radiusBottomLeft: (d: ChartData) => {
          if (d[y[0].value] && d[y[0].value] < 0) {
            return 4
          }
          return 0
        },
        radiusBottomRight: (d: ChartData) => {
          if (d[y[0].value] && d[y[0].value] < 0) {
            return 4
          }
          return 0
        },
      },
      axis: {
        x: {
          title: false, // x[0].name,
          labelFontSize: 12,
          labelAutoHide: {
            type: 'hide',
            keepHeader: true,
            keepTail: true,
          },
          labelAutoRotate: false,
          labelAutoWrap: true,
          labelAutoEllipsis: true,
        },
        y: {
          title: false, // y[0].name,
          labelFontSize: 12,
          labelAutoHide: {
            type: 'hide',
            keepHeader: true,
          },
          labelAutoRotate: false,
          labelAutoWrap: true,
          labelAutoEllipsis: true,
          labelFormatter: (value: any) => {
            const formatted = some(axes.y, 'formatNumber') ? formatNumber(value) : value
            return String(formatted)
          },
        },
      },
      scale: {
        x: {
          nice: true,
        },
        y: {
          nice: true,
          type: 'linear',
        },
      },
      interaction: {
        elementHighlight: { background: true, region: true },
        tooltip: { series: series.length > 0, shared: true },
      },
      tooltip: (data: any) => {
        if (series.length > 0) {
          const s = series[0].formatNumber
            ? formatNumber(data[series[0].value])
            : data[series[0].value]
          return {
            name: s,
            value: formatValue(data),
          }
        } else {
          return {
            name: y[0].name,
            value: formatValue(data),
          }
        }
      },
      labels: this.showLabel
        ? [
            {
              text: (data: any) => {
                const value = data[y[0].value]
                if (value === undefined || value === null) {
                  return ''
                }
                return formatValue(data)
              },
              position: (data: any) => {
                if (data[y[0].value] < 0) {
                  return 'left'
                }
                return 'right'
              },
              transform: [
                { type: 'contrastReverse' },
                { type: 'exceedAdjust' },
                { type: 'overlapHide' },
              ],
            },
          ]
        : [],
    } as G2Spec

    if (series.length > 0) {
      options.transform = [{ type: 'stackY' }]
    }

    this.chart.options(options)
  }
}
