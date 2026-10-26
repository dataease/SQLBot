import { defineConfig } from '@playwright/test'
import base from './playwright.config.mjs'
export default defineConfig({
  ...base,
  webServer: { command: 'node fixtures/password/server.mjs', url: 'http://127.0.0.1:4208', reuseExistingServer: false, timeout: 30000 },
  projects: [{ name: 'password', testMatch: 'password-policy.spec.mjs', use: { baseURL: 'http://127.0.0.1:4208' } }],
  outputDir: 'output/password-results'
})
