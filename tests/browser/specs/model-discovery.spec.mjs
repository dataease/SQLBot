import { test, expect } from "@playwright/test";
const fetchButton = (page) =>
  page.getByRole("button", {
    name: /获取模型列表|重新获取|获取中/,
    exact: false,
  });
const domain = (page) =>
  page.getByPlaceholder("请输入API 域名", { exact: true });
const key = (page) => page.getByPlaceholder("请输入API Key", { exact: true });
const model = (page) => page.locator(".ed-select,.el-select").nth(1);
test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New generic", exact: true }).click();
});
test("fetch without key, deduplicate, search, preserve address, and save manual model", async ({
  page,
}) => {
  await expect(domain(page)).toBeVisible();
  await expect(key(page)).toBeVisible();
  await page.route("**/api/system/aimodel/models", async (route) => {
    expect(route.request().postDataJSON().api_key).toBe("");
    await route.fulfill({
      json: { models: ["demo-chat", "demo-chat", "demo-code"] },
    });
  });
  await domain(page).fill("http://127.0.0.1:4232/v1");
  await fetchButton(page).click();
  await expect(page.getByRole("status")).toContainText("2 个模型");
  await model(page).click();
  await expect(
    page.getByRole("option", { name: "demo-chat", exact: true }),
  ).toHaveCount(1);
  await expect(
    page.getByRole("option").locator(".model-option-name"),
  ).toHaveText(["demo-chat", "demo-code"]);
  await page.getByRole("option", { name: "demo-chat", exact: true }).click();
  await expect(domain(page)).toHaveValue("http://127.0.0.1:4232/v1");
  await model(page).locator("input").fill("manual-model");
  await page.getByRole("option", { name: "manual-model", exact: true }).click();
  await model(page).click();
  await expect(
    page
      .getByRole("option", { name: "manual-model", exact: true })
      .locator(".model-option-source"),
  ).toHaveText("当前配置 · 本次未返回");
  await page.keyboard.press("Escape");
  await page
    .getByPlaceholder("请输入模型名称", { exact: true })
    .fill("Synthetic");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect
    .poll(() => page.evaluate(() => window.savedModel?.base_model))
    .toBe("manual-model");
});

