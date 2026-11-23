import { test, expect } from '@playwright/test';

async function setup(page, path = '/', options = {}) {
  await page.context().route('**/api/user/ws', route => route.fulfill({ json: [{ id: '1', name: '示例工作空间' }] }));
  const state = { requests: {}, next: 0, confirms: 0, callbacks: 0, bound: options.bound || false, licensed: options.licensed ?? true, starts: 0, statusCalls: 0, calls: 0, listCalls: 0 };
  await page.context().route('**/api/system/account-bindings**', async route => {
    state.calls++;
    const req = route.request(); const url = new URL(req.url()); const path = url.pathname.replace('/api/system/account-bindings', '');
    const body = req.postDataJSON();
    const ok = json => route.fulfill({ json });
    const bad = message => route.fulfill({ status: 400, json: message });
    if (path === '/capabilities') return ok({ show_bindings: state.licensed || state.bound, can_bind: state.licensed });
    if (!path) {
      state.listCalls++;
      return ok([8,6,7,4,1,2].filter(origin => state.licensed || (origin === 4 && state.bound)).map(origin => ({ origin, enabled: state.licensed && origin !== 2, bound: origin === 4 && state.bound, account: state.bound ? 'provider-account' : '', display_name: 'Provider User' })));
    }
    if (path === '/requests') {
      state.starts++;
      if (body.pwd !== 'Synthetic42!') return bad('本地密码不正确。');
      const id = 'sqlbot_bind_' + String(++state.next).padStart(43, 'x');
      state.requests[id] = { status: 'pending', origin: body.origin };
      return ok({ origin: body.origin, state: id, expires_at: Math.floor(Date.now()/1000) + 300,
        url: `${url.origin}/provider?state=${id}`, callback_url: url.origin + '/', client: { client_id: 'synthetic', corpid: 'synthetic', agent_id: 'synthetic' } });
    }
    if (path === '/callback') {
      state.callbacks++;
      state.requests[body.state].status = 'verified';
      return ok({ status: 'verified' });
    }
    if (path.endsWith('/refresh')) {
      const old = path.split('/')[2]; state.requests[old].status = 'cancelled';
      const id = 'sqlbot_bind_' + String(++state.next).padStart(43, 'x');
      state.requests[id] = { status: 'pending', origin: state.requests[old].origin };
      return ok({origin: state.requests[id].origin, state:id, expires_at:Math.floor(Date.now()/1000)+300,
        url:`${url.origin}/provider?state=${id}`,callback_url:url.origin+'/',client:{client_id:'synthetic'}});
    }
    if (path.endsWith('/confirm')) {
      const id = path.split('/')[2];
      if (state.requests[id].status !== 'verified') return bad('尚未认证');
      state.confirms++; state.bound = true; state.requests[id].status = 'confirmed'; return ok({ status: 'confirmed' });
    }
    if (path.endsWith('/unbind')) {
      if (body.pwd !== 'Synthetic42!') return bad('本地密码不正确。');
      state.bound = false; return ok(null);
    }
    const id = path.split('/')[2];
    if (req.method() === 'DELETE') { if (state.requests[id].status !== 'confirmed') state.requests[id].status = 'cancelled'; return ok(null); }
    state.statusCalls++;
    return ok({ status: state.requests[id].status, account: 'provider-account', display_name: 'Provider User' });
  });
  await page.context().route('**/provider?*', async route => {
    const state = new URL(route.request().url()).searchParams.get('state');
    if (new URL(route.request().url()).searchParams.has('tmp_code')) return route.fulfill({contentType:'text/html',body:`<script>location.href='/?state=${state}&code=synthetic-code'</script>`});
    await route.fulfill({ contentType: 'text/html', body: `<button onclick="location.href='/?state=${state}&code=synthetic-code'">Complete provider authentication</button>` });
  });
  await page.goto(path);
  return state;
}
const row = (page, name) => page.locator('.binding-row').filter({ has: page.getByRole('heading', { name, exact: true }) });
async function begin(page, name='OAuth2') {
  await row(page,name).getByRole('button', { name: '绑定', exact:true }).click();
  await page.getByRole('dialog').getByLabel('登录密码').fill('Synthetic42!');
  await page.getByRole('button', { name:'下一步',exact:true }).click();
}

