const assert = require('node:assert/strict')
const { test } = require('node:test')
const { getColumnOptions } = require('../charts/column.js')
const { getBarOptions } = require('../charts/bar.js')
const { getLineOptions } = require('../charts/line.js')
const { getPieOptions } = require('../charts/pie.js')

const axes = [
  { type: 'x', name: 'Month', value: 'month' },
  { type: 'y', name: 'Rate', value: 'rate' },
]

test('a formatted zero does not mask a later percentage', () => {
  const rows = [
    { month: 'Jan', rate: '0.00' },
    { month: 'Feb', rate: ' +0 ' },
    { month: 'Mar', rate: '12.5%' },
  ]
  const chart = getColumnOptions({}, axes, rows)

  assert.equal(chart.data[2].rate, 12.5)
  assert.equal(chart.labels[0].text(chart.data[2]), '12.5%')
  assert.equal(rows[2].rate, '12.5%')
})

test('a grouped pie uses the unit of its displayed measure', () => {
  const axes = [
    { type: 'series', name: 'Month', value: 'month' },
    { type: 'y', name: 'Rate', value: 'rate' },
  ]
  const chart = getPieOptions({}, axes, [
    { month: 'Jan', rate: '0.00' },
    { month: 'Feb', rate: '12.5%' },
  ])
  assert.equal(chart.data[1].rate, 12.5)
  assert.equal(chart.labels[0].text(chart.data[0]), 'Jan: 0.00%')
  assert.equal(chart.tooltip.items[0](chart.data[1]).value, '12.5%')
})

test('percentages after leading zeros are detected even when another metric is nonzero', () => {
  const metrics = [
    { type: 'y', name: 'Value', value: 'sales', 'multi-quota': true },
    { type: 'y', name: 'Value', value: 'rate', 'multi-quota': true },
  ]
  const chart = getColumnOptions({}, [axes[0], ...metrics], [
    { month: 'Jan', sales: 200, rate: '0.00' },
    { month: 'Feb', sales: 400, rate: '-12.5%' },
  ])
  assert.deepEqual(chart.data.map(chart.labels[0].text), ['200', '0.00%', '400', '-12.5%'])
  assert.equal(chart.data[3][chart.encode.y], -12.5)
})

test('an ordinary numeric series keeps its units', () => {
  const chart = getColumnOptions({}, axes, [{ month: 'Jan', rate: 0 }, { month: 'Feb', rate: 12.5 }])

  assert.equal(chart.labels[0].text(chart.data[1]), '12.5')
})

for (const getOptions of [getColumnOptions, getBarOptions, getLineOptions]) {
  test(`${getOptions.name} keeps each metric's unit when folding rows`, () => {
    const sales = { type: 'y', name: 'Sales', value: 'sales', 'multi-quota': true }
    const rate = { ...axes[1], 'multi-quota': true }
    const rows = [
      { month: 'Jan', sales: '0.00', rate: '12.5%' },
      { month: 'Feb', sales: 200, rate: '15%' },
      { month: 'Mar', sales: 1250, rate: '0.00' },
    ]
    for (const metrics of [[sales, rate], [rate, sales]]) {
      const chart = getOptions({}, [axes[0], ...metrics], rows)
      const mark = chart.children?.[0] ?? chart
      const values = chart.data.map(row => [
        row.month, mark.tooltip(row).name, row[chart.encode.y],
        mark.labels[0].text(row), mark.tooltip(row).value,
      ])
      assert.deepEqual(values.filter(([, name]) => name === 'Sales'), [
        ['Jan', 'Sales', '0.00', '0.00', '0.00'],
        ['Feb', 'Sales', 200, '200', '200'],
        ['Mar', 'Sales', 1250, '1,250', '1,250'],
      ])
      assert.deepEqual(values.filter(([, name]) => name === 'Rate'), [
        ['Jan', 'Rate', 12.5, '12.5%', '12.5%'],
        ['Feb', 'Rate', 15, '15%', '15%'],
        ['Mar', 'Rate', '0.00', '0.00%', '0.00%'],
      ])
    }
    assert.equal(rows[0].rate, '12.5%')
  })
}
