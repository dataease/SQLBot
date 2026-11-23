import { test, expect } from '@playwright/test';

const api = `http://127.0.0.1:${process.env.SQLBOT_BINDING_BACKEND_PORT || 4268}`;
const row = page => page.locator('.binding-row').filter({ has: page.getByRole('heading', { name: '飞书', exact: true }) });
const password = 'SyntheticLink42!';

async function setup(page, request) {
  expect((await request.post(`${api}/__test/reset`)).ok()).toBe(true);
  await page.route('**/api/user/ws', route => route.fulfill({ json: [{ id: '1', name: 'Synthetic' }] }));
  await page.route('**/LarkSSOSDKWebQRCode-1.0.3.js', route => route.fulfill({ contentType: 'application/javascript', body: `window.QRLogin=o=>{const f=document.createElement('iframe');f.src='/synthetic-qr';document.getElementById(o.id).append(f);return {matchOrigin:origin=>origin===location.origin,matchData:d=>typeof d.tmp_code==='string'}}` }));
  await page.route('**/synthetic-qr', route => route.fulfill({ contentType: 'text/html', body: `<button onclick="parent.postMessage({tmp_code:'synthetic'},location.origin)">Synthetic scan</button>` }));
  await page.route('**/provider?**', route => {
    const state = new URL(route.request().url()).searchParams.get('state');
    return route.fulfill({ contentType: 'text/html', body: `<script>location.href='/?state=${encodeURIComponent(state)}&code=synthetic-code'</script>` });
  });
  await page.goto('/');
  await expect(row(page).getByRole('button', { name: '绑定', exact: true })).toBeVisible();
}

async function begin(page) {
  await row(page).getByRole('button', { name: '绑定', exact: true }).click();
  await page.getByRole('dialog').getByLabel('登录密码').fill(password);
  const response = page.waitForResponse(r => r.url().endsWith('/requests') && r.request().method() === 'POST');
  await page.getByRole('button', { name: '下一步', exact: true }).click();
  expect((await response).status()).toBe(200);
}

async function refresh(page, count) {
  for (let i = 0; i < count; i++) {
    const response = page.waitForResponse(r => r.url().endsWith('/refresh'));
    await page.getByRole('button', { name: '刷新二维码', exact: true }).click();
    expect((await response).status()).toBe(200);
  }
}

test('twenty QR refreshes permit binding then password-verified unbinding', async ({ page, request }) => {
  await setup(page, request);
  const passwordCalls = [];
  page.on('request', r => {
    if (r.method() === 'POST' && (/\/requests$/.test(r.url()) || /\/unbind$/.test(r.url()))) passwordCalls.push(r.url());
  });
  await begin(page);
  await refresh(page, 20);
  await page.frameLocator('.binding-qr iframe').getByRole('button', { name: 'Synthetic scan' }).click();
  await expect(page.getByRole('dialog')).toContainText('different-provider-id');
  await page.getByRole('button', { name: '确认绑定', exact: true }).click();
  await expect(row(page)).toContainText('已绑定');
  await row(page).getByRole('button', { name: '解除绑定', exact: true }).click();
  await page.getByRole('dialog').getByLabel('登录密码').fill(password);
  const response = page.waitForResponse(r => r.url().endsWith('/8/unbind'));
  await page.getByRole('button', { name: '确认解除', exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect(row(page).getByRole('button', { name: '绑定', exact: true })).toBeVisible();
  expect(passwordCalls).toHaveLength(2);
  expect(await (await request.get(`${api}/__test/evidence`)).json()).toEqual({ password_attempts: 2, links: 0 });
});

test('refresh and cancel preserve the ten-password-attempt limit and show its error', async ({ page, request }) => {
  await setup(page, request);
  await begin(page);
  await refresh(page, 20);
  await page.getByRole('button', { name: '取消', exact: true }).click();
  await row(page).getByRole('button', { name: '绑定', exact: true }).click();
  await page.getByRole('dialog').getByLabel('登录密码').fill('WrongSynthetic!');
  for (let i = 0; i < 10; i++) {
    const response = page.waitForResponse(r => r.url().endsWith('/requests') && r.request().method() === 'POST');
    await page.getByRole('button', { name: '下一步', exact: true }).click();
    expect((await response).status()).toBe(i === 9 ? 429 : 400);
  }
  await expect(page.getByRole('dialog')).toContainText('操作过于频繁，请稍后重试。');
  expect(await (await request.get(`${api}/__test/evidence`)).json()).toEqual({ password_attempts: 10, links: 0 });
});
