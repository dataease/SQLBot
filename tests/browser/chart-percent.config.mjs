import { defineConfig } from '@playwright/test'
import base from './playwright.config.mjs'

export default defineConfig({
  ...base,
  webServer: [],
  projects: [{ name: 'chart-percent', testMatch: 'chart-percent.spec.mjs' }],
  outputDir: 'output/chart-percent-results',
})
