import { readFileSync } from 'node:fs'
import { test, expect } from '@playwright/test'

const locales = ['zh-TW', 'zh-CN', 'en', 'ko-KR', 'th-TH']
const messages = Object.fromEntries(locales.map(locale => [locale,
  JSON.parse(readFileSync(new URL(`../../../frontend/src/i18n/${locale}.json`, import.meta.url), 'utf8'))
]))
const text = (locale, key) => key.split('.').reduce((value, part) => value[part], messages[locale])
const primary = ['menu.Data Q&A', 'dashboard.dashboard', 'menu.Data Connections', 'embedded.assistant_app', 'workspace.set']
const settings = ['workspace.member_management', 'workspace.permission_configuration', 'professional.professional_terminology', 'training.data_training', 'prompt.customize_prompt_words']
const admin = ['user.user_management', 'user.workspace', 'model.ai_model_configuration', 'embedded.embedded_management', 'system.system_settings', 'audit.system_log']
const systemSettings = ['system.appearance_settings', 'parameter.parameter_configuration', 'variables.system_variables', 'system.authentication_settings', 'platform.title']

async function expectLabels(page, locale, keys) {
  for (const key of keys) {
    await expect(page.getByRole('menubar').getByText(text(locale, key), { exact: true }).first()).toBeVisible()
  }
}

for (const locale of locales) {
  test(`切换账号后普通导航和设置子菜单跟随 ${locale}`, async ({ page }) => {
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.goto('/')
    await expectLabels(page, 'en', primary)
    await page.evaluate(() => window.menuFixture.signOut())
    await expect(page.getByRole('menubar')).toHaveCount(0)
    await page.evaluate(language => window.menuFixture.signIn({ id: 42, language, weight: 1 }), locale)
    await expect(page.locator('#language')).toHaveText(locale)
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(text(locale, 'menu.Data Q&A'))
    await expectLabels(page, locale, primary)
    await page.getByText(text(locale, 'workspace.set'), { exact: true }).first().click()
    await expectLabels(page, locale, settings)
    await page.evaluate(() => window.menuFixture.signOut())
    await page.evaluate(() => window.menuFixture.signIn({ id: 41, language: 'en', weight: 1 }))
    await expectLabels(page, 'en', primary)
    expect(errors).toEqual([])
  })

  test(`管理员菜单在不刷新页面时跟随 ${locale}`, async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => window.menuFixture.signOut())
    await page.evaluate(() => window.menuFixture.signIn({ id: 1, language: 'en', weight: 1 }))
    await page.evaluate(() => window.menuFixture.go('/system/user'))
    await expectLabels(page, 'en', admin)
    await page.evaluate(language => window.menuFixture.setLanguage(language), locale)
    await expectLabels(page, locale, admin)
    await page.getByText(text(locale, 'system.system_settings'), { exact: true }).first().click()
    await expectLabels(page, locale, systemSettings)
  })
}

test('普通成员保持动态导航权限，扩展的直接标题保持可见', async ({ page }) => {
  await page.goto('/')
  await page.evaluate(() => window.menuFixture.signOut())
  await page.evaluate(() => window.menuFixture.signIn({ id: 43, language: 'zh-TW', weight: 0 }))
  await expectLabels(page, 'zh-TW', primary.slice(0, 2))
  for (const key of primary.slice(2)) {
    await expect(page.getByRole('menubar').getByText(text('zh-TW', key), { exact: true })).toHaveCount(0)
  }
  await page.evaluate(() => window.menuFixture.go('/extension'))
  await expect(page.getByRole('menuitem', { name: 'Extension title' })).toBeVisible()
  await page.evaluate(() => window.menuFixture.setLanguage('ko-KR'))
  await expect(page.getByRole('menuitem', { name: 'Extension title' })).toBeVisible()
})
