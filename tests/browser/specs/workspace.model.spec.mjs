// Real product routes/components with controlled API and xpack identity adapters.
// Backend persistence/authorization/provider calls are tested separately in Python.
import { test, expect } from '@playwright/test'

test.skip(!process.env.PLAYWRIGHT_BASE_URL, 'An explicitly started frontend is required')
test.setTimeout(60_000)

async function setup(page) {
  const state = {
    settings: { enable_custom_model: false, custom_model: null },
    mapped: ['1'],
    mutations: [],
    deleted: false,
  }
  const models = [
    { id: '10', name: 'System model', base_model: 'system', supplier: 15, model_type: 0, default_model: true, ws_mapping_count: 0 },
    { id: '20', name: 'Workspace model', base_model: 'workspace', supplier: 15, model_type: 0, default_model: false, ws_mapping_count: 1 },
    { id: '30', name: 'Replacement model', base_model: 'replacement', supplier: 15, model_type: 0, default_model: false, ws_mapping_count: 1 },
  ]
  await page.addInitScript(() => {
    for (const [key, value] of Object.entries({ 'user.token': 'offline-ui-test', 'user.language': 'en' })) {
      localStorage.setItem(`sqlbot_v1_${key}`, JSON.stringify({ c: Date.now(), e: Date.now() + 3600000, v: JSON.stringify(value) }))
    }
  })
  await page.route('**/*', async route => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path.includes('/xpack_static/license-generator.umd.js')) {
      return route.fulfill({ contentType: 'application/javascript', body: 'window.LicenseGenerator={init:async()=>{},generateRouters:()=>{},getLicense:()=>({status:"invalid"})};' })
    }
    const json = data => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ code: 0, data, msg: null }) })
    if (path.endsWith('/user/info')) return json({ id: '1', oid: '1', name: 'Test admin', account: 'admin', language: 'en', weight: 1, origin: 0, exp: 9999999999, time: 1 })
    if (path.endsWith('/system/workspace/1/model')) {
      if (request.method() === 'PUT') {
        state.settings = request.postDataJSON()
        state.mutations.push(state.settings)
        return json({})
      }
      return json({ ...state.settings, models: models.slice(1), model_valid: ['20', '30'].includes(state.settings.custom_model) })
    }
    if (path.endsWith('/system/workspace')) return json([{ id: 1, name: 'Workspace A' }, { id: 2, name: 'Workspace B' }])
    if (path.includes('/system/workspace/uws/pager/')) return json({ items: [], total: 0 })
    if (path.endsWith('/system/aimodel/20/workspace_impact')) {
      return json([{ workspace_id: '1', workspace_name: 'Workspace A', uses_default: true, assistants: ['Existing assistant'], models: [models[2]] }])
    }
    if (path.endsWith('/system/aimodel/20/ws_mapping')) {
      if (request.method() !== 'GET') {
        state.mutations.push(request.postDataJSON())
        state.mapped = []
      }
      return json(state.mapped)
    }
    if (path.endsWith('/system/aimodel/20') && request.method() === 'DELETE') {
      state.mutations.push(request.postDataJSON())
      state.deleted = true
      return json(null)
    }
    if (path.endsWith('/system/aimodel')) return json(models.filter(item => !state.deleted || item.id !== '20'))
    // Unknown API calls stay offline; scripts/styles use the real Vite frontend.
    if (['xhr', 'fetch'].includes(request.resourceType())) return json([])
    return route.continue()
  })
  return state
}

test('workspace model dialog saves, cancels and reloads using the real management page', async ({ page }) => {
  const state = await setup(page)
  await page.goto('/#/system/workspace')
  await page.getByRole('button', { name: 'Model management', exact: true }).click()
  let dialog = page.getByRole('dialog', { name: 'Model management', exact: true })
  await expect(dialog.getByText('Workspace A', { exact: true })).toBeVisible()
  await dialog.getByText('Specify model', { exact: true }).click()
  await expect(dialog.getByText(/Leaving this empty disables/)).toBeVisible()
  await dialog.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(dialog).not.toBeVisible()
  expect(state.settings).toEqual({ enable_custom_model: true, custom_model: null })
  await page.reload()
  await page.getByRole('button', { name: 'Model management', exact: true }).click()
  dialog = page.getByRole('dialog', { name: 'Model management', exact: true })
  await expect(dialog.getByRole('radio', { name: 'Specify model', exact: true })).toBeChecked()
  await dialog.getByRole('combobox').click()
  await page.getByRole('option', { name: 'Workspace model', exact: true }).click()
  await dialog.getByRole('button', { name: 'Cancel', exact: true }).click()
  expect(state.mutations).toHaveLength(1)
  await page.getByRole('button', { name: 'Model management', exact: true }).click()
  await dialog.getByRole('combobox').click()
  await page.getByRole('option', { name: 'Replacement model', exact: true }).click()
  await dialog.getByRole('button', { name: 'Save', exact: true }).click()
  await expect.poll(() => state.settings.custom_model).toBe('30')
})

