const { checkIsPercent, getAxesWithFilter, processMultiQuotaData } = require('./utils')

function getColumnOptions(baseOptions, axis, data) {

  const axes = getAxesWithFilter(axis)

  if (axes.x.length === 0 || axes?.y?.length === 0) {
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
      config.data,
    )
  }

  const x = axes.x
  const y = config.y
  const series = config.series

  const _data = checkIsPercent(y, config.data)

  const options = {
    ...baseOptions,
    type: 'interval',
    data: _data.data,
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
      y: { title: false },
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
          value: `${data[y[0].value]}${_data.isPercent ? '%' : ''}`,
        }
      } else {
        return { name: y[0].name, value: `${data[y[0].value]}${_data.isPercent ? '%' : ''}` }
      }
    },
    labels: [
      {
        text: (data) => {
          const value = data[y[0].value]
          if (value === undefined || value === null) {
            return ''
          }
          return `${value}${_data.isPercent ? '%' : ''}`
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