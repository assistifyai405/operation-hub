// @ts-check
const { defineConfig, devices } = require("@playwright/test");

const baseURL =
  process.env.STAGING_BASE_URL ||
  process.env.E2E_BASE_URL ||
  "http://127.0.0.1:3000";

const isStaging = Boolean(process.env.STAGING_BASE_URL);

module.exports = defineConfig({
  testDir: "./tests",
  timeout: isStaging ? 120_000 : 90_000,
  expect: { timeout: isStaging ? 20_000 : 15_000 },
  fullyParallel: false,
  retries: process.env.CI || isStaging ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 20_000,
    navigationTimeout: 45_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  outputDir: "test-results",
});
