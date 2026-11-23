const assert = require('node:assert/strict')
const { test } = require('node:test')
const { getColumnOptions } = require('../charts/column.js')

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

test('an ordinary numeric series keeps its units', () => {
  const chart = getColumnOptions({}, axes, [{ month: 'Jan', rate: 0 }, { month: 'Feb', rate: 12.5 }])

  assert.equal(chart.labels[0].text(chart.data[1]), '12.5')
})
