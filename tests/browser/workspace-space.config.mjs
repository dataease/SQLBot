import { defineConfig } from '@playwright/test'
import base from './playwright.config.mjs'

export default defineConfig({
  ...base,
  webServer: {
    command: 'node fixtures/workspace-space/server.mjs',
    url: 'http://127.0.0.1:4250',
    reuseExistingServer: false,
    timeout: 30000,
  },
  projects: [
    {
      name: 'workspace-space',
      testMatch: 'workspace-space.spec.mjs',
      use: { baseURL: 'http://127.0.0.1:4250' },
    },
  ],
  outputDir: 'output/workspace-space-results',
})
