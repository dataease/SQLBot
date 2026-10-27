import { defineConfig } from '@playwright/test'
import base from './playwright.config.mjs'

export default defineConfig({
  ...base,
  webServer: {
    command: 'node fixtures/menu-language/server.mjs',
    url: 'http://127.0.0.1:4217',
    reuseExistingServer: false,
    timeout: 30000
  },
  projects: [{ name: 'menu-language', testMatch: 'menu-language.spec.mjs', use: { baseURL: 'http://127.0.0.1:4217' } }],
  outputDir: 'output/menu-language-results'
})
