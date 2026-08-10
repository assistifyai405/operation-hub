// @ts-check
const { defineConfig, devices } = require("@playwright/test");

const baseURL =
  process.env.STAGING_BASE_URL ||
  process.env.E2E_BASE_URL ||
  "http://127.0.0.1:3000";

module.exports = defineConfig({
  testDir: "./tests",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