test("successful discovery replaces built-ins, preserves selection, and falls back after empty or failure", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Edit legacy", exact: true }).click();
  let result = { models: ["other-chat", "other-reasoner", "other-chat"] };
  await page.route("**/api/system/aimodel/models", (route) =>
    route.fulfill({ json: result }),
  );
  await fetchButton(page).click();
  await expect(page.getByRole("status")).toHaveText("从服务获取 2 个模型");
  await model(page).click();
  await expect(
    page.getByRole("option").locator(".model-option-name"),
  ).toHaveText(["other-chat", "other-reasoner", "legacy-custom"]);
  await expect(
    page
      .getByRole("option", { name: "other-chat", exact: true })
      .locator(".model-option-source"),
  ).toHaveText("服务返回");
  await expect(
    page
      .getByRole("option", { name: "legacy-custom", exact: true })
      .locator(".model-option-source"),
  ).toHaveText("当前配置 · 本次未返回");
  const remoteOption = page.getByRole("option", {
    name: "other-chat",
    exact: true,
  });
  const nameBox = await remoteOption
    .locator(".model-option-name")
    .boundingBox();
  const sourceBox = await remoteOption
    .locator(".model-option-source")
    .boundingBox();
  expect(sourceBox.x).toBeGreaterThan(nameBox.x + nameBox.width);
  await page.keyboard.press("Escape");
  await expect(model(page)).toContainText("legacy-custom");
  await expect(page.getByText("0.33", { exact: true })).toBeVisible();
  for (const fallback of [
    { models: [] },
    { models: [], error: "此服务不支持获取模型列表。" },
  ]) {
    result = fallback;
    await fetchButton(page).click();
    await expect(page.getByRole("status")).toContainText(
      fallback.error ? "获取失败" : "未返回模型",
    );
    await model(page).click();
    await expect(
      page.getByRole("option", { name: "gpt-4.1", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("option", { name: "legacy-custom", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("option", { name: "other-chat", exact: true }),
    ).toHaveCount(0);
    await expect(
      page
        .getByRole("option", { name: "gpt-4.1", exact: true })
        .locator(".model-option-source"),
    ).toHaveText("内置参考");
    await page.keyboard.press("Escape");
    await expect(page.getByText("0.33", { exact: true })).toBeVisible();
  }
  result = { models: ["legacy-custom", "recovered-model"] };
  await fetchButton(page).click();
  await expect(page.getByRole("status")).toHaveText("从服务获取 2 个模型");
  await model(page).click();
  await expect(
    page.getByRole("option").locator(".model-option-name"),
  ).toHaveText(["legacy-custom", "recovered-model"]);
  await expect(
    page
      .getByRole("option", { name: "legacy-custom", exact: true })
      .locator(".model-option-source"),
  ).toHaveText("服务返回");
});

test("discovery button is a right-aligned text button whose icon follows the text color", async ({
  page,
}) => {
  const button = fetchButton(page);
  await expect(button).toHaveClass(/is-text/);
  await expect(button).not.toHaveClass(/ed-button--primary/);
  const style = await button.evaluate((el) => {
    const s = getComputedStyle(el);
    const icon = el.querySelector("svg path");
    const label = el.closest(".ed-form-item__label");
    return {
      fontSize: s.fontSize,
      height: s.height,
      borderWidth: s.borderWidth,
      position: s.position,
      color: s.color,
      iconFill: icon ? getComputedStyle(icon).fill : null,
      rightDelta: label
        ? Math.round(label.getBoundingClientRect().right - el.getBoundingClientRect().right)
        : null,
    };
  });
  expect(style.fontSize).toBe("14px");
  expect(style.height).toBe("26px");
  expect(style.borderWidth).toBe("0px");
  expect(style.position).toBe("absolute");
  expect(style.iconFill).toBe(style.color);
  expect(Math.abs(style.rightDelta)).toBeLessThanOrEqual(1);

  await page.route("**/api/system/aimodel/models", (route) =>
    route.fulfill({ json: { models: [], error: "鉴权失败，请检查 API Key。" } }),
  );
  await domain(page).fill("http://127.0.0.1:4232/v1");
  await button.click();
  await expect(page.getByRole("status")).toContainText("获取失败");
  await expect(button).toHaveClass(/is-text/);
  await expect(button).not.toHaveClass(/ed-button--primary/);
  const errorStyle = await button.evaluate((el) => {
    const icon = el.querySelector("svg path");
    return {
      color: getComputedStyle(el).color,
      iconFill: icon ? getComputedStyle(icon).fill : null,
    };
  });
  expect(errorStyle.iconFill).toBe(errorStyle.color);
});

test("loading, stale responses and credential binding", async ({ page }) => {
  let release;
  await page.route("**/api/system/aimodel/models", async (route) => {
    await new Promise((resolve) => (release = resolve));
    await route.fulfill({ json: { models: ["stale-model"] } });
  });
  await key(page).fill("synthetic-key");
  await fetchButton(page).click();
  await expect(fetchButton(page)).toBeDisabled();
  await domain(page).fill("http://127.0.0.1:4233/v1");
  await expect(key(page)).toHaveValue("");
  release();
  await expect(page.getByRole("status")).toHaveCount(0);
  await model(page).click();
  await expect(
    page.getByRole("option", { name: "stale-model", exact: true }),
  ).toHaveCount(0);
});
test("empty and failure preserve legacy selection and parameters", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Edit legacy", exact: true }).click();
  for (const result of [
    { models: [] },
    { models: [], error: "鉴权失败，请检查 API Key。" },
  ]) {
    await page.route("**/api/system/aimodel/models", (route) =>
      route.fulfill({ json: result }),
    );
    await fetchButton(page).click();
    await expect(page.getByRole("status")).toContainText(
      result.error ? "获取失败" : "未返回模型",
    );
    await expect(model(page)).toContainText("legacy-custom");
    await expect(page.getByText("0.33", { exact: true })).toBeVisible();
    await expect(domain(page)).toHaveValue("http://127.0.0.1:4232/v1");
  }
});

test("key changes invalidate results and reopening ignores pending response", async ({
  page,
}) => {
  let release;
  let calls = 0;
  await page.route("**/api/system/aimodel/models", async (route) => {
    calls++;
    if (calls === 1)
      return route.fulfill({ json: { models: ["first-result"] } });
    await new Promise((resolve) => (release = resolve));
    await route.fulfill({ json: { models: ["closed-result"] } });
  });
  await fetchButton(page).click();
  await expect(page.getByRole("status")).toContainText("1 个模型");
  await key(page).fill("changed-synthetic-key");
  await expect(page.getByRole("status")).toHaveCount(0);
  await fetchButton(page).click();
  await expect.poll(() => calls).toBe(2);
  await page.getByRole("button", { name: "Toggle form", exact: true }).click();
  const response = page.waitForResponse("**/api/system/aimodel/models");
  release();
  await response;
  await page.getByRole("button", { name: "Toggle form", exact: true }).click();
  await page.getByRole("button", { name: "New generic", exact: true }).click();
  await expect(page.getByRole("status")).toHaveCount(0);
  await model(page).click();
  await expect(
    page.getByRole("option", { name: "closed-result", exact: true }),
  ).toHaveCount(0);
});

test("original drawer preserves interaction while discovery matches prototype states", async ({
  page,
}, testInfo) => {
  const mutations = [];
  page.on("request", (request) => {
    if (
      request.method() !== "GET" &&
      /\/aimodel\/?$/.test(new URL(request.url()).pathname)
    )
      mutations.push(request.url());
  });
  await page.setViewportSize({ width: 1280, height: 1024 });
  await page.goto("/full.html");
  await page.getByRole("button", { name: "编辑", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("编辑通用OpenAI");
  await expect(
    dialog.getByRole("button", { name: "验证连接", exact: true }),
  ).toHaveCount(0);
  await expect(page.locator(".params-table")).toBeVisible();
  await expect(page.locator(".generic-model-drawer")).toHaveCount(0);
  const drawerBox = await dialog.boundingBox();
  expect(drawerBox.width).toBe(1280);
  expect(drawerBox.height).toBe(924);
  await expect(
    dialog.getByRole("button", { name: "取消", exact: true }),
  ).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "保存", exact: true }),
  ).toBeVisible();
  const inputBox = await model(page).boundingBox();
  const buttonBox = await fetchButton(page).boundingBox();
  expect(
    Math.abs(buttonBox.x + buttonBox.width - inputBox.x - inputBox.width),
  ).toBeLessThan(24);
  let release;
  await page.route("**/api/system/aimodel/models", async (route) => {
    await new Promise((resolve) => (release = resolve));
    await route.fulfill({
      json: { models: ["demo-chat", "demo-reasoner", "demo-code"] },
    });
  });
  await fetchButton(page).click();
  await expect(
    dialog.getByRole("button", { name: "获取中...", exact: true }),
  ).toBeDisabled();
  await expect.poll(() => Boolean(release)).toBe(true);
  await dialog.screenshot({
    path: testInfo.outputPath("prototype-loading.png"),
  });
  release();
  await expect(page.getByRole("status")).toHaveText("从服务获取 3 个模型");
  await expect(page.getByRole("status")).toHaveCSS("color", "rgb(0, 138, 0)");
  await model(page).click();
  await expect(
    page.getByText("支持搜索或手动输入模型 ID", { exact: true }),
  ).toBeVisible();
  await page.waitForTimeout(300);
  await dialog.screenshot({
    path: testInfo.outputPath("prototype-success.png"),
  });
  await page.keyboard.press("Escape");
  await page.route("**/api/system/aimodel/models", (route) =>
    route.fulfill({
      json: { models: [], error: "鉴权失败，请检查 API Key。" },
    }),
  );
  await fetchButton(page).click();
  await expect(page.getByRole("status")).toHaveText(
    "获取失败，请稍后重试。可手动输入模型 ID。",
  );
  await expect(page.getByRole("status")).toHaveCSS("color", "rgb(255, 0, 0)");
  await expect(
    dialog.getByRole("button", { name: "重新获取", exact: true }),
  ).toBeVisible();
  await page.route("**/api/system/aimodel/models", (route) =>
    route.fulfill({ json: { models: [] } }),
  );
  await fetchButton(page).click();
  await expect(page.getByRole("status")).toHaveText(
    "未返回模型，可手动输入模型 ID。",
  );
  await dialog.screenshot({ path: testInfo.outputPath("prototype-empty.png") });
  expect(mutations).toEqual([]);
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  await expect(dialog).not.toBeVisible();
});

test("every active compatible supplier exposes discovery and keeps manual fallback", async ({
  page,
}) => {
  const suppliers = await page.evaluate(() => window.testSuppliers);
  let requested = 0;
  await page.route("**/api/system/aimodel/models", async (route) => {
    requested++;
    expect(route.request().postDataJSON().api_key).toBe("synthetic-key");
    await route.fulfill({ json: { models: ["discovered-model"] } });
  });
  for (const supplier of suppliers) {
    await test.step(supplier.name, async () => {
      await page.evaluate((id) => window.selectTestSupplier(id), supplier.id);
      await expect(domain(page)).toBeVisible();
      await expect(key(page)).toHaveValue("");
      await key(page).fill("synthetic-key");
      await fetchButton(page).click();
      await expect(page.getByRole("status")).toHaveText("从服务获取 1 个模型");
      await model(page).click();
      await page
        .getByRole("option", { name: "discovered-model", exact: true })
        .click();
      await page
        .getByPlaceholder("请输入模型名称", { exact: true })
        .fill(supplier.name);
      await page.getByRole("button", { name: "Save", exact: true }).click();
      await expect
        .poll(() => page.evaluate(() => window.savedModel?.base_model))
        .toBe("discovered-model");
      await page.route("**/api/system/aimodel/models", (route) =>
        route.fulfill({ json: { models: [], error: "unsupported" } }),
      );
      await fetchButton(page).click();
      await expect(page.getByRole("status")).toContainText("获取失败");
      await model(page).locator("input").fill("manual-model");
      await page
        .getByRole("option", { name: "manual-model", exact: true })
        .click();
      await page.getByRole("button", { name: "Save", exact: true }).click();
      await expect
        .poll(() => page.evaluate(() => window.savedModel?.base_model))
        .toBe("manual-model");
      await page.unroute("**/api/system/aimodel/models");
      await page.route("**/api/system/aimodel/models", async (route) => {
        requested++;
        expect(route.request().postDataJSON().api_key).toBe("synthetic-key");
        await route.fulfill({ json: { models: ["discovered-model"] } });
      });
    });
  }
  expect(requested).toBe(suppliers.length);
});

test("per-model defaults still change endpoints and custom addresses survive selection", async ({
  page,
}) => {
  await page.evaluate(() => window.selectTestSupplier(5));
  await key(page).fill("synthetic-key");
  await model(page).click();
  await page.getByRole("option", { name: "x1", exact: true }).click();
  await expect(domain(page)).toHaveValue(
    "https://spark-api-open.xf-yun.com/v2/",
  );
  await expect(key(page)).toHaveValue("");
  await domain(page).fill("http://127.0.0.1:4232/custom/v1");
  await key(page).fill("synthetic-key");
  await model(page).click();
  await page.getByRole("option", { name: "4.0Ultra", exact: true }).click();
  await expect(domain(page)).toHaveValue("http://127.0.0.1:4232/custom/v1");
  await expect(key(page)).toHaveValue("synthetic-key");
  await page.evaluate(() => window.selectTestSupplier(3));
  await expect(key(page)).toHaveValue("");
});

test("non-compatible historical protocol does not expose discovery", async ({
  page,
}) => {
  await page.evaluate(() =>
    window.editTestSupplier({
      id: "1",
      supplier: 15,
      name: "Legacy",
      model_type: 0,
      base_model: "legacy",
      api_domain: "http://127.0.0.1:4232/v1",
      api_key: "",
      protocol: 2,
      config_list: [],
    }),
  );
  await expect(fetchButton(page)).toHaveCount(0);
});

test("switching vendors ignores in-flight results and clears credentials", async ({
  page,
}) => {
  await page.evaluate(() => window.selectTestSupplier(3));
  await key(page).fill("synthetic-key");
  let release;
  await page.route("**/api/system/aimodel/models", async (route) => {
    await new Promise((resolve) => (release = resolve));
    await route.fulfill({ json: { models: ["old-vendor-result"] } });
  });
  await fetchButton(page).click();
  await expect.poll(() => Boolean(release)).toBe(true);
  await page.evaluate(() => window.selectTestSupplier(7));
  await expect(key(page)).toHaveValue("");
  const response = page.waitForResponse("**/api/system/aimodel/models");
  release();
  await response;
  await expect(page.getByRole("status")).toHaveCount(0);
  await model(page).click();
  await expect(
    page.getByRole("option", { name: "old-vendor-result", exact: true }),
  ).toHaveCount(0);
});

test("timeout is explicit, safe, non-blocking and retryable", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Edit legacy", exact: true }).click();
  let release;
  await page.route("**/api/system/aimodel/models", async (route) => {
    await new Promise((resolve) => (release = resolve));
    await route.fulfill({
      json: {
        models: [],
        error_code: "timeout",
        error: "synthetic-secret-provider-body",
      },
    });
  });
  await fetchButton(page).click();
  await expect(fetchButton(page)).toBeDisabled();
  await expect.poll(() => Boolean(release)).toBe(true);
  release();
  await expect(page.getByRole("status")).toHaveText(
    "获取模型列表超时，请稍后重试。也可手动输入模型 ID。",
  );
  await expect(fetchButton(page)).toBeEnabled();
  await expect(model(page)).toContainText("legacy-custom");
  await expect(page.getByText("0.33", { exact: true })).toBeVisible();
  expect(await page.getByRole("status").getAttribute("title")).not.toContain(
    "synthetic-secret",
  );
  await page.route("**/api/system/aimodel/models", (route) =>
    route.fulfill({ json: { models: ["recovered-model"] } }),
  );
  await fetchButton(page).click();
  await expect(page.getByRole("status")).toHaveText("从服务获取 1 个模型");
  await expect(page.getByRole("status")).not.toHaveAttribute(
    "title",
    /synthetic-secret/,
  );
});

