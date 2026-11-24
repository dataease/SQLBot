import { expect, test } from '@playwright/test'

test('embedded streamed questions use the host language and preserve the browser fallback', async ({ page, context }) => {
  await context.route('**/xpack_static/license-generator.umd.js*', route => route.fulfill({
    contentType: 'application/javascript',
    body: 'window.LicenseGenerator = { init: async () => {}, generateRouters() {}, getLicense: () => ({}) }',
  }))
  await context.route('**/api/v1/**', route => route.fulfill({ json: { code: 0, data: [] } }))

  async function openAssistant(target, query = '') {
    await target.goto('/#/assistant?id=locale' + query)
    await expect(target.locator('.sqlbot-assistant-container')).toBeVisible({ timeout: 45_000 })
  }

  async function questionLanguage() {
    const [req] = await Promise.all([
      page.waitForRequest(request => request.url().endsWith('/chat/question')),
      page.evaluate(async () => {
        const { questionApi } = await import('/src/api/chat.ts')
        await questionApi.add({ question: 'test', chat_id: 1 })
      }),
    ])
    return req.headerValue('accept-language')
  }

  await openAssistant(page)
  expect(await questionLanguage()).toMatch(/^en-US\b/i)
  await page.goto('about:blank')
  await openAssistant(page, '&lang=zh-TW')
  expect(await questionLanguage()).toBe('zh-TW')
  await page.evaluate(() => window.postMessage({
    eventName: 'sqlbot_assistant_event', messageId: 'locale', busi: 'setLang', lang: 'ko-KR',
  }, window.location.origin))
  await expect.poll(questionLanguage).toBe('ko-KR')

  // Another embedding on the same origin shares storage, but has its own UI language.
  const other = await context.newPage()
  await openAssistant(other, '&lang=th-TH')
  expect(await questionLanguage()).toBe('ko-KR')
})
