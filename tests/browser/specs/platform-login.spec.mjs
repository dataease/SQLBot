import { test, expect } from '@playwright/test'
const categories = [{ name: 'wecom', enable: true }, { name: 'qrcode', enable: true }]
const org = { tree: [{ id: 'dept1', name: 'Synthetic department', options: { is_user: false } }], checked_list: [] }
async function setup(page) {
  await page.route('**/api/v1/system/authentication/platform/status', r => r.fulfill({ json: { code: 0, data: categories, msg: null } }))
  await page.route('**/api/v1/system/parameter/login', r => r.fulfill({ json: { code: 0, data: [], msg: null } }))
}
for (const [lang, message, retry] of [
  ['zh-CN', '登录失败，请重试或联系管理员。', '重新登录'],
  ['en', 'Login failed. Please try again or contact the administrator.', 'Log in again'],
]) test(`callback failure ends loading and permits fresh login (${lang})`, async ({ page }) => {
  await setup(page)
  let calls = 0
  await page.route('**/api/v1/system/platform/sso/6', async r => {
    calls++
    await r.fulfill({ status: 503, json: 'synthetic-private-token-in-unsafe-old-error' })
  })
  await page.goto(`/?lang=${lang}&code=synthetic-code&state=fit2cloud-wecom-qr#/login`)
  await expect(page.getByRole('status')).toHaveText('login ready')
  await expect(page.getByRole('alert')).toContainText(message)
  await expect(page.locator('body')).not.toContainText('synthetic-private-token-in-unsafe-old-error')
  await page.getByRole('button', { name: retry, exact: true }).click()
  await expect(page).not.toHaveURL(/code=/)
  await expect(page.getByRole('status')).toHaveText('login ready')
  expect(calls).toBe(1)
})
test('successful callback retains token and navigates', async ({ page }) => {
  await setup(page)
  await page.route('**/api/v1/system/platform/sso/6', r => r.fulfill({ json: { code: 0, data: { access_token: 'synthetic-session', exp: 42 }, msg: null } }))
  await page.goto('/?code=synthetic-code&state=fit2cloud-wecom-qr#/login')
  await expect.poll(() => page.evaluate(() => window.testUser.token)).toBe('synthetic-session')
  await expect.poll(() => page.evaluate(() => !!window.testRoute)).toBe(true)
  await expect(page.getByRole('alert')).toHaveCount(0)
})
test('sync failure removes fullscreen mask and retry loads departments', async ({ page }) => {
  const errors = []; page.on('pageerror', e => errors.push(e.message))
  let fail = true
  await page.route('**/api/v1/system/platform/org/6', async r => {
    if (fail) await r.fulfill({ status: 503, json: '平台认证暂时不可用，请重试或联系管理员。' })
    else await r.fulfill({ json: { code: 0, data: org, msg: null } })
  })
  await page.goto('/?view=sync')
  await page.getByRole('button', { name: 'Open sync' }).click()
  await expect(page.locator('.ed-message')).toContainText('平台认证暂时不可用')
  await expect(page.locator('.ed-loading-mask')).toHaveCount(0)
  await expect(page.getByRole('dialog')).not.toBeVisible()
  fail = false
  await page.getByRole('button', { name: 'Open sync' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByText('Synthetic department', { exact: true })).toBeVisible()
  expect(errors).toEqual([])
})
test('lazy node failure clears its spinner and expansion can retry', async ({ page }) => {
  let childCalls = 0
  await page.route('**/api/v1/system/platform/org/6', async r => {
    const data = r.request().postDataJSON()
    if (data.pid) {
      childCalls++
      if (childCalls === 1) return r.fulfill({ status: 503, json: 'Safe temporary failure' })
      return r.fulfill({ json: { code: 0, data: { tree: [{ id: 'user1', name: 'Synthetic member', options: { is_user: true } }] }, msg: null } })
    }
    return r.fulfill({ json: { code: 0, data: org, msg: null } })
  })
  await page.goto('/?view=sync')
  await page.getByRole('button', { name: 'Open sync' }).click()
  const node = page.getByRole('treeitem').filter({ hasText: 'Synthetic department' }).first()
  await node.locator('.ed-tree-node__expand-icon').first().click()
  await expect.poll(() => childCalls).toBe(1)
  await expect(node.locator('.is-loading')).toHaveCount(0)
  await node.locator('.ed-tree-node__expand-icon').first().click()
  await expect(page.getByText('Synthetic member', { exact: true })).toBeVisible()
})

test('switching load mode clears failure mask and can recover', async ({ page }) => {
  let fail = false
  await page.route('**/api/v1/system/platform/org/6', async r => {
    if (fail) return r.fulfill({ status: 503, json: 'Safe temporary failure' })
    return r.fulfill({ json: { code: 0, data: org, msg: null } })
  })
  await page.goto('/?view=sync')
  await page.getByRole('button', { name: 'Open sync' }).click()
  await expect(page.getByText('Synthetic department', { exact: true })).toBeVisible()
  fail = true
  await page.getByText('懒加载', { exact: true }).click()
  await expect(page.getByRole('checkbox', { name: '懒加载', exact: true })).not.toBeChecked()
  await expect(page.locator('.ed-message')).toContainText('Safe temporary failure')
  await expect(page.locator('.ed-loading-mask')).toHaveCount(0)
  await expect(page.getByText('Synthetic department', { exact: true })).toHaveCount(0)
  fail = false
  await page.getByText('懒加载', { exact: true }).click()
  await expect(page.getByRole('checkbox', { name: '懒加载', exact: true })).toBeChecked()
  await expect(page.getByText('Synthetic department', { exact: true })).toBeVisible()
})