test('unavailable default remains visible and requires a replacement or explicit clearing', async ({ page }) => {
  const state = await setup(page)
  state.settings = { enable_custom_model: true, custom_model: '999' }
  await page.goto('/#/system/workspace')
  await page.getByRole('button', { name: 'Model management', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Model management', exact: true })
  await expect(dialog.getByRole('button', { name: 'Save', exact: true })).toBeDisabled()
  await expect(dialog.getByText(/Model deleted or authorization revoked/).first()).toBeVisible()
  await dialog.getByRole('combobox').click()
  await page.getByRole('option', { name: 'Replacement model', exact: true }).click()
  await expect(dialog.getByRole('button', { name: 'Save', exact: true })).toBeEnabled()
})

test('revoking authorization prompts for impact and cancellation sends no mutation', async ({ page }) => {
  const state = await setup(page)
  await page.goto('/#/system/model')
  const card = page.locator('.card').filter({ has: page.getByText('Workspace model', { exact: true }) })
  await card.locator('.type-value .hover-icon_with_bg').click()
  const drawer = page.getByRole('dialog', { name: 'Authorized Space List' })
  await expect(drawer.getByText('Workspace A', { exact: true })).toBeVisible()
  await drawer.locator('.action-btn').click()
  await page.locator('.ed-message-box').getByRole('button', { name: 'Remove', exact: true }).click()
  const impact = page.getByRole('dialog', { name: 'Affected workspaces', exact: true })
  await expect(impact.getByText(/Existing assistant/)).toBeVisible()
  await expect(impact.getByRole('button', { name: 'Confirm', exact: true })).toBeDisabled()
  await impact.getByRole('button', { name: 'Cancel', exact: true }).click()
  expect(state.mutations).toEqual([])
  await drawer.locator('.action-btn').click()
  await page.locator('.ed-message-box').getByRole('button', { name: 'Remove', exact: true }).click()
  await impact.locator('.ed-select__wrapper').click()
  await page.getByRole('option', { name: 'Replacement model', exact: true }).click()
  await impact.getByRole('button', { name: 'Confirm', exact: true }).click()
  await expect.poll(() => state.mutations.length).toBe(1)
  expect(state.mutations[0]).toEqual({ ws_ids: ['1'], resolutions: [{ workspace_id: '1', custom_model: '30' }] })
})

test('deleting a model requires explicit acknowledgement of the unavailable default', async ({ page }) => {
  const state = await setup(page)
  await page.goto('/#/system/model')
  const card = page.locator('.card').filter({ has: page.getByText('Workspace model', { exact: true }) })
  await card.locator('.more').click()
  await card.getByText('Delete', { exact: true }).click()
  await page.locator('.ed-message-box').getByRole('button', { name: 'Delete', exact: true }).click()
  const impact = page.getByRole('dialog', { name: 'Affected workspaces', exact: true })
  await expect(impact.getByRole('button', { name: 'Confirm', exact: true })).toBeDisabled()
  await impact.locator('.ed-select__wrapper').click()
  await page.getByRole('option', { name: 'Keep unavailable default and suspend default calls', exact: true }).click()
  await impact.getByRole('button', { name: 'Confirm', exact: true }).click()
  await expect.poll(() => state.deleted).toBe(true)
  expect(state.mutations).toEqual([[{ workspace_id: '1', custom_model: null }]])
  await expect(card).toHaveCount(0)
})

test('bulk authorization removal also requires an explicit impact resolution', async ({ page }) => {
  const state = await setup(page)
  await page.goto('/#/system/model')
  const card = page.locator('.card').filter({ has: page.getByText('Workspace model', { exact: true }) })
  await card.locator('.type-value .hover-icon_with_bg').click()
  const drawer = page.getByRole('dialog', { name: 'Authorized Space List' })
  await drawer.getByRole('row', { name: 'Workspace A', exact: true }).locator('.ed-checkbox__inner').click()
  await drawer.getByRole('button', { name: 'Remove', exact: true }).click()
  await page.locator('.ed-message-box').getByRole('button', { name: 'Remove', exact: true }).click()
  const impact = page.getByRole('dialog', { name: 'Affected workspaces', exact: true })
  await impact.locator('.ed-select__wrapper').click()
  await page.getByRole('option', { name: 'Keep unavailable default and suspend default calls', exact: true }).click()
  await impact.getByRole('button', { name: 'Confirm', exact: true }).click()
  await expect.poll(() => state.mutations.length).toBe(1)
  expect(state.mutations[0]).toEqual({ ws_ids: ['1'], resolutions: [{ workspace_id: '1', custom_model: null }] })
})
