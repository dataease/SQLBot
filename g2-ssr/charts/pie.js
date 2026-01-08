const { checkIsPercent, getAxesWithFilter } = require('./utils')

function getPieOptions(baseOptions, axis, data) {

  const { y, series } = getAxesWithFilter(axis)

  if (series.length === 0 || y.length === 0) {
    return
  }

  const _data = checkIsPercent(y, data)

  return {
    ...baseOptions,
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
    labels: [
      {
        position: 'spider',
        text: (data) =>
          `${data[series[0].value]}: ${data[y[0].value]}${_data.isPercent ? '%' : ''}`,
      },
    ],
    tooltip: {
      title: (data) => data[series[0].value],
      items: [
        (data) => {
          return {
            name: y[0].name,
            value: `${data[y[0].value]}${_data.isPercent ? '%' : ''}`,
          }
        },
      ],
    },
  }

}

module.exports = { getPieOptions }
