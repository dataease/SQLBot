import { defineConfig } from '@playwright/test'
import base from './playwright.config.mjs'

export default defineConfig({
  ...base,
  webServer: {
    command: 'node fixtures/welcome-language/server.mjs',
    url: 'http://127.0.0.1:4218',
    reuseExistingServer: false,
    timeout: 30000
  },
  projects: [{ name: 'welcome-language', testMatch: 'welcome-language.spec.mjs', use: { baseURL: 'http://127.0.0.1:4218' } }],
  outputDir: 'output/welcome-language-results'
})
