import { defineConfig } from '@playwright/test'
import base from './playwright.config.mjs'
export default defineConfig({
  ...base,
  webServer: { command: 'node fixtures/cas/server.mjs', url: 'http://127.0.0.1:4219', reuseExistingServer: false, timeout: 30000 },
  projects: [{ name: 'cas', testMatch: 'cas.spec.mjs', use: { baseURL: 'http://127.0.0.1:4219' } }],
  outputDir: 'output/cas-results'
})
