import { test, expect } from '@playwright/test';

const users = Array.from({ length: 543 }, (_, i) => ({ id: String(i + 2), name: `Member ${i + 2}`, account: `user${i + 2}` }));

async function mockPages(page, { total = 543, failSecond = false } = {}) {
  const calls = [];
  const saves = [];
  await page.route('**/api/system/workspace/uws/option/pager/**', async route => {
    const url = new URL(route.request().url());
    const [current, requestedSize] = url.pathname.split('/').slice(-2).map(Number);
    calls.push([current, requestedSize]);
    expect(url.searchParams.get('oid')).toBe('99');
    if (failSecond && current === 2) return route.fulfill({ status: 500, body: '{}' });
    const size = Math.min(500, requestedSize);
    await route.fulfill({ json: { items: users.slice((current - 1) * size, Math.min(current * size, total)), page: current, size, total, total_pages: Math.ceil(total / size) } });
  });
  await page.route('**/api/system/workspace/uws', async route => {
    saves.push(route.request().postDataJSON());
    await route.fulfill({ json: true });
  });
  return { calls, saves };
}

test('loads all bounded pages and saves a member beyond the first 500', async ({ page }) => {
  const { calls, saves } = await mockPages(page);
  await page.goto('/');
  await page.getByRole('button', { name: 'Open members' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  expect(calls).toEqual([[1, 500], [2, 500]]);
  await dialog.getByRole('textbox').fill('Member 544');
  await dialog.locator('label').filter({ hasText: 'Member 544' }).click();
  await dialog.getByRole('button', { name: '添加', exact: true }).click();
  await expect.poll(() => saves.length).toBe(1);
  expect(saves[0]).toMatchObject({ oid: '99', uid_list: ['544'] });
});

test('empty list stops after the first page', async ({ page }) => {
  const { calls } = await mockPages(page, { total: 0 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Open members' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  expect(calls).toEqual([[1, 500]]);
  await expect(page.getByRole('checkbox')).toHaveCount(0);
});

test('failed later page never exposes a partially loaded selection', async ({ page }) => {
  const { calls } = await mockPages(page, { failSecond: true });
  await page.goto('/');
  await page.getByRole('button', { name: 'Open members' }).click();
  await expect(page.getByRole('status')).toHaveText('load failed');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  expect(calls).toEqual([[1, 500], [2, 500]]);
});
