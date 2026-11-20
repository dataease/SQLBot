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

test('账号绑定页面与认证回调不出现在侧边导航', async ({ page }) => {
  await page.goto('/')
  for (const account of [{ id: 41, language: 'zh-CN', weight: 1 }, { id: 1, language: 'zh-CN', weight: 1 }]) {
    await page.evaluate(value => window.menuFixture.signIn(value), account)
    await expect(page.getByRole('menubar').getByText('账号绑定', { exact: true })).toHaveCount(0)
  }
})

for (const id of [1, 41]) test(`用户 ${id} 的个人信息入口位于帮助下面，且不进入侧边导航`, async ({ page }) => {
  await page.goto('/?person=1')
  await page.evaluate(id => window.menuFixture.signIn({ id, language: 'zh-CN', weight: 1 }), id)
  await expect(page.getByRole('menubar').getByText('账号绑定', { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Test', exact: true }).click()
  const labels = await page.locator('.system-person .popover-item .datasource-name').allTextContents()
  const help = labels.indexOf('帮助')
  expect(help).toBeGreaterThanOrEqual(0)
  expect(labels[help + 1]).toBe('个人信息')
  expect(labels[help + 2]).toBe('退出登录')
  expect(labels.indexOf('关于')).toBeLessThan(help)
  await page.locator('.system-person').getByText('个人信息', { exact: true }).click()
  await expect(page).toHaveURL(/#\/account\/bindings$/)
  await expect(page.getByRole('menubar').getByText('账号绑定', { exact: true })).toHaveCount(0)
})

test('当前用户邮箱由真实用户信息动作读取，切换账号和退出后不保留旧邮箱', async ({ page }) => {
  await page.goto('/')
  await page.evaluate(() => window.menuFixture.signIn({ id: 41, language: 'zh-CN', weight: 1, email: 'first@example.invalid' }))
  await expect.poll(() => page.evaluate(() => window.menuFixture.email())).toBe('first@example.invalid')
  await page.evaluate(() => window.menuFixture.signIn({ id: 42, language: 'zh-CN', weight: 1 }))
  await expect.poll(() => page.evaluate(() => window.menuFixture.email())).toBe('')
  await page.evaluate(() => window.menuFixture.signIn({ id: 41, language: 'zh-CN', weight: 1, email: 'first@example.invalid' }))
  await page.evaluate(() => window.menuFixture.signOut())
  await expect.poll(() => page.evaluate(() => window.menuFixture.email())).toBe('')
})


test('第三方账号的个人信息入口仍位于帮助下面', async ({ page }) => {
  await page.goto('/?person=1');
  await page.evaluate(() => window.menuFixture.signIn({ id: 42, language: 'zh-CN', weight: 1, origin: 3 }));
  await page.getByRole('button', { name: 'Test', exact: true }).click();
  const labels = await page.locator('.system-person .popover-item .datasource-name').allTextContents();
  expect(labels[labels.indexOf('帮助') + 1]).toBe('个人信息');
  await page.locator('.system-person').getByText('个人信息', { exact: true }).click();
  await expect(page).toHaveURL(/#\/account\/bindings$/);
});