test('new window authenticates, notifies and closes; only explicit confirmation writes the link', async ({page}) => {
  const state = await setup(page);
  await begin(page);
  const opened = page.waitForEvent('popup');
  await page.getByRole('button', {name:'前往认证',exact:true}).click();
  const popup = await opened;
  await popup.getByRole('button', {name:'Complete provider authentication'}).click();
  await expect.poll(() => popup.isClosed()).toBe(true);
  await expect(page.getByRole('dialog')).toContainText('provider-account');
  expect(state.confirms).toBe(0);
  await page.getByRole('button', {name:'确认绑定',exact:true}).click();
  await expect(row(page,'OAuth2')).toContainText('已绑定');
  expect(state.confirms).toBe(1);
  await row(page,'OAuth2').getByRole('button', {name:'解除绑定',exact:true}).click();
  await page.getByRole('dialog').getByLabel('登录密码').fill('wrong');
  await page.getByRole('button', {name:'确认解除',exact:true}).click();
  await expect(page.getByRole('dialog')).toContainText('本地密码不正确');
  await page.getByRole('dialog').getByLabel('登录密码').fill('Synthetic42!');
  await page.getByRole('button', {name:'确认解除',exact:true}).click();
  await expect(row(page,'OAuth2')).toContainText('未绑定');
});

test('wrong local password, popup blocked, forged message and cancellation', async ({page}) => {
  const state = await setup(page);
  await row(page,'OAuth2').getByRole('button', {name:'绑定',exact:true}).click();
  await page.getByRole('dialog').getByLabel('登录密码').fill('wrong');
  await page.getByRole('button', {name:'下一步',exact:true}).click();
  await expect(page.getByRole('dialog')).toContainText('本地密码不正确');
  expect(state.callbacks).toBe(0);
  await page.getByRole('dialog').getByLabel('登录密码').fill('Synthetic42!');
  await page.getByRole('button', {name:'下一步',exact:true}).click();
  await page.evaluate(() => { window.open = () => null; });
  await page.getByRole('button', {name:'前往认证',exact:true}).click();
  await expect(page.getByRole('dialog')).toContainText('被浏览器拦截');
  const id = Object.keys(state.requests)[0];
  await page.evaluate(state => window.postMessage({type:'sqlbot-binding-updated',state},location.origin), id);
  await expect(page.getByRole('dialog')).not.toContainText('provider-account');
  await page.getByRole('dialog').getByRole('button',{name:'取消',exact:true}).click();
  await expect.poll(() => state.requests[id].status).toBe('cancelled');
  expect(state.confirms).toBe(0);
});

for (const [name, url, script] of [
 ['企业微信','**/wecom-jssdk-2.3.3.js', `window.ww={createWWLoginPanel(o){const b=document.createElement('button');b.textContent='Synthetic scan';b.onclick=()=>o.onLoginSuccess({code:'synthetic'});document.querySelector(o.el).append(b);return {unmount(){b.remove()}}}}`],
 ['钉钉','**/ddlogin.js', `window.DTFrameLogin=(target,params,ok)=>{const b=document.createElement('button');b.textContent='Synthetic scan';b.onclick=()=>ok({authCode:'synthetic'});document.getElementById(target.id).append(b)}`],
]) test(`${name} QR verifies identity without navigating or signing in`, async ({page}) => {
  const state = await setup(page);
  await page.route(url, route=>route.fulfill({contentType:'application/javascript',body:script}));
  await begin(page,name);
  await page.getByRole('button',{name:'Synthetic scan'}).click();
  await expect(page.getByRole('dialog')).toContainText('provider-account');
  await expect(page).toHaveURL('/');
  expect(state.confirms).toBe(0);
  await page.getByRole('button',{name:'确认绑定',exact:true}).click();
  expect(state.confirms).toBe(1);
});

