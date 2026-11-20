import { defineConfig } from '@playwright/test';
import base from './playwright.config.mjs';
export default defineConfig({ ...base,
  webServer: { command: 'node fixtures/account-binding/server.mjs', url: 'http://127.0.0.1:4236', reuseExistingServer: false, timeout: 30000 },
  projects: [{ name: 'account-binding', testMatch: 'account-binding.spec.mjs', use: { baseURL: 'http://127.0.0.1:4236' } }],
  outputDir: 'output/account-binding-results',
});
