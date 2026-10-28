import { readFileSync } from 'node:fs'
import { test, expect } from '@playwright/test'

const locales = ['zh-CN', 'zh-TW', 'en', 'ko-KR', 'th-TH']
const messages = Object.fromEntries(locales.map(locale => [locale,
  JSON.parse(readFileSync(new URL(`../../../frontend/src/i18n/${locale}.json`, import.meta.url), 'utf8'))
]))
const text = (locale, key) => key.split('.').reduce((value, part) => value[part], messages[locale])
const titleKey = 'embedded.i_am_sqlbot'
const sloganKey = 'common.intelligent_questioning_platform'

test.beforeEach(async ({ page }) => {
  page.on('pageerror', error => { throw error })
  await page.goto('/')
  await page.waitForFunction(() => window.welcomeFixture)
})

test('login appearance: restore saves default mode and preserves the other section', async ({ page }) => {
  await page.evaluate(() => window.welcomeFixture.editor('appearance', {
    slogan: 'Custom login slogan', showSlogan: '1',
    pc_welcome: 'Keep platform title', pc_welcome_desc: 'Keep platform description'
  }))
  await page.getByRole('button', { name: text('zh-CN', 'system.restore_default'), exact: true }).first().click()
  await page.getByRole('button', { name: text('zh-CN', 'system.save_and_apply'), exact: true }).click()
  await expect.poll(() => page.evaluate(() => window.welcomeFixture.saved.length)).toBe(1)
  const saved = await page.evaluate(() => Object.fromEntries(window.welcomeFixture.saved[0].data.map(row => [row.pkey, row.pval])))
  expect(saved.slogan).toBe('')
  expect(saved.showSlogan).toBe('0')
  expect(saved.pc_welcome).toBe('Keep platform title')
  expect(saved.pc_welcome_desc).toBe('Keep platform description')
  await page.evaluate(() => window.welcomeFixture.reopen())
  const sloganInput = locale => page.getByPlaceholder(text(locale, sloganKey), { exact: true })
  for (const locale of locales) {
    await page.evaluate(locale => window.welcomeFixture.language(locale), locale)
    await expect(sloganInput(locale)).toHaveValue('')
    await expect(page.locator('.login-welcome')).toHaveText(text(locale, sloganKey))
  }
  await sloganInput('th-TH').fill('New custom login slogan')
  await page.getByRole('button', { name: text('th-TH', 'system.save_and_apply'), exact: true }).click()
  await expect.poll(() => page.evaluate(() => window.welcomeFixture.saved.length)).toBe(2)
  const custom = await page.evaluate(() => Object.fromEntries(window.welcomeFixture.saved[1].data.map(row => [row.pkey, row.pval])))
  expect(custom.slogan).toBe('New custom login slogan')
  await page.evaluate(() => window.welcomeFixture.reopen())
  await page.evaluate(() => window.welcomeFixture.language('en'))
  await expect(sloganInput('en')).toHaveValue('New custom login slogan')
  await expect(page.locator('.login-welcome')).toHaveText('New custom login slogan')
  await page.evaluate(config => window.welcomeFixture.render('login', 0, config), custom)
  await expect(page.locator('.welcome')).toHaveText('New custom login slogan')
  await page.evaluate(config => window.welcomeFixture.render('login', 0, config), saved)
  await expect(page.locator('.welcome')).toHaveText(text('en', sloganKey))
})

test('login: defaults follow language and the display switch still hides custom text', async ({ page }) => {
  for (const old of [...locales, undefined, '', null]) {
    const config = { slogan: locales.includes(old) ? text(old, sloganKey) : old, showSlogan: '0' }
    await page.evaluate(config => window.welcomeFixture.render('login', 0, config), config)
    for (const locale of locales) {
      await page.evaluate(locale => window.welcomeFixture.language(locale), locale)
      await expect(page.locator('.welcome')).toHaveText(text(locale, sloganKey))
    }
  }
  const custom = text('zh-CN', sloganKey) + '!'
  await page.evaluate(config => window.welcomeFixture.render('login', 0, config), { slogan: custom, showSlogan: '0' })
  await page.evaluate(() => window.welcomeFixture.language('en'))
  await expect(page.locator('.welcome')).toHaveText(custom)
  await page.evaluate(config => window.welcomeFixture.render('login', 0, config), { slogan: custom, showSlogan: '1' })
  await expect(page.locator('.welcome')).toHaveText('')
})