for (const [code, message] of [
  ["unsupported", "此服务不支持获取模型列表，可手动输入模型 ID。"],
  [
    "credentials",
    "鉴权失败，请检查 API Key 和服务访问权限。也可手动输入模型 ID。",
  ],
  ["address", "API 基地址无效，请检查地址。也可手动输入模型 ID。"],
  ["invalid", "模型列表格式无效或超出大小限制，可手动输入模型 ID。"],
]) {
  test(`safe discovery reason ${code} preserves configuration and can recover`, async ({
    page,
  }) => {
    await page
      .getByRole("button", { name: "Edit legacy", exact: true })
      .click();
    await page.route("**/api/system/aimodel/models", (route) =>
      route.fulfill({
        json: {
          models: [],
          error_code: code,
          error: "synthetic-secret-provider-body",
        },
      }),
    );
    await fetchButton(page).click();
    await expect(page.getByRole("status")).toHaveText(message);
    await expect(page.getByRole("status")).toHaveAttribute("title", message);
    await expect(fetchButton(page)).toBeEnabled();
    await expect(model(page)).toContainText("legacy-custom");
    await expect(page.getByText("0.33", { exact: true })).toBeVisible();
    expect(await page.locator("body").innerText()).not.toContain(
      "synthetic-secret",
    );
    await page.route("**/api/system/aimodel/models", (route) =>
      route.fulfill({ json: { models: ["recovered-model"] } }),
    );
    await fetchButton(page).click();
    await expect(page.getByRole("status")).toHaveText("从服务获取 1 个模型");
  });
}

