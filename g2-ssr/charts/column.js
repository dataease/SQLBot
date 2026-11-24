const { formatNumber, getAxesWithFilter, prepareChartData } = require('./utils')

function getColumnOptions(baseOptions, axis, data) {

  const axes = getAxesWithFilter(axis)

  if (axes.x.length === 0 || axes?.y?.length === 0) {
    return
  }

  const x = axes.x
  const { y, series, data: chartData, formatValue } = prepareChartData(axes, data)

  const options = {
    ...baseOptions,
    type: 'interval',
    data: chartData,
    encode: {
      x: x[0].value,
      y: y[0].value,
      color: series.length > 0 ? series[0].value : undefined,
    },
    style: {
      radiusTopLeft: (d) => {
        if (d[y[0].value] && d[y[0].value] > 0) {
          return 4
        }
        return 0
      },
      radiusTopRight: (d) => {
        if (d[y[0].value] && d[y[0].value] > 0) {
          return 4
        }
        return 0
      },
      radiusBottomLeft: (d) => {
        if (d[y[0].value] && d[y[0].value] < 0) {
          return 4
        }
        return 0
      },
      radiusBottomRight: (d) => {
        if (d[y[0].value] && d[y[0].value] < 0) {
          return 4
        }
        return 0
      },
    },
    axis: {
      x: {
        title: false,
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
        title: false,
        labelFormatter: (value) => {
          return String(formatNumber(value))
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
      elementHighlight: { background: true },
    },
    tooltip: (data) => {
      if (series.length > 0) {
        return {
          name: data[series[0].value],
          value: formatValue(data),
        }
      } else {
        return { name: y[0].name, value: formatValue(data) }
      }
    },
    labels: [
      {
        text: (data) => {
          const value = data[y[0].value]
          if (value === undefined || value === null) {
            return ''
          }
          return formatValue(data)
        },
        position: (data) => {
          if (data[y[0].value] < 0) {
            return 'bottom'
          }
          return 'top'
        },
        dy: -25,
        transform: [
          { type: 'contrastReverse' },
          { type: 'exceedAdjust' },
          { type: 'overlapHide' },
        ],
      },
    ],
  }

  if (series.length > 0) {
    options.transform = [{ type: 'stackY' }]
  }

  return options
}

module.exports = { getColumnOptions }