test('Feishu QR callback remains in a separate frame and refresh invalidates the old request', async ({page}) => {
  const state = await setup(page);
  await page.route('**/LarkSSOSDKWebQRCode-1.0.3.js', route => route.fulfill({contentType:'application/javascript',body:`window.QRLogin=o=>{const frame=document.createElement('iframe');frame.src='/qr-source';document.getElementById(o.id).append(frame);return {matchOrigin:origin=>origin===location.origin,matchData:d=>typeof d.tmp_code==='string'}}`}));
  await page.route('**/qr-source', route => route.fulfill({contentType:'text/html',body:`<button onclick="parent.postMessage({tmp_code:'synthetic-tmp'},location.origin)">Synthetic scan</button>`}));
  await begin(page, '飞书');
  const old = Object.keys(state.requests)[0];
  await page.getByRole('button',{name:'刷新二维码',exact:true}).click();
  await expect.poll(()=>state.next).toBe(2);
  expect(state.requests[old].status).toBe('cancelled');
  await page.frameLocator('.binding-qr iframe').getByRole('button',{name:'Synthetic scan'}).click();
  await expect(page.getByRole('dialog')).toContainText('provider-account');
  await expect(page).toHaveURL('/');
  expect(state.confirms).toBe(0);
});

test('server status polling works when the provider severs opener', async ({page}) => {
  const state = await setup(page); await begin(page);
  const opened = page.waitForEvent('popup'); await page.getByRole('button',{name:'前往认证',exact:true}).click();
  const popup = await opened; await popup.evaluate(()=>{window.opener=null});
  await popup.getByRole('button',{name:'Complete provider authentication'}).click();
  await expect(page.getByRole('dialog')).toContainText('provider-account');
  expect(state.confirms).toBe(0);
});

test('personal tabs show the selected content and disabled providers cannot be bound',async({page})=>{
  await setup(page);
  await expect(page.getByRole('tab',{name:'账号绑定',exact:true})).toHaveAttribute('aria-selected','true');
  await expect(row(page,'OIDC').getByRole('button',{name:'绑定',exact:true})).toBeDisabled();
  await page.getByRole('tab',{name:'基本信息',exact:true}).click();
  await expect(page.getByRole('heading',{name:'第三方账号',exact:true})).toHaveCount(0);
  await page.getByRole('tab',{name:'账号绑定',exact:true}).click();
  await expect(page.getByRole('heading',{name:'第三方账号',exact:true})).toBeVisible();
});

test('基本信息完整显示姓名、账号、邮箱和真实账号类型', async ({ page }) => {
  await setup(page);
  await page.getByRole('tab', { name: '基本信息', exact: true }).click();
  const details = page.getByRole('region', { name: '账号信息', exact: true });
  await expect(details.locator('dt')).toHaveText(['用户姓名', '账号', '邮箱', '账号类型']);
  await expect(details.locator('dd')).toHaveText(['林晓', 'lin.xiao', 'lin.xiao@example.com', '本地账号']);
  await page.evaluate(() => { window.bindingFixture.user.getEmail = ''; window.bindingFixture.user.getOrigin = 4; });
  await expect(details.locator('dd').nth(2)).toHaveText('—');
  await expect(details.locator('dd').nth(3)).toHaveText('OAuth2');
  await expect(page.locator('.account-tag')).toHaveText('OAuth2');
});


test('内置管理员可以看到已启用钉钉和飞书的绑定入口', async ({ page }) => {
  await setup(page, '/?role=admin');
  await expect(row(page, '钉钉').getByRole('button', { name: '绑定', exact: true })).toBeEnabled();
  await expect(row(page, '飞书').getByRole('button', { name: '绑定', exact: true })).toBeEnabled();
  await begin(page, '钉钉');
  await expect(page.getByRole('dialog')).toContainText('绑定');
});


test('二维码不会在前端自行设定的两分钟后失效，真实超时才结束认证', async ({ page }) => {
  const state = await setup(page);
  await page.clock.install();
  await page.route('**/ddlogin.js', route => route.fulfill({ contentType: 'application/javascript', body: `window.DTFrameLogin=(target,params,ok)=>{const b=document.createElement('button');b.textContent='Synthetic scan';b.onclick=()=>ok({authCode:'synthetic'});document.getElementById(target.id).append(b)}` }));
  await begin(page, '钉钉');
  const id = Object.keys(state.requests)[0];
  await expect(page.getByRole('dialog')).not.toContainText(/\d+s/);
  await page.clock.fastForward(121000);
  await expect(page.getByRole('button', { name: 'Synthetic scan' })).toBeVisible();
  await page.clock.fastForward(180000);
  await expect(page.getByRole('dialog')).toContainText('本次身份验证已超时，请重新验证本地密码');
  await expect(page.getByRole('button', { name: 'Synthetic scan' })).toHaveCount(0);
  await expect.poll(() => state.requests[id].status).toBe('cancelled');
  state.requests[id].status = 'verified';
  const calls = state.statusCalls;
  await page.clock.fastForward(10000);
  expect(state.statusCalls).toBe(calls);
  expect(state.confirms).toBe(0);
  await expect(page.getByRole('dialog')).not.toContainText('provider-account');
  await page.getByRole('button', { name: '重试', exact: true }).click();
  await expect(page.getByRole('dialog').getByLabel('登录密码')).toBeVisible();
});

test('二维码加载失败时保持展示区域并允许刷新恢复', async ({ page }) => {
  const state = await setup(page);
  await page.route('**/ddlogin.js', route => route.abort());
  await begin(page, '钉钉');
  await expect(page.locator('.qr-overlay')).toContainText('二维码加载失败');
  const before = await page.locator('.qr-stage').boundingBox();
  await page.getByRole('dialog').screenshot({ path: 'output/qr-loading-error.png' });
  await page.route('**/ddlogin.js', route => route.fulfill({ contentType: 'application/javascript', body: `window.DTFrameLogin=(target)=>{document.getElementById(target.id).textContent='Synthetic QR'}` }));
  await page.getByRole('button', { name: '刷新二维码', exact: true }).click();
  await expect(page.locator('.qr-stage')).toContainText('Synthetic QR');
  await expect(page.locator('.qr-overlay')).toHaveCount(0);
  const after = await page.locator('.qr-stage').boundingBox();
  expect(after.height).toBe(before.height);
  expect(state.next).toBe(2);
});


test('验证期间禁止重复操作，超时后忽略迟到的认证响应', async ({ page }) => {
  const state = await setup(page);
  await page.clock.install();
  await page.route('**/ddlogin.js', route => route.fulfill({ contentType: 'application/javascript', body: `window.DTFrameLogin=(target,params,ok)=>{const b=document.createElement('button');b.textContent='Synthetic scan';b.onclick=()=>ok({authCode:'synthetic'});document.getElementById(target.id).append(b)}` }));
  let release;
  const hold = new Promise(resolve => { release = resolve; });
  await page.route('**/api/system/account-bindings/callback', async route => {
    const id = route.request().postDataJSON().state;
    state.requests[id].status = 'exchanging';
    await hold;
    await route.fulfill({ json: { status: 'verified' } });
  });
  await begin(page, '钉钉');
  await page.getByRole('button', { name: 'Synthetic scan' }).click();
  await expect(page.locator('.qr-overlay')).toContainText('正在验证账号');
  await expect(page.getByRole('button', { name: '刷新二维码', exact: true })).toBeDisabled();
  await page.getByRole('dialog').screenshot({ path: 'output/qr-verifying.png' });
  await page.clock.fastForward(301000);
  await expect(page.locator('.qr-overlay')).toContainText('本次身份验证已超时');
  release();
  await page.clock.fastForward(5000);
  await expect(page.getByRole('dialog')).not.toContainText('provider-account');
  expect(state.confirms).toBe(0);
  await page.getByRole('dialog').screenshot({ path: 'output/qr-timeout.png' });
});


for (const [origin, type] of [[1, 'CAS'], [2, 'OIDC'], [3, 'LDAP'], [4, 'OAuth2'], [5, 'SAML2'], [6, '企业微信'], [7, '钉钉'], [8, '飞书'], [9, '国际飞书']]) {
  test(`${type} 账号只能查看基本信息，直接进入绑定地址也不请求绑定接口`, async ({ page }) => {
    const state = await setup(page, `/?origin=${origin}`);
    await expect(page.getByRole('tab', { name: '基本信息', exact: true })).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByRole('tab', { name: '账号绑定', exact: true })).toHaveCount(0);
    const details = page.getByRole('region', { name: '账号信息', exact: true });
    await expect(details.locator('dd')).toHaveText(['林晓', 'lin.xiao', 'lin.xiao@example.com', type]);
    await expect(page.locator('.binding-row')).toHaveCount(0);
    await expect(page.getByRole('heading', { name: '第三方账号', exact: true })).toHaveCount(0);
    expect(state.calls).toBe(0);
  });
}


test('开源版只显示基本信息，不读取商业平台列表', async ({ page }) => {
  const state = await setup(page, '/', { licensed: false });
  await expect(page.getByRole('tab', { name: '基本信息', exact: true })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('tab', { name: '账号绑定', exact: true })).toHaveCount(0);
  await expect(page.getByRole('region', { name: '账号信息', exact: true })).toContainText('lin.xiao@example.com');
  await expect(page.locator('.binding-row')).toHaveCount(0);
  await expect(page.getByRole('alert')).toHaveCount(0);
  expect(state.listCalls).toBe(0);
});

test('许可证失效后仅管理历史绑定，解绑最后一项后回到基本信息', async ({ page }) => {
  const state = await setup(page, '/', { licensed: false, bound: true });
  await expect(row(page, 'OAuth2')).toContainText('已绑定');
  await expect(page.locator('.binding-row')).toHaveCount(1);
  await expect(page.getByRole('button', { name: '绑定', exact: true })).toHaveCount(0);
  await expect(page.getByRole('tab', { name: '账号绑定', exact: true })).toBeVisible();
  await row(page, 'OAuth2').getByRole('button', { name: '解除绑定', exact: true }).click();
  await page.getByRole('dialog').getByLabel('登录密码').fill('Synthetic42!');
  await page.getByRole('button', { name: '确认解除', exact: true }).click();
  await expect(page.getByRole('tab', { name: '账号绑定', exact: true })).toHaveCount(0);
  await expect(page.getByRole('tab', { name: '基本信息', exact: true })).toHaveAttribute('aria-selected', 'true');
  expect(state.starts).toBe(0);
  expect(state.bound).toBe(false);
});

// Operation errors must end with their dialog, while independent load errors remain actionable.
const conflictText = '该平台身份已关联其他 SQLBot 用户，或当前账号已绑定其他身份。';
async function conflict(page, state) {
  await page.route('**/LarkSSOSDKWebQRCode-1.0.3.js', route => route.fulfill({
    contentType: 'application/javascript',
    body: 'window.QRLogin=()=>({matchOrigin:()=>false,matchData:()=>false})',
  }));
  await begin(page, '飞书');
  state.requests[Object.keys(state.requests).at(-1)].status = 'conflict';
  await expect(page.getByRole('dialog')).toContainText(conflictText);
}
for (const close of ['cancel', 'cross', 'escape']) test(`operation error lifecycle: Feishu conflict cleared on ${close} and tab switch`, async ({ page }) => {
  const state = await setup(page);
  await conflict(page, state);
  const id = Object.keys(state.requests)[0];
  if (close === 'cancel') await page.getByRole('dialog').getByRole('button', { name: '取消', exact: true }).click();
  if (close === 'cross') await page.getByRole('dialog').getByRole('button', { name: 'Close this dialog' }).click();
  if (close === 'escape') await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.locator('.account-content')).not.toContainText(conflictText);
  await expect.poll(() => state.requests[id].status).toBe('cancelled');
  await page.getByRole('tab', { name: '基本信息', exact: true }).click();
  await expect(page.locator('.account-content')).not.toContainText(conflictText);
  await page.getByRole('tab', { name: '账号绑定', exact: true }).click();
  await conflict(page, state);
  await page.getByRole('button', { name: '重试', exact: true }).click();
  await expect(page.getByRole('dialog').getByLabel('登录密码')).toBeVisible();
  await expect(page.getByRole('dialog')).not.toContainText(conflictText);
  await page.getByRole('dialog').getByLabel('登录密码').fill('Synthetic42!');
  await page.getByRole('button', { name: '下一步', exact: true }).click();
  state.requests[Object.keys(state.requests).at(-1)].status = 'verified';
  await page.getByRole('button', { name: '确认绑定', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.locator('.account-content')).not.toContainText(conflictText);
  await expect(page.locator('.ed-message')).toContainText('绑定成功');
  expect(state.confirms).toBe(1);
});

