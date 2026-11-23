import { defineConfig } from '@playwright/test';
import base from './playwright.config.mjs';
const python = process.env.SQLBOT_BINDING_TEST_PYTHON;
if (!python || !process.env.SQLBOT_XPACK_TEST_ROOT || !process.env.PYTHONPATH) {
  throw new Error('Set SQLBOT_BINDING_TEST_PYTHON, SQLBOT_XPACK_TEST_ROOT and PYTHONPATH to the prepared cross-repository test environment.');
}
const uiPort = Number(process.env.SQLBOT_BINDING_UI_PORT || 4267);
const apiPort = Number(process.env.SQLBOT_BINDING_BACKEND_PORT || 4268);
const ui = `http://127.0.0.1:${uiPort}`;
const api = `http://127.0.0.1:${apiPort}`;
export default defineConfig({ ...base,
  timeout: 60000,
  webServer: [
    { command: `"${python}" fixtures/account-binding/backend.py`, url: `${api}/__test/health`, reuseExistingServer: false, timeout: 30000,
      env: { SQLBOT_BINDING_UI_URL: ui, SQLBOT_BINDING_BACKEND_PORT: String(apiPort), LOG_FORMAT: '%(levelname)s %(message)s' } },
    { command: 'node fixtures/account-binding/server.mjs', url: ui, reuseExistingServer: false, timeout: 30000,
      env: { SQLBOT_BINDING_UI_PORT: String(uiPort), SQLBOT_BINDING_API_URL: api } },
  ],
  projects: [{ name: 'account-binding-quota', testMatch: 'account-binding-quota.spec.mjs', use: { baseURL: ui } }],
  outputDir: 'output/account-binding-quota-results',
});
