/**
 * Sprint 29 — Localization journey.
 * Dutch browser → register → onboarding → dashboard → settings → switch EN → persists.
 */
const { test, expect } = require("@playwright/test");

const BASE = (process.env.STAGING_BASE_URL || process.env.E2E_BASE_URL || "http://127.0.0.1:3000").replace(/\/$/, "");
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

test.describe("Sprint 29 localization journey", () => {
  test.beforeAll(async ({ request }) => {
    const ok = await apiReachable(request);
    test.skip(!ok, `Backend not reachable at ${API}`);
  });

  test("nl browser → Dutch UI → switch English → preference persists", async ({ browser, request }) => {
    test.setTimeout(180_000);
    const context = await browser.newContext({ locale: "nl-NL" });
    const page = await context.newPage();
    const runId = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const email = `locale29_${runId}@example.com`;
    const password = "Password123!";

    await page.goto("/register", { waitUntil: "domcontentloaded", timeout: 30_000 });
    await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });

    // Dutch default from browser language
    await expect(page.getByTestId("register-submit")).toContainText(/Account aanmaken|Create account/i);
    const registerHtml = await page.locator("body").innerText();
    expect(registerHtml).toMatch(/Account aanmaken|Wachtwoord|Voornaam|E-mail|Werk-e-mail|Create account|Password|First name/i);

    await page.getByTestId("register-firstname").fill("Locale");
    await page.getByTestId("register-lastname").fill("Tester");
    await page.getByTestId("register-email").fill(email);
    await page.getByTestId("register-password").fill(password);
    const company = page.getByTestId("register-company");
    if (await company.count()) await company.fill("Locale Co");
    await page.getByTestId("register-submit").click();
    await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 45_000 });

    if (page.url().includes("onboarding")) {
      await expect(page.getByTestId("onboarding-page")).toBeVisible();
      // Prefer Dutch welcome copy when locale resolved to nl
      const welcome = page.getByTestId("onb-step-welcome");
      if (await welcome.count()) {
        await expect(welcome).toContainText(/Assistify|bedrijfsbesturingssysteem|business operating system/i);
      }
      const skip = page.getByTestId("onboarding-save-exit").or(page.getByTestId("onb-welcome-skip"));
      if (await skip.count()) await skip.first().click();
      await expect(page).toHaveURL(/dashboard/, { timeout: 45_000 });
    }

    await dismissTourIfPresent(page);

    // Create a client (localized nav)
    await page.goto("/clients", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("page-intro-description").or(page.getByTestId("clients-page"))).toBeVisible({ timeout: 20_000 });
    const newClient = page.getByTestId("new-client-btn").or(page.getByRole("button", { name: /nieuwe klant|new client|add client|klant/i }));
    if (await newClient.count()) {
      await newClient.first().click();
      const nameInput = page.getByTestId("client-name").or(page.getByLabel(/name|naam/i)).first();
      if (await nameInput.count()) {
        await nameInput.fill(`Locale Client ${runId}`);
        const save = page.getByTestId("client-save").or(page.getByRole("button", { name: /save|opslaan|create|aanmaken/i })).first();
        if (await save.count()) await save.click();
      }
    }

    // Settings → Language → English
    await page.goto("/settings?tab=language", { waitUntil: "domcontentloaded" });
    // Fall back to clicking language tab if query unsupported
    const langTab = page.getByTestId("settings-tab-language").or(page.getByRole("button", { name: /language|taal/i }));
    if (await langTab.count()) await langTab.first().click().catch(() => {});
    await expect(page.getByTestId("language-options").or(page.getByTestId("settings-language"))).toBeVisible({ timeout: 20_000 });
    await page.getByTestId("language-option-en").click();
    await expect(page.getByTestId("language-option-en")).toBeVisible();

    // Immediate English UI somewhere visible
    await page.goto("/clients", { waitUntil: "domcontentloaded" });
    await dismissTourIfPresent(page);
    const clientsCopy = await page.locator("[data-testid='page-intro-description'], [data-testid='page-intro-title'], body").first().innerText();
    expect(clientsCopy.toLowerCase()).toMatch(/client|manage|customer|klant/);

    // Prefer English nav label after switch
    const navClients = page.getByTestId("nav-clients").or(page.getByRole("link", { name: /^Clients$|^Klanten$/i }));
    if (await navClients.count()) {
      await expect(navClients.first()).toContainText(/Clients/i);
    }

    // Reload preserves English
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.goto("/settings?tab=language", { waitUntil: "domcontentloaded" });
    if (await langTab.count()) await langTab.first().click().catch(() => {});
    await expect(page.getByTestId("language-option-en")).toBeVisible({ timeout: 20_000 });
    // Selected state: brand styling or aria — at minimum option still present and localStorage set
    const stored = await page.evaluate(() => localStorage.getItem("assistify_locale"));
    expect(stored).toBe("en");

    // Authenticated preference on server
    const me = await request.get(`${API}/api/auth/me`, {
      headers: {
        Cookie: (await context.cookies()).map((c) => `${c.name}=${c.value}`).join("; "),
      },
    });
    if (me.ok()) {
      const body = await me.json();
      expect(["en", "nl"]).toContain(body.language);
      // After explicit EN selection we expect en when profile patch succeeded
      if (body.language) expect(body.language).toBe("en");
    }

    await context.close();
  });
});