test('operation error lifecycle: list error survives dialog close but is scoped to bindings', async ({ page }) => {
  const state = await setup(page);
  await page.route('**/api/system/account-bindings', route => route.fulfill({ status: 503, json: '绑定列表暂不可用' }));
  await begin(page);
  state.requests[Object.keys(state.requests)[0]].status = 'verified';
  await page.getByRole('button', { name: '确认绑定', exact: true }).click();
  await expect(page.locator('.account-content')).toContainText('绑定列表暂不可用');
  await row(page, '飞书').getByRole('button', { name: '绑定', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '取消', exact: true }).click();
  await expect(page.locator('.account-content')).toContainText('绑定列表暂不可用');
  await expect(page.locator('.ed-message')).toContainText('绑定成功');
  await page.getByRole('tab', { name: '基本信息', exact: true }).click();
  await expect(page.locator('.account-content')).not.toContainText('绑定列表暂不可用');
  await page.getByRole('tab', { name: '账号绑定', exact: true }).click();
  await expect(page.locator('.account-content')).toContainText('绑定列表暂不可用');
});

for (const operation of ['confirm', 'unbind']) test(`operation error lifecycle: late ${operation} failure cannot affect a new dialog or basic info`, async ({ page }) => {
  const state = await setup(page, '/', { bound: operation === 'unbind' });
  let release, started;
  const held = new Promise(resolve => { release = resolve; });
  const received = new Promise(resolve => { started = resolve; });
  await page.route(`**/api/system/account-bindings/**/${operation}`, async route => {
    started();
    await held;
    await route.fulfill({ status: 400, json: '旧操作的失败提示' });
  });
  if (operation === 'confirm') {
    await begin(page);
    state.requests[Object.keys(state.requests)[0]].status = 'verified';
    await page.getByRole('button', { name: '确认绑定', exact: true }).click();
  } else {
    await row(page, 'OAuth2').getByRole('button', { name: '解除绑定', exact: true }).click();
    await page.getByRole('dialog').getByLabel('登录密码').fill('Synthetic42!');
    await page.getByRole('button', { name: '确认解除', exact: true }).click();
  }
  await received;
  // The modal blocks pointer navigation. Exercise the real tab handler for a programmatic switch.
  await page.getByRole('tab', { name: '基本信息', exact: true }).evaluate(el => el.click());
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('tab', { name: '账号绑定', exact: true }).click();
  await row(page, '飞书').getByRole('button', { name: '绑定', exact: true }).click();
  const response = page.waitForResponse(response => response.url().endsWith(`/${operation}`));
  release();
  await response;
  await expect(page.getByRole('dialog').getByLabel('登录密码')).toBeVisible();
  await expect(page.getByRole('dialog')).not.toContainText('旧操作的失败提示');
  await page.getByRole('dialog').getByRole('button', { name: '取消', exact: true }).click();
  await page.getByRole('tab', { name: '基本信息', exact: true }).click();
  await expect(page.locator('.account-content')).not.toContainText('旧操作的失败提示');
});

for (const endpoint of ['capabilities', '']) test(`operation error lifecycle: initial ${endpoint || 'list'} failure stays visible as a load error`, async ({ page }) => {
  await setup(page);
  await page.route(`**/api/system/account-bindings${endpoint ? '/' + endpoint : ''}`, route => route.fulfill({ status: 503, json: '绑定服务暂不可用' }));
  await page.reload();
  await expect(page.locator('.account-content')).toContainText('绑定服务暂不可用');
  if (!endpoint) {
    await page.getByRole('tab', { name: '基本信息', exact: true }).click();
    await expect(page.locator('.account-content')).not.toContainText('绑定服务暂不可用');
    await page.getByRole('tab', { name: '账号绑定', exact: true }).click();
    await expect(page.locator('.account-content')).toContainText('绑定服务暂不可用');
  }
});

