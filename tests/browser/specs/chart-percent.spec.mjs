import { test, expect } from '@playwright/test'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const frontend = fileURLToPath(new URL('../../../frontend/', import.meta.url))
const require = createRequire(path.join(frontend, 'package.json'))
let chartScript

test.beforeAll(async () => {
  const { build } = await import(require.resolve('vite'))
  const result = await build({
    root: frontend,
    configFile: false,
    logLevel: 'error',
    resolve: { alias: { '@': path.join(frontend, 'src') } },
    build: {
      write: false,
      lib: {
        entry: path.join(frontend, 'src/views/chat/component/charts/Column.ts'),
        name: 'SQLBotCharts',
        formats: ['iife'],
      },
    },
  })
  chartScript = result[0].output[0].code
})

test('a shared column tooltip keeps the sales amount and margin units', async ({ page }) => {
  await page.setContent('<div id="chart" style="width:640px;height:360px"></div>')
  await page.addScriptTag({ content: chartScript })
  const labels = await page.evaluate(async () => {
    const chart = new window.SQLBotCharts.Column('chart')
    chart.showLabel = true
    chart.init([
      { type: 'x', name: 'Month', value: 'month' },
      { type: 'y', name: 'Sales', value: 'sales', 'multi-quota': true },
      { type: 'y', name: 'Margin', value: 'margin', 'multi-quota': true },
    ], [
      { month: 'Jan', sales: '0.00', margin: '12.5%' },
      { month: 'Feb', sales: 200, margin: '15%' },
    ], [])
    await chart.chart.render()
    const document = chart.chart.getContext().canvas.document
    return document.getElementsByClassName('label').map(label => label.style.text)
  })
  expect(labels).toEqual(expect.arrayContaining(['0.00', '12.5%', '200', '15%']))
  const chart = page.locator('#chart')
  await chart.hover({ position: { x: 465, y: 190 } })
  await expect(chart).toContainText('Sales')
  await expect(chart.getByText('200', { exact: true })).toBeVisible()
  await expect(chart.getByText('15%', { exact: true })).toBeVisible()
})
