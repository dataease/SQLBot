import { test, expect } from '@playwright/test'

const spaces = [
  { id: '1', name: '空间A' },
  { id: '2', name: '空间B' },
]

async function mock(page) {
  const writes = []
  await page.route('**/api/system/**', async route => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    const reply = data => route.fulfill({ json: data })
    if (path.endsWith('/system/workspace') && request.method() === 'GET') return reply(spaces)
    if (path.endsWith('/ws_mapping')) {
      if (request.method() === 'GET') return reply([])
      writes.push({ method: request.method(), body: request.postDataJSON() })
      return reply(true)
    }
    return reply([])
  })
  return writes
}

async function openDialog(page, button) {
  await page.goto('/')
  await page.getByRole('button', { name: button }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  return dialog
}

async function selectAndHide(dialog) {
  const search = dialog.getByRole('textbox')
  await search.fill('空间A')
  await dialog.locator('.checkbox-group-block label').filter({ hasText: '空间A' }).click()
  await expect(dialog.locator('.w-full .hover-bg_select')).toHaveCount(1)
  await search.fill('空间B')
}

test('add authorization clears selections hidden by the search', async ({ page }) => {
  const writes = await mock(page)
  const dialog = await openDialog(page, '打开新增授权')

  await selectAndHide(dialog)
  await dialog.getByRole('button', { name: '清空', exact: true }).click()
  await expect(dialog.locator('.w-full .hover-bg_select')).toHaveCount(0)

  await dialog.getByRole('textbox').fill('')
  await expect(dialog.locator('.w-full .hover-bg_select')).toHaveCount(0)

  await dialog.getByRole('button', { name: '确定', exact: true }).click()
  await expect.poll(() => writes.length).toBe(1)
  expect(writes[0]).toEqual({ method: 'POST', body: [] })
})

test('edit authorization clears selections hidden by the search', async ({ page }) => {
  const writes = await mock(page)
  const dialog = await openDialog(page, '打开修改授权')

  await selectAndHide(dialog)
  await dialog.getByRole('button', { name: '清空', exact: true }).click()
  await expect(dialog.locator('.w-full .hover-bg_select')).toHaveCount(0)

  await dialog.getByRole('textbox').fill('')
  await expect(dialog.locator('.w-full .hover-bg_select')).toHaveCount(0)

  await dialog.getByRole('button', { name: '确定', exact: true }).click()
  await expect.poll(() => writes.length).toBe(1)
  expect(writes[0]).toEqual({
    method: 'PUT',
    body: { ws_ids: [], resolutions: [] },
  })
})
