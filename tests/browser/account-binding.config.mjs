import { defineConfig } from '@playwright/test';
import base from './playwright.config.mjs';
const baseURL = `http://127.0.0.1:${process.env.SQLBOT_BINDING_BROWSER_PORT || 4236}`;
export default defineConfig({ ...base,
  webServer: { command: 'node fixtures/account-binding/server.mjs', url: baseURL, reuseExistingServer: false, timeout: 30000 },
  projects: [{ name: 'account-binding', testMatch: 'account-binding.spec.mjs', use: { baseURL } }],
  outputDir: 'output/account-binding-results',
});
