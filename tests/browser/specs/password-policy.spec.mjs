import { test, expect } from '@playwright/test'

async function fill(page, password = 'InitialPassword42!') {
  await page.locator('input[type=password]').nth(0).fill('OldPassword42!')
  await page.locator('input[type=password]').nth(1).fill(password)
  await page.locator('input[type=password]').nth(2).fill(password)
  await page.locator('input[type=password]').nth(2).press('Tab')
  await expect(page.locator('.ed-form-item__error')).toHaveCount(0)
}

for (const [lang, message] of [['zh-CN', '新密码不能为初始密码'], ['en', 'The new password cannot be the initial password']]) {
  test(`策略拒绝显示明确提示且允许纠正后保存 (${lang})`, async ({ page }) => {
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    let calls = 0
    await page.route('**/api/v1/user/pwd', async route => {
      calls++
      const denied = route.request().postDataJSON().new_pwd === 'InitialPassword42!'
      await route.fulfill({ status: denied ? 400 : 200, contentType: 'application/json', body: JSON.stringify(denied ? message : { code: 0, data: {} }) })
    })
    await page.goto(`/?lang=${lang}`)
    await fill(page)
    await page.getByRole('button', { name: 'Submit', exact: true }).click()
    await expect(page.locator('.pwd-submit-error')).toContainText(message)
    await expect(page.locator('input[type=password]')).toHaveCount(3)
    await expect(page.getByRole('status')).toHaveCount(0)
    await page.locator('input[type=password]').nth(1).fill('DifferentPassword42!')
    await expect(page.locator('.pwd-submit-error')).toHaveCount(0)
    await page.locator('input[type=password]').nth(2).fill('DifferentPassword42!')
    await page.locator('input[type=password]').nth(2).press('Tab')
    await expect(page.locator('.ed-form-item__error')).toHaveCount(0)
    await page.getByRole('button', { name: 'Submit', exact: true }).click()
    await expect(page.getByRole('status')).toHaveText('saved')
    expect(calls).toBe(2)
    expect(errors).toEqual([])
  })
}

test('策略关闭时初始密码可保存', async ({ page }) => {
  await page.route('**/api/v1/user/pwd', route => route.fulfill({ json: { code: 0, data: {} } }))
  await page.goto('/')
  await fill(page)
  await page.getByRole('button', { name: 'Submit', exact: true }).click()
  await expect(page.getByRole('status')).toHaveText('saved')
})

test('网络异常保留表单并显示友好提示', async ({ page }) => {
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route('**/api/v1/user/pwd', route => route.abort('failed'))
  await page.goto('/')
  await fill(page)
  await page.getByRole('button', { name: 'Submit', exact: true }).click()
  await expect(page.locator('.pwd-submit-error')).toContainText('密码修改失败，请稍后重试')
  await expect(page.locator('input[type=password]')).toHaveCount(3)
  expect(errors).toEqual([])
})
