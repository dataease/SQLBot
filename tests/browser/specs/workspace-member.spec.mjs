import { test, expect } from '@playwright/test'

const users = [
  { id: '101', name: '张三', account: 'zhangsan_a' },
  { id: '102', name: '张三', account: 'zhangsan_b' },
]

async function mock(page) {
  const saves = []
  await page.route('**/api/system/workspace/uws/option/pager/**', async route => {
    const url = new URL(route.request().url())
    const [current, size] = url.pathname.split('/').slice(-2).map(Number)
    await route.fulfill({
      json: { items: users, page: current, size, total: users.length, total_pages: 1 },
    })
  })
  await page.route('**/api/system/workspace/uws', async route => {
    if (route.request().method() === 'POST') saves.push(route.request().postDataJSON())
    await route.fulfill({ json: true })
  })
  return { saves }
}

async function openDialog(page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Open members' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  return dialog
}

const selectedPanel = dialog => dialog.locator('.select-right_member')
const selectAllLabel = dialog =>
  dialog.locator('label.ed-checkbox').filter({ hasText: '全选' }).first()

test('same-name members stay distinct when searched by account', async ({ page }) => {
  const { saves } = await mock(page)
  const dialog = await openDialog(page)
  const search = dialog.getByRole('textbox')

  await search.fill('zhangsan_a')
  await dialog.locator('.checkbox-group-block label').filter({ hasText: 'zhangsan_a' }).click()
  await expect(selectedPanel(dialog)).toContainText('zhangsan_a')

  await search.fill('zhangsan_b')
  await expect(selectedPanel(dialog)).toContainText('zhangsan_a')
  await expect(selectedPanel(dialog)).not.toContainText('zhangsan_b')
  await expect(dialog.getByRole('checkbox').first()).not.toBeChecked()

  await dialog.locator('.checkbox-group-block label').filter({ hasText: 'zhangsan_b' }).click()
  await expect(selectedPanel(dialog)).toContainText('zhangsan_a')
  await expect(selectedPanel(dialog)).toContainText('zhangsan_b')

  await dialog.getByRole('button', { name: '添加', exact: true }).click()
  await expect.poll(() => saves.length).toBe(1)
  expect(saves[0].oid).toBe('99')
  expect(saves[0].uid_list.sort()).toEqual(['101', '102'])
})

test('add stays enabled when the selected member is filtered out', async ({ page }) => {
  const { saves } = await mock(page)
  const dialog = await openDialog(page)
  const search = dialog.getByRole('textbox')

  await search.fill('zhangsan_a')
  await dialog.locator('.checkbox-group-block label').filter({ hasText: 'zhangsan_a' }).click()
  await expect(selectedPanel(dialog)).toContainText('zhangsan_a')

  await search.fill('zhangsan_b')
  await expect(selectedPanel(dialog)).toContainText('zhangsan_a')
  const addButton = dialog.getByRole('button', { name: '添加', exact: true })
  await expect(addButton).toBeEnabled()

  await addButton.click()
  await expect.poll(() => saves.length).toBe(1)
  expect(saves[0].oid).toBe('99')
  expect(saves[0].uid_list).toEqual(['101'])
})

test('clear removes selections hidden by the current filter', async ({ page }) => {
  const { saves } = await mock(page)
  const dialog = await openDialog(page)
  const search = dialog.getByRole('textbox')

  await search.fill('zhangsan_a')
  await dialog.locator('.checkbox-group-block label').filter({ hasText: 'zhangsan_a' }).click()
  await search.fill('zhangsan_b')
  await dialog.locator('.checkbox-group-block label').filter({ hasText: 'zhangsan_b' }).click()
  await expect(selectedPanel(dialog)).toContainText('zhangsan_a')
  await expect(selectedPanel(dialog)).toContainText('zhangsan_b')

  await dialog.getByRole('button', { name: '清空', exact: true }).click()
  await expect(selectedPanel(dialog)).not.toContainText('zhangsan_a')
  await expect(selectedPanel(dialog)).not.toContainText('zhangsan_b')

  await search.fill('')
  await expect(selectedPanel(dialog)).not.toContainText('zhangsan_a')
  await expect(selectedPanel(dialog)).not.toContainText('zhangsan_b')
  await expect(dialog.getByRole('button', { name: '添加', exact: true })).toBeDisabled()
  expect(saves).toHaveLength(0)
})

test('select all on a same-name filtered list keeps hidden selections', async ({ page }) => {
  const { saves } = await mock(page)
  const dialog = await openDialog(page)
  const search = dialog.getByRole('textbox')

  await search.fill('zhangsan_a')
  await dialog.locator('.checkbox-group-block label').filter({ hasText: 'zhangsan_a' }).click()
  await expect(selectedPanel(dialog)).toContainText('zhangsan_a')

  await search.fill('zhangsan_b')
  await expect(dialog.getByRole('checkbox').first()).not.toBeChecked()

  await selectAllLabel(dialog).click()
  await expect(selectedPanel(dialog)).toContainText('zhangsan_a')
  await expect(selectedPanel(dialog)).toContainText('zhangsan_b')

  await dialog.getByRole('button', { name: '添加', exact: true }).click()
  await expect.poll(() => saves.length).toBe(1)
  expect(saves[0].oid).toBe('99')
  expect(saves[0].uid_list.sort()).toEqual(['101', '102'])
})