for (const [kind, type] of [['float', 0], ['float', 1], ['page', 0], ['page', 1], ['page', 4], ['chat', 0]]) {
  test(`${kind}/${type}: missing, empty and legacy defaults follow language; custom text survives`, async ({ page }) => {
    const full = type === 4 || kind === 'chat'
    const title = full ? 'pc_welcome' : 'welcome'
    const description = full ? 'pc_welcome_desc' : 'welcome_desc'
    const descKey = full ? 'qa.hint_description' : 'embedded.data_analysis_now'
    const root = page.locator('.welcome-content')
    for (const old of [...locales, undefined, '']) {
      const config = old === undefined ? {} : {
        [title]: old === '' ? '' : text(old, titleKey),
        [description]: old === '' ? '' : text(old, descKey)
      }
      await page.evaluate(args => window.welcomeFixture.render(...args), [kind, type, config])
      for (const locale of locales) {
        await page.evaluate(locale => window.welcomeFixture.language(locale), locale)
        await expect(root).toContainText(text(locale, titleKey))
        await expect(root).toContainText(text(locale, descKey))
      }
    }
    await page.evaluate(args => window.welcomeFixture.render(...args), [kind, type, {
      [title]: 'Custom welcome', [description]: '我的专属说明'
    }])
    for (const locale of locales) {
      await page.evaluate(locale => window.welcomeFixture.language(locale), locale)
      await expect(root).toContainText('Custom welcome')
      await expect(root).toContainText('我的专属说明')
      await expect(root).toContainText(text(locale, 'qa.start_sqlbot'))
    }
  })
}

for (const kind of ['settings', 'appearance']) {
  test(`${kind}: restore, save, reopen, switch language and edit again`, async ({ page }) => {
    const title = kind === 'settings' ? 'welcome' : 'pc_welcome'
    const description = kind === 'settings' ? 'welcome_desc' : 'pc_welcome_desc'
    await page.evaluate(args => window.welcomeFixture.editor(...args), [kind, {
      [title]: 'Custom title', [description]: 'Custom description'
    }])
    const restore = page.getByRole('button', { name: text('zh-CN', 'system.restore_default'), exact: true })
    await restore.nth(kind === 'settings' ? 0 : 1).click()
    await page.evaluate(() => window.welcomeFixture.language('th-TH'))
    const welcomeInput = locale => page.getByPlaceholder(text(locale, titleKey), { exact: true })
    await expect(welcomeInput('th-TH')).toHaveValue('')
    await page.getByRole('button', { name: text('th-TH', kind === 'settings' ? 'common.save' : 'system.save_and_apply'), exact: true }).click()
    await expect.poll(() => page.evaluate(() => window.welcomeFixture.saved.length)).toBe(1)
    const saved = await page.evaluate(() => window.welcomeFixture.saved[0].data)
    const values = kind === 'settings' ? saved : Object.fromEntries(saved.map(x => [x.pkey, x.pval]))
    expect(values[title]).toBe('')
    expect(values[description]).toBe('')
    await page.evaluate(() => window.welcomeFixture.reopen())
    await page.evaluate(() => window.welcomeFixture.language('en'))
    await expect(welcomeInput('en')).toHaveValue('')
    await welcomeInput('en').fill('Temporary custom text')
    await welcomeInput('en').fill('')
    await expect(welcomeInput('en')).toHaveValue('')
    await welcomeInput('en').fill('Custom after reset')
    await page.getByRole('button', { name: text('en', kind === 'settings' ? 'common.save' : 'system.save_and_apply'), exact: true }).click()
    await expect.poll(() => page.evaluate(() => window.welcomeFixture.saved.length)).toBe(2)
    const again = await page.evaluate(() => window.welcomeFixture.saved[1].data)
    expect(kind === 'settings' ? again[title] : again.find(x => x.pkey === title).pval).toBe('Custom after reset')
    await page.evaluate(() => window.welcomeFixture.reopen())
    await page.evaluate(() => window.welcomeFixture.language('ko-KR'))
    await expect(welcomeInput('ko-KR')).toHaveValue('Custom after reset')
  })
}
