import { test, expect } from '@playwright/test'
import fs from 'node:fs'

test('valid callback invokes validation exactly once', async ({ page }) => {
  // The async-validator library settles on the first callback; count all calls explicitly.
  const source = fs.readFileSync(new URL('../../../frontend/src/views/system/authentication/CasEditor.vue', import.meta.url), 'utf8')
  const body = source.match(/const validateCbUrl = \(rule, value, callback\) => \{([\s\S]*?)\n\}/)[1]
  const results = await page.evaluate(body => {
    const validate = new Function('rule', 'value', 'callback', 'getSQLBotAddr', 't', body)
    return ['https://app.example.invalid', 'https://app.example.invalid/', 'https://wrong.example.invalid/'].map(value => {
      const calls = []
      validate(null, value, error => calls.push(error ? 'error' : 'success'), () => 'https://app.example.invalid/', key => key)
      return calls
    })
  }, body)
  expect(results).toEqual([['success'], ['success'], ['error']])
})

for (const suffix of ['', '/']) {
  test(`saves historical root callback with suffix ${JSON.stringify(suffix)}`, async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Open CAS' }).click()
    const fields = page.getByRole('textbox')
    await fields.nth(0).fill('https://cas.example.invalid/cas/login/')
    await fields.nth(1).fill(`http://127.0.0.1:4219${suffix}`)
    await fields.nth(2).fill('{}')
    await page.getByRole('button', { name: '保存', exact: true }).click()
    await expect.poll(() => page.evaluate(() => window.savedConfigs.length)).toBe(1)
    const config = await page.evaluate(() => JSON.parse(window.savedConfigs[0].config))
    expect(config.casCallbackDomain).toBe(`http://127.0.0.1:4219${suffix}`)
    expect(config.idpUri).toBe('https://cas.example.invalid/cas/login/')
  })
}

test('rejects another callback origin', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Open CAS' }).click()
  const fields = page.getByRole('textbox')
  await fields.nth(0).fill('https://cas.example.invalid/cas')
  await fields.nth(1).fill('https://wrong.example.invalid/')
  await fields.nth(2).fill('{}')
  await page.getByRole('button', { name: '保存', exact: true }).click()
  await expect(page.locator('.ed-form-item__error')).toBeVisible()
  expect(await page.evaluate(() => window.savedConfigs)).toEqual([])
})

test('connection success explains its limited scope', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Open CAS' }).click()
  await page.getByRole('textbox').nth(0).fill('https://cas.example.invalid/cas')
  await page.getByRole('button', { name: '测试连接', exact: true }).click()
  await expect(page.getByText('CAS 登录端点可达，请通过实际登录验证回调及账号。')).toBeVisible()
})
