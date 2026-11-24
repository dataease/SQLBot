import { defineConfig } from '@playwright/test'
import base from './playwright.config.mjs'

export default defineConfig({
  ...base,
  webServer: {
    command: 'node fixtures/pagination/server.mjs',
    url: 'http://127.0.0.1:4247',
    reuseExistingServer: false,
    timeout: 30000,
  },
  projects: [
    {
      name: 'workspace-member',
      testMatch: 'workspace-member.spec.mjs',
      use: { baseURL: 'http://127.0.0.1:4247' },
    },
  ],
  outputDir: 'output/workspace-member-results',
})