test('operation error lifecycle: late password request does not unlock the next operation', async ({ page }) => {
  await setup(page);
  let releaseFirst, releaseSecond, receivedFirst, receivedSecond;
  const first = new Promise(resolve => { releaseFirst = resolve; });
  const second = new Promise(resolve => { releaseSecond = resolve; });
  const startedFirst = new Promise(resolve => { receivedFirst = resolve; });
  const startedSecond = new Promise(resolve => { receivedSecond = resolve; });
  let starts = 0;
  await page.route('**/api/system/account-bindings/requests', async route => {
    const current = ++starts;
    if (current === 1) { receivedFirst(); await first; }
    else { receivedSecond(); await second; }
    await route.fulfill({ status: 400, json: current === 1 ? '旧请求失败' : '当前请求失败' });
  });
  await begin(page, '飞书');
  await startedFirst;
  await page.getByRole('tab', { name: '基本信息', exact: true }).evaluate(el => el.click());
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('tab', { name: '账号绑定', exact: true }).click();
  await begin(page, '飞书');
  await startedSecond;
  const oldResponse = page.waitForResponse(response => response.url().endsWith('/requests'));
  releaseFirst();
  await oldResponse;
  await expect(page.getByRole('dialog')).not.toContainText('旧请求失败');
  await expect(page.getByRole('dialog').getByRole('button', { name: '取消', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: '下一步', exact: true })).toHaveClass(/is-loading/);
  releaseSecond();
  await expect(page.getByRole('dialog')).toContainText('当前请求失败');
  await page.getByRole('dialog').getByRole('button', { name: '取消', exact: true }).click();
  await expect(page.locator('.account-content')).not.toContainText('当前请求失败');
});

for (const leave of ['tab', 'unmount']) test(`operation error lifecycle: late confirmation success after ${leave} does not close another dialog or show a notification`, async ({ page }) => {
  const state = await setup(page);
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  let release, started;
  const held = new Promise(resolve => { release = resolve; });
  const received = new Promise(resolve => { started = resolve; });
  await page.route('**/api/system/account-bindings/requests/*/confirm', async route => {
    started();
    await held;
    await route.fulfill({ json: { status: 'confirmed' } });
  });
  await begin(page);
  state.requests[Object.keys(state.requests)[0]].status = 'verified';
  await page.getByRole('button', { name: '确认绑定', exact: true }).click();
  await received;
  if (leave === 'unmount') await page.evaluate(() => window.bindingFixture.unmount());
  else {
    await page.getByRole('tab', { name: '基本信息', exact: true }).evaluate(el => el.click());
    await expect(page.getByRole('dialog')).not.toBeVisible();
    await page.getByRole('tab', { name: '账号绑定', exact: true }).click();
    await row(page, '飞书').getByRole('button', { name: '绑定', exact: true }).click();
  }
  const response = page.waitForResponse(response => response.url().endsWith('/confirm'));
  release();
  await (await response).finished();
  // Give the component's promise handler a turn before checking absent side effects.
  await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 0)));
  await expect(page.locator('.ed-message')).toHaveCount(0);
  expect(pageErrors).toEqual([]);
  if (leave === 'tab') await expect(page.getByRole('dialog').getByLabel('登录密码')).toBeVisible();
  else {
    await expect(page.locator('#app')).toBeEmpty();
    await expect(page.getByRole('dialog')).toHaveCount(0);
  }
});

test('operation error lifecycle: retry is immediate even while server cancellation is pending', async ({ page }) => {
  const state = await setup(page);
  let release;
  const held = new Promise(resolve => { release = resolve; });
  await page.route('**/api/system/account-bindings/requests/*', async route => {
    if (route.request().method() !== 'DELETE') return route.fallback();
    await held;
    return route.fulfill({ json: null });
  });
  await conflict(page, state);
  await page.getByRole('button', { name: '重试', exact: true }).click();
  await expect(page.getByRole('dialog').getByLabel('登录密码')).toBeVisible();
  await expect(page.getByRole('dialog')).not.toContainText(conflictText);
  await page.getByRole('dialog').getByRole('button', { name: '取消', exact: true }).click();
  await page.getByRole('tab', { name: '基本信息', exact: true }).click();
  release();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.locator('.account-content')).not.toContainText(conflictText);
});
