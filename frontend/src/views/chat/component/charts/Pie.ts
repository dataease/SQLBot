import { BaseG2Chart } from '@/views/chat/component/BaseG2Chart.ts'
import type { ChartAxis, ChartData } from '@/views/chat/component/BaseChart.ts'
import type { G2Spec } from '@antv/g2'
import {
  checkIsPercent,
  formatNumber,
  getAxesWithFilter,
} from '@/views/chat/component/charts/utils.ts'

export class Pie extends BaseG2Chart {
  constructor(id: string) {
    super(id, 'pie')
  }

  init(axis: Array<ChartAxis>, data: Array<ChartData>, formatNumberFields: Array<string>) {
    super.init(axis, data, formatNumberFields)
    const { y, series } = getAxesWithFilter(this.axis)

    if (series.length == 0 || y.length == 0) {
      console.debug({ instance: this })
      return
    }

    const _data = checkIsPercent(y, data)

    console.debug({ 'render-info': { y: y, series: series, data: _data }, instance: this })

    const options: G2Spec = {
      ...this.chart.options(),
      type: 'interval',
      coordinate: { type: 'theta', outerRadius: 0.8 },
      transform: [{ type: 'stackY' }],
      data: _data.data,
      encode: {
        y: y[0].value,
        color: series[0].value,
      },
      scale: {
        x: {
          nice: true,
        },
        y: {
          type: 'linear',
        },
      },
      legend: {
        color: { position: 'bottom', layout: { justifyContent: 'center' } },
      },
      animate: { enter: { type: 'waveIn' } },
      labels: this.showLabel
        ? [
            {
              position: 'spider',
              text: (data: any) => {
                const v = y[0].formatNumber ? formatNumber(data[y[0].value]) : data[y[0].value]
                return `${data[series[0].value]}: ${v}${_data.isPercent ? '%' : ''}`
              },
            },
          ]
        : [],
      tooltip: {
        title: (data: any) => {
          const s = series[0].formatNumber
            ? formatNumber(data[series[0].value])
            : data[series[0].value]
          return s
        },
        items: [
          (data: any) => {
            const v = y[0].formatNumber ? formatNumber(data[y[0].value]) : data[y[0].value]
            return {
              name: y[0].name,
              value: `${v}${_data.isPercent ? '%' : ''}`,
            }
          },
        ],
      },
    }

    this.chart.options(options)
  }
}
