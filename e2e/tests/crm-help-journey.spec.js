/**
 * Sprint 31 — CRM help + guided tour journey (NL).
 * Does not auto-create hidden workspace data; user-driven tour clicks only.
 */
const { test, expect } = require("@playwright/test");

const API = (process.env.E2E_API_URL || process.env.STAGING_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function apiReachable(request) {
  try {
    const r = await request.get(`${API}/api/health/live`, { timeout: 8_000 });
    return r.ok();
  } catch {
    return false;
  }
}

async function dismissProductTour(page) {
  const skip = page.getByTestId("product-tour-skip");
  if (await skip.count()) await skip.first().click().catch(() => {});
}

test.describe("Sprint 31 CRM help system", () => {
  test.beforeAll(async ({ request }) => {
    const ok = await apiReachable(request);
    test.skip(!ok, `Backend not reachable at ${API}`);
  });

  test("NL CRM help → tutorial → try yourself → tour remembered", async ({ browser }) => {
    test.setTimeout(240_000);
    const context = await browser.newContext({ locale: "nl-NL" });
    const page = await context.newPage();
    const runId = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const email = `help31_${runId}@example.com`;
    const password = "Password123!";

    await page.goto("/register", { waitUntil: "domcontentloaded", timeout: 30_000 });
    await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
    await page.getByTestId("register-firstname").fill("Help");
    await page.getByTestId("register-lastname").fill("Tour");
    await page.getByTestId("register-email").fill(email);
    await page.getByTestId("register-password").fill(password);
    const company = page.getByTestId("register-company");
    if (await company.count()) await company.fill("Help Co");
    await page.getByTestId("register-submit").click();
    await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 45_000 });
    if (page.url().includes("onboarding")) {
      const skip = page.getByTestId("onboarding-save-exit").or(page.getByTestId("onb-welcome-skip"));
      if (await skip.count()) await skip.first().click();
      await expect(page).toHaveURL(/dashboard/, { timeout: 45_000 });
    }
    await dismissProductTour(page);

    await page.goto("/crm", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("crm-page")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("page-help-crm")).toBeVisible();

    await page.getByTestId("page-help-crm").click();
    await expect(page.getByTestId("help-panel")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("help-panel-description")).toContainText(/leads|klanten|verkoop/i);

    await page.getByTestId("help-start-tutorial").click();
    await expect(page.getByTestId("mini-walkthrough")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("crm-tutorial-stage")).toBeVisible();
    for (let i = 0; i < 10; i += 1) {
      if (await page.getByTestId("mini-walkthrough-done").count()) {
        await page.getByTestId("mini-walkthrough-done").click();
        break;
      }
      await page.getByTestId("mini-walkthrough-next").click();
    }
    await expect(page.getByTestId("mini-walkthrough")).toHaveCount(0, { timeout: 10_000 });

    // Re-open help and start guided tour
    await page.getByTestId("page-help-crm").click();
    await expect(page.getByTestId("help-panel")).toBeVisible({ timeout: 10_000 });
    await page.getByTestId("help-try-yourself").click();

    await expect(page).toHaveURL(/pipeline/, { timeout: 20_000 });
    await expect(page.getByTestId("guided-tour")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("guided-tour-highlight").or(page.getByTestId("guided-tour-title")).first()).toBeVisible();

    // Safe completion via Done/Skip without forcing hidden API creates beyond optional user click
    const doneBtn = page.getByTestId("guided-tour-done");
    const skipBtn = page.getByTestId("guided-tour-skip");
    // Move to last step with Next when enabled, else skip
    for (let i = 0; i < 4; i += 1) {
      if (await doneBtn.count()) break;
      const next = page.getByTestId("guided-tour-next");
      if (await next.count() && await next.isEnabled()) await next.click();
      else break;
    }
    if (await doneBtn.count()) await doneBtn.click();
    else if (await skipBtn.count()) await skipBtn.click();

    await expect(page.getByTestId("guided-tour")).toHaveCount(0, { timeout: 10_000 });

    const progress = await page.evaluate(() => {
      const keys = Object.keys(localStorage).filter((k) => k.includes("assistify_help_"));
      return keys.map((k) => ({ k, v: localStorage.getItem(k) }));
    });
    expect(progress.length).toBeGreaterThan(0);

    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("pipeline-page").or(page.getByTestId("crm-page")).first()).toBeVisible({ timeout: 20_000 });
    // Tour should not auto-reopen after completion/skip persistence
    await expect(page.getByTestId("guided-tour")).toHaveCount(0);

    await context.close();
  });
});
