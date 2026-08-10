#!/usr/bin/env node
/**
 * Staging Playwright runner — refuses to pretend success without STAGING_BASE_URL.
 */
const { spawnSync } = require("child_process");

const base = (process.env.STAGING_BASE_URL || "").replace(/\/$/, "");
const api = (process.env.E2E_API_URL || process.env.STAGING_API_URL || "").replace(/\/$/, "");

function isLocal(url) {
  return !url || /localhost|127\.0\.0\.1/i.test(url);
}

if (!base || isLocal(base)) {
  console.error("PENDING: Staging E2E requires an external STAGING_BASE_URL (https://…).");
  console.error("Example:");
  console.error("  STAGING_BASE_URL=https://staging.example.com \\");
  console.error("  E2E_API_URL=https://api.staging.example.com \\");
  console.error("  yarn test:staging");
  process.exit(2);
}

if (!api || isLocal(api)) {
  console.error("PENDING: Staging E2E requires E2E_API_URL / STAGING_API_URL (https://…).");
  process.exit(2);
}

process.env.E2E_BASE_URL = base;
process.env.STAGING_BASE_URL = base;
process.env.E2E_API_URL = api;

const r = spawnSync("npx", ["playwright", "test"], {
  stdio: "inherit",
  env: process.env,
  shell: process.platform === "win32",
});
process.exit(r.status == null ? 1 : r.status);
