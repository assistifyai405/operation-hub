/**
 * Sprint 31.5 — Authenticated light theme, onboarding & expanded help.
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

async function register(page, prefix) {
  const runId = `${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
  const email = `${prefix}_${runId}@example.com`;
  await page.goto("/register", { waitUntil: "domcontentloaded", timeout: 30_000 });
  await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("register-firstname").fill("Light");
  await page.getByTestId("register-lastname").fill("User");
  await page.getByTestId("register-email").fill(email);
  await page.getByTestId("register-password").fill("Password123!");
  const company = page.getByTestId("register-company");
  if (await company.count()) await company.fill("Light Co");
  await page.getByTestId("register-submit").click();
  await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 45_000 });
  return email;
}

test.describe("Sprint 31.5 light app + guidance", () => {
  test.beforeAll(async ({ request }) => {
    const ok = await apiReachable(request);
    test.skip(!ok, `Backend not reachable at ${API}`);
  });

  test("NL onboarding → light dashboard → theme toggle → tutorials", async ({ browser }) => {
    test.setTimeout(240_000);
    const context = await browser.newContext({ locale: "nl-NL" });
    const page = await context.newPage();

    await register(page, "s315");

    if (page.url().includes("onboarding")) {
      await expect(page.getByTestId("onboarding-page")).toBeVisible();
      await expect(page.locator("body")).toContainText(/Welkom bij Assistify|Assistify brengt/i);
      // Skip through to dashboard via save-exit
      await page.getByTestId("onboarding-save-exit").click();
      await expect(page).toHaveURL(/dashboard/, { timeout: 45_000 });
    }

    await dismissProductTour(page);
    await expect(page.getByTestId("app-shell")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("app-shell")).toHaveAttribute("data-resolved-theme", "light");

    // Checklist present for new user
    const checklist = page.getByTestId("onboarding-checklist");
    if (await checklist.count()) {
      await expect(checklist).toContainText(/Aan de slag|Getting started|klant|client/i);
    }

    // Dashboard help
    await expect(page.getByTestId("page-help-dashboard")).toBeVisible();
    await page.getByTestId("page-help-dashboard").click();
    await expect(page.getByTestId("help-panel")).toBeVisible();
    await expect(page.getByTestId("help-panel-description")).toContainText(/Dashboard|prioriteiten|overzicht|workspace/i);
    await page.getByTestId("help-start-tutorial").click();
    await expect(page.getByTestId("mini-walkthrough")).toBeVisible();
    await expect(page.getByTestId("dashboard-tutorial-stage")).toBeVisible();
    await page.getByTestId("mini-walkthrough-close").click();

    // Theme settings
    await page.goto("/settings?tab=appearance", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("settings-appearance")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("theme-option-dark").click();
    await expect(page.getByTestId("app-shell")).toHaveAttribute("data-resolved-theme", "dark");
    const storedDark = await page.evaluate(() => localStorage.getItem("assistify_theme"));
    expect(storedDark).toBe("dark");

    await page.getByTestId("theme-option-light").click();
    await expect(page.getByTestId("app-shell")).toHaveAttribute("data-resolved-theme", "light");

    // Projects tutorial
    await page.goto("/projects", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("page-help-projects")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("page-help-projects").click();
    await expect(page.getByTestId("help-panel")).toBeVisible();
    await page.getByTestId("help-start-tutorial").click();
    await expect(page.getByTestId("projects-tutorial-stage")).toBeVisible({ timeout: 10_000 });
    await page.getByTestId("mini-walkthrough-close").click();

    // Copilot tutorial
    await page.goto("/ai-chat", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("page-help-copilot")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("page-help-copilot").click();
    await page.getByTestId("help-start-tutorial").click();
    await expect(page.getByTestId("copilot-tutorial-stage")).toBeVisible({ timeout: 10_000 });
    await page.getByTestId("mini-walkthrough-close").click();

    // CRM help still works
    await page.goto("/crm", { waitUntil: "domcontentloaded" });
    await page.getByTestId("page-help-crm").click();
    await expect(page.getByTestId("help-panel-description")).toContainText(/leads|klanten|verkoop/i);
    await page.getByTestId("help-panel-close").click();

    // Marketing stays light regardless
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("marketing-home")).toBeVisible();
    await expect(page.getByTestId("day-with-assistify")).toBeVisible();
    const theme = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
    expect(theme).toBe("light");

    await context.close();
  });
});
