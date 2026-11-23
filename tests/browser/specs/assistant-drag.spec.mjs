import { test, expect } from '@playwright/test'
const button = (page) => page.locator('.sqlbot-assistant-chat-button')
const chat = (page) => page.locator('#sqlbot-assistant-chat-container')
async function drag(page, x, y) {
  const box = await button(page).boundingBox()
  await page.mouse.move(box.x + 15, box.y + 15)
  await page.mouse.down()
  await page.mouse.move(x, y, { steps: 20 })
  await page.mouse.up()
}
for (const x of ['left', 'right'])
  for (const y of ['top', 'bottom']) {
    test(`hit area follows icon from ${x}/${y}`, async ({ page }) => {
      await page.goto(`/?x=${x}&y=${y}`)
      const old = await button(page).boundingBox()
      await drag(page, 400, 300)
      await expect(chat(page)).toBeHidden()
      const box = await button(page).boundingBox()
      expect(box.width).toBe(30)
      expect(box.height).toBe(30)
      for (const point of [
        [old.x + 15, old.y + 15],
        [(old.x + box.x) / 2 + 15, (old.y + box.y) / 2 + 15],
      ]) {
        await page.mouse.click(...point)
        await expect(chat(page)).toBeHidden()
      }
      expect(await page.evaluate(() => window.hostClicks)).toBe(2)
      await button(page).click()
      await expect(chat(page)).toBeVisible()
      await page.locator('.sqlbot-assistant-chat-close').click()
      await drag(page, 200, 150)
      await expect(chat(page)).toBeHidden()
      expect((await button(page).boundingBox()).width).toBe(30)
      await button(page).click()
      await expect(chat(page)).toBeVisible()
    })
  }
test('edge clamping and resize keep icon reachable', async ({ page }) => {
  await page.goto('/')
  await drag(page, 0, 0)
  let box = await button(page).boundingBox()
  expect(box.x).toBe(0)
  expect(box.y).toBe(0)
  await drag(page, 999, 699)
  box = await button(page).boundingBox()
  expect(box.x + box.width).toBeLessThanOrEqual(1000)
  expect(box.y + box.height).toBeLessThanOrEqual(700)
  await page.setViewportSize({ width: 600, height: 400 })
  await expect
    .poll(async () => {
      const b = await button(page).boundingBox()
      return b.x + b.width
    })
    .toBeLessThanOrEqual(600)
  await expect
    .poll(async () => {
      const b = await button(page).boundingBox()
      return b.y + b.height
    })
    .toBeLessThanOrEqual(400)
  await button(page).click()
  await expect(chat(page)).toBeVisible()
  await page.setViewportSize({ width: 500, height: 350 })
  await expect
    .poll(() => button(page).evaluate((e) => parseFloat(e.style.left) + 30))
    .toBeLessThanOrEqual(500)
  await page.locator('.sqlbot-assistant-chat-close').click()
  box = await button(page).boundingBox()
  expect(box.x + box.width).toBeLessThanOrEqual(500)
  expect(box.y + box.height).toBeLessThanOrEqual(350)
})
test('small movement remains a click; dragging disabled remains unchanged', async ({
  page,
}) => {
  for (const query of ['', '?drag=false', '?custom=true']) {
    await page.goto('/' + query)
    const b = await button(page).boundingBox()
    await page.mouse.move(b.x + 10, b.y + 10)
    await page.mouse.down()
    await page.mouse.move(b.x + 12, b.y + 12)
    await page.mouse.up()
    await expect(chat(page)).toBeVisible()
    await page.locator('.sqlbot-assistant-chat-close').click()
    if (query.includes('custom')) {
      await drag(page, 200, 150)
      expect((await button(page).boundingBox()).width).toBe(30)
      await expect(chat(page)).toBeHidden()
    }
  }
})
test('touch tap, drag and cancel', async ({ page, context }) => {
  await page.goto('/')
  await button(page).tap()
  await expect(chat(page)).toBeVisible()
  await page.locator('.sqlbot-assistant-chat-close').tap()
  const cdp = await context.newCDPSession(page)
  const b = await button(page).boundingBox()
  await cdp.send('Input.dispatchTouchEvent', {
    type: 'touchStart',
    touchPoints: [{ x: b.x + 15, y: b.y + 15 }],
  })
  await cdp.send('Input.dispatchTouchEvent', {
    type: 'touchMove',
    touchPoints: [{ x: 200, y: 150 }],
  })
  await cdp.send('Input.dispatchTouchEvent', {
    type: 'touchEnd',
    touchPoints: [],
  })
  await expect(chat(page)).toBeHidden()
  expect((await button(page).boundingBox()).width).toBe(30)
  await button(page).tap()
  await expect(chat(page)).toBeVisible()
  await page.locator('.sqlbot-assistant-chat-close').tap()
  await cdp.send('Input.dispatchTouchEvent', {
    type: 'touchStart',
    touchPoints: [{ x: 200, y: 150 }],
  })
  await cdp.send('Input.dispatchTouchEvent', {
    type: 'touchCancel',
    touchPoints: [],
  })
  await expect(chat(page)).toBeHidden()
  await button(page).tap()
  await expect(chat(page)).toBeVisible()
})
