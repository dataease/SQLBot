import { defineConfig } from "@playwright/test";
import base from "./playwright.config.mjs";
export default defineConfig({
  ...base,
  webServer: {
    command: "node fixtures/model-discovery/server.mjs",
    url: "http://127.0.0.1:4231",
    reuseExistingServer: false,
    timeout: 30000,
  },
  projects: [
    {
      name: "model-discovery",
      testMatch: "model-discovery.spec.mjs",
      use: { baseURL: "http://127.0.0.1:4231" },
    },
  ],
  outputDir: "output/model-discovery-results",
});