test("unknown, legacy and network failures use safe fallback and stale errors are ignored", async ({
  page,
}) => {
  for (const code of [
    "failed",
    "unknown-secret-code",
    "constructor",
    "__proto__",
    undefined,
  ]) {
    await page.route("**/api/system/aimodel/models", (route) =>
      route.fulfill({
        json: {
          models: [],
          error_code: code,
          error: "synthetic-secret-provider-body",
        },
      }),
    );
    await fetchButton(page).click();
    await expect(page.getByRole("status")).toHaveText(
      "获取失败，请稍后重试。可手动输入模型 ID。",
    );
    await expect(page.getByRole("status")).toHaveAttribute(
      "title",
      "获取失败，请稍后重试。可手动输入模型 ID。",
    );
  }
  await page.route("**/api/system/aimodel/models", (route) =>
    route.abort("failed"),
  );
  await fetchButton(page).click();
  await expect(page.getByRole("status")).toHaveText(
    "获取失败，请稍后重试。可手动输入模型 ID。",
  );
  await expect(fetchButton(page)).toBeEnabled();
  let release;
  await page.route("**/api/system/aimodel/models", async (route) => {
    await new Promise((resolve) => (release = resolve));
    await route.fulfill({
      json: {
        models: [],
        error_code: "credentials",
        error: "synthetic-secret",
      },
    });
  });
  await fetchButton(page).click();
  await expect.poll(() => Boolean(release)).toBe(true);
  await domain(page).fill("http://127.0.0.1:4232/new/v1");
  const response = page.waitForResponse("**/api/system/aimodel/models");
  release();
  await response;
  await expect(page.getByRole("status")).toHaveCount(0);
});

