import { defineConfig } from '@playwright/test'
import base from './playwright.config.mjs'

const baseURL = 'http://127.0.0.1:4243'

export default defineConfig({
  ...base,
  webServer: {
    cwd: '../../frontend',
    command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 4243 --strictPort',
    env: { VITE_API_BASE_URL: '/api/v1' },
    url: baseURL,
    reuseExistingServer: false,
    timeout: 60_000,
  },
  projects: [{ name: 'request-locale', testMatch: 'request-locale.spec.mjs', use: { baseURL, locale: 'en-US' } }],
  outputDir: 'output/request-locale-results',
})
