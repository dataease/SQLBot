import { defineConfig } from '@playwright/test'
import base from './playwright.config.mjs'
export default defineConfig({ ...base,
  webServer: { command: 'node fixtures/platform-login/server.mjs', url: 'http://127.0.0.1:4251', reuseExistingServer: false, timeout: 30000 },
  projects: [{ name: 'platform-login', testMatch: 'platform-login.spec.mjs', use: { baseURL: 'http://127.0.0.1:4251' } }],
  outputDir: 'output/platform-login-results',
})