test("discovery feedback keeps the layout stable and the dropdown anchored", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 1024 });
  const select = model(page);
  const before = await select.boundingBox();
  await page.route("**/api/system/aimodel/models", (route) =>
    route.fulfill({ json: { models: ["demo-chat", "demo-reasoner"] } }),
  );
  await domain(page).fill("http://127.0.0.1:4232/v1");
  await fetchButton(page).click();
  await expect(page.getByRole("status")).toHaveText("从服务获取 2 个模型");
  const afterFetch = await select.boundingBox();
  expect(Math.abs(afterFetch.y - before.y)).toBeLessThan(1);
  await select.click();
  const popper = page.locator(".ed-select__popper.discovery-model-options");
  await expect(popper).toBeVisible();
  const popperBox = await popper.boundingBox();
  expect(popperBox.y - (afterFetch.y + afterFetch.height)).toBeLessThan(24);
  await page.keyboard.press("Escape");
  await page.route("**/api/system/aimodel/models", (route) =>
    route.fulfill({
      json: { models: [], error_code: "credentials", error: "synthetic-secret" },
    }),
  );
  await fetchButton(page).click();
  await expect(page.getByRole("status")).toContainText("鉴权失败");
  const afterFailure = await select.boundingBox();
  expect(Math.abs(afterFailure.y - before.y)).toBeLessThan(1);
  const statusBox = await page.getByRole("status").boundingBox();
  expect(statusBox.y).toBeGreaterThan(afterFailure.y + afterFailure.height);
});

test("option source label keeps clear of the selection check", async ({ page }) => {
  await page.getByRole("button", { name: "Edit legacy", exact: true }).click();
  await model(page).click();
  const popper = page.locator(".ed-select__popper.discovery-model-options");
  await expect(popper).toBeVisible();
  const selected = popper.locator(".ed-select-dropdown__item.is-selected");
  await expect(selected).toHaveCount(1);
  const itemBox = await selected.boundingBox();
  const sourceBox = await selected
    .locator(".model-option-source")
    .boundingBox();
  // 勾选图标绝对定位在 right: 12px、宽 16px，即占据右侧 12-28px。
  expect(
    itemBox.x + itemBox.width - (sourceBox.x + sourceBox.width),
  ).toBeGreaterThanOrEqual(36);
});
