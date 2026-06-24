import { BaseG2Chart } from '@/views/chat/component/BaseG2Chart.ts'
import type { ChartAxis, ChartData } from '@/views/chat/component/BaseChart.ts'
import type { G2Spec } from '@antv/g2'
import {
  checkIsPercent,
  formatNumber,
  getAxesWithFilter,
  processMultiQuotaData,
} from '@/views/chat/component/charts/utils.ts'

export class Line extends BaseG2Chart {
  constructor(id: string) {
    super(id, 'line')
  }

  init(axis: Array<ChartAxis>, data: Array<ChartData>, formatNumberFields: Array<string>) {
    super.init(axis, data, formatNumberFields)

    const axes = getAxesWithFilter(this.axis)

    if (axes.x.length == 0 || axes.y.length == 0) {
      console.debug({ instance: this })
      return
    }

    let config = {
      data: data,
      y: axes.y,
      series: axes.series,
    }
    if (axes.multiQuota.length > 0) {
      config = processMultiQuotaData(
        axes.x,
        config.y,
        axes.multiQuota,
        axes.multiQuotaName,
        config.data
      )
    }

    const x = axes.x
    const y = config.y
    const series = config.series

    const _data = checkIsPercent(y, config.data)

    console.debug({ 'render-info': { x: x, y: y, series: series, data: _data }, instance: this })

    const options: G2Spec = {
      ...this.chart.options(),
      type: 'view',
      data: _data.data,
      encode: {
        x: x[0].value,
        y: y[0].value,
        color: series.length > 0 ? series[0].value : undefined,
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
          labelFormatter: (value: any) => {
            const formatted = axes.y[0].formatNumber ? formatNumber(value) : value
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
      children: [
        {
          type: 'line',
          encode: {
            shape: 'smooth',
          },
          labels: this.showLabel
            ? [
                {
                  text: (data: any) => {
                    const value = data[y[0].value]
                    if (value === undefined || value === null) {
                      return ''
                    }
                    const v = y[0].formatNumber ? formatNumber(value) : value
                    return `${v}${_data.isPercent ? '%' : ''}`
                  },
                  style: {
                    dx: -10,
                    dy: -12,
                  },
                  transform: [
                    { type: 'contrastReverse' },
                    { type: 'exceedAdjust' },
                    { type: 'overlapHide' },
                  ],
                },
              ]
            : [],
          tooltip: (data: any) => {
            const v = y[0].formatNumber ? formatNumber(data[y[0].value]) : data[y[0].value]
            if (series.length > 0) {
              const s = series[0].formatNumber
                ? formatNumber(data[series[0].value])
                : data[series[0].value]
              return {
                name: s,
                value: `${v}${_data.isPercent ? '%' : ''}`,
              }
            } else {
              return {
                name: y[0].name,
                value: `${v}${_data.isPercent ? '%' : ''}`,
              }
            }
          },
        },
        {
          type: 'point',
          style: {
            fill: 'white',
          },
          encode: {
            size: 1.5,
          },
          tooltip: false,
        },
      ],
    } as G2Spec

    this.chart.options(options)
  }
}
