/**
 * Sprint 29.5 — Extended localization journey.
 * Dutch browser → register → major modules (NL) → switch EN → verify → reload.
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

async function dismissTourIfPresent(page) {
  const skip = page.getByTestId("product-tour-skip").or(page.getByRole("button", { name: /skip|overslaan|got it|begrepen|close tour/i }));
  if (await skip.count()) {
    await skip.first().click().catch(() => {});
  }
}

async function assertIntro(page, nlPattern, enPattern, expectNl) {
  const title = page.getByTestId("page-intro-title");
  const desc = page.getByTestId("page-intro-description");
  if (await title.count()) {
    await expect(title.first()).toBeVisible({ timeout: 15_000 });
    await expect(title.first()).toContainText(expectNl ? nlPattern : enPattern);
  } else if (await desc.count()) {
    await expect(desc.first()).toContainText(expectNl ? nlPattern : enPattern);
  }
}

test.describe("Sprint 29.5 extended localization journey", () => {
  test.beforeAll(async ({ request }) => {
    const ok = await apiReachable(request);
    test.skip(!ok, `Backend not reachable at ${API}`);
  });

  test("NL modules → EN switch → reload persists across major pages", async ({ browser }) => {
    test.setTimeout(240_000);
    const context = await browser.newContext({ locale: "nl-NL" });
    const page = await context.newPage();
    const runId = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const email = `locale295_${runId}@example.com`;
    const password = "Password123!";

    await page.goto("/register", { waitUntil: "domcontentloaded", timeout: 30_000 });
    await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("register-submit")).toContainText(/Account aanmaken/i);

    await page.getByTestId("register-firstname").fill("Locale");
    await page.getByTestId("register-lastname").fill("Full");
    await page.getByTestId("register-email").fill(email);
    await page.getByTestId("register-password").fill(password);
    const company = page.getByTestId("register-company");
    if (await company.count()) await company.fill("Locale Full Co");
    await page.getByTestId("register-submit").click();
    await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 45_000 });

    if (page.url().includes("onboarding")) {
      const skip = page.getByTestId("onboarding-save-exit").or(page.getByTestId("onb-welcome-skip"));
      if (await skip.count()) await skip.first().click();
      await expect(page).toHaveURL(/dashboard/, { timeout: 45_000 });
    }
    await dismissTourIfPresent(page);

    // Create client + project for workspace visit
    await page.goto("/clients", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("clients-page")).toBeVisible({ timeout: 20_000 });
    await assertIntro(page, /Klanten/i, /Clients/i, true);
    await page.getByTestId("add-client-btn").click();
    await page.getByTestId("client-name-input").fill(`NL Client ${runId}`);
    await page.getByTestId("client-save-btn").click();
    await expect(page.getByTestId("clients-page")).toContainText(new RegExp(`NL Client ${runId}`), { timeout: 15_000 });

    await page.goto("/projects", { waitUntil: "domcontentloaded" });
    await assertIntro(page, /Projecten/i, /Projects/i, true);
    const addProject = page.getByTestId("new-project-btn");
    if (await addProject.count()) {
      await addProject.first().click();
      const name = page.getByTestId("project-name-input");
      if (await name.count()) {
        await name.first().fill(`NL Project ${runId}`);
        // Optional client select
        const clientTrigger = page.getByTestId("project-client-trigger");
        if (await clientTrigger.count()) {
          await clientTrigger.click().catch(() => {});
          const opt = page.locator("[data-testid^='project-client-']").first();
          if (await opt.count()) await opt.click().catch(() => {});
        }
        await page.getByTestId("project-save-btn").click();
      }
    }

    // Dutch pass across modules
    const nlChecks = [
      ["/dashboard", /overzicht|aandacht|Dashboard|gebeurt/i],
      ["/clients", /Klanten/i],
      ["/projects", /Projecten/i],
      ["/tasks", /Taken/i],
      ["/ai-chat", /Copilot|assistent|werkzaamheden/i],
      ["/settings", /Instellingen/i],
    ];
    for (const [path, re] of nlChecks) {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      await dismissTourIfPresent(page);
      const body = page.locator("body");
      await expect(body).toContainText(re, { timeout: 20_000 });
    }

    // Open first project workspace if available
    await page.goto("/projects", { waitUntil: "domcontentloaded" });
    const row = page.locator("[data-testid^='project-card-']").first();
    if (await row.count()) {
      await row.click();
      await expect(page).toHaveURL(/\/projects\//, { timeout: 20_000 });
      await expect(page.locator("body")).toContainText(/Overzicht|Plan|Offerte|Contract|Factuur|Overview|Proposal|Invoice|Tasks|Taken/i);
    }

    // Operations (owner)
    await page.goto("/settings?tab=operations", { waitUntil: "domcontentloaded" });
    const opsTab = page.getByTestId("settings-tab-operations");
    if (await opsTab.count()) {
      await opsTab.click();
      await expect(page.locator("body")).toContainText(/Operations|Operaties|Worker|Scheduler|AI/i, { timeout: 15_000 });
    }

    // Switch to English
    await page.goto("/settings?tab=language", { waitUntil: "domcontentloaded" });
    await page.getByTestId("settings-tab-language").click().catch(() => {});
    await expect(page.getByTestId("language-options")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("language-option-en").click();

    const enChecks = [
      ["/dashboard", /attention|happening|Dashboard/i],
      ["/clients", /Clients/i],
      ["/projects", /Projects/i],
      ["/tasks", /Tasks/i],
      ["/ai-chat", /Copilot|assistant|daily work/i],
      ["/settings", /Settings/i],
    ];
    for (const [path, re] of enChecks) {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      await dismissTourIfPresent(page);
      await expect(page.locator("body")).toContainText(re, { timeout: 20_000 });
    }

    await page.reload({ waitUntil: "domcontentloaded" });
    const stored = await page.evaluate(() => localStorage.getItem("assistify_locale"));
    expect(stored).toBe("en");
    await page.goto("/clients", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("page-intro-title")).toContainText(/Clients/i);

    await context.close();
  });
});
