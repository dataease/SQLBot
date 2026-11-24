const { getAxesWithFilter, prepareChartData } = require('./utils')

function getPieOptions(baseOptions, axis, data) {

  const axes = getAxesWithFilter(axis)

  if (axes.series.length === 0 || axes.y.length === 0) {
    return
  }

  const { y, series, data: chartData, formatValue } = prepareChartData(axes, data)

  return {
    ...baseOptions,
    type: 'interval',
    coordinate: { type: 'theta', outerRadius: 0.8 },
    transform: [{ type: 'stackY' }],
    data: chartData,
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
          `${data[series[0].value]}: ${formatValue(data)}`,
      },
    ],
    tooltip: {
      title: (data) => data[series[0].value],
      items: [
        (data) => {
          return {
            name: y[0].name,
            value: formatValue(data),
          }
        },
      ],
    },
  }

}

module.exports = { getPieOptions }
