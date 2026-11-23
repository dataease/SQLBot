import { defineConfig } from '@playwright/test'
import base from './playwright.config.mjs'
const url = `http://127.0.0.1:${process.env.SQLBOT_DRAG_BROWSER_PORT || 4288}`
export default defineConfig({
  ...base,
  webServer: {
    command: 'node fixtures/assistant-drag/server.mjs',
    url,
    reuseExistingServer: false,
  },
  projects: [
    {
      name: 'assistant-drag',
      testMatch: 'assistant-drag.spec.mjs',
      use: {
        baseURL: url,
        viewport: { width: 1000, height: 700 },
        hasTouch: true,
      },
    },
  ],
  outputDir: 'output/assistant-drag-results',
})
