/**
 * Sprint 31 — Light marketing homepage journey.
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

test.describe("Sprint 31 marketing light redesign", () => {
  test.beforeAll(async ({ request }) => {
    const ok = await apiReachable(request);
    test.skip(!ok, `Backend not reachable at ${API}`);
  });

  test("NL light homepage → sections → EN switch persists", async ({ browser }) => {
    test.setTimeout(180_000);
    const context = await browser.newContext({ locale: "nl-NL" });
    const page = await context.newPage();

    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 30_000 });
    await expect(page.getByTestId("marketing-home")).toBeVisible({ timeout: 20_000 });

    // Light surface: off-white / not pure black body chrome
    const bg = await page.locator('[data-testid="marketing-home"]').evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(bg).not.toMatch(/^rgb\(0,\s*0,\s*0\)$/);

    await expect(page.getByTestId("marketing-hero")).toBeVisible();
    await expect(page.locator("body")).toContainText(/Wat is Assistify|Eén werkplek|Aan de slag/i);
    await expect(page.getByTestId("what-is-assistify")).toBeVisible();
    await expect(page.getByTestId("without-with")).toBeVisible();
    await expect(page.getByTestId("product-showcase")).toBeVisible();

    await page.getByTestId("hero-cta-secondary").click();
    await expect(page.getByTestId("product-showcase")).toBeInViewport({ timeout: 10_000 });

    await page.getByTestId("showcase-tab-copilot").click();
    await expect(page.getByTestId("showcase-title")).toContainText(/Copilot|nuttig|Ask|Vraag/i);

    await page.getByTestId("pricing-preview").scrollIntoViewIfNeeded();
    await expect(page.getByTestId("pricing-preview")).toContainText(/Starter|Pro|Business/i);
    await expect(page.locator("body")).not.toContainText(/Checkout|Pay now|Stripe/i);

    await page.getByTestId("faq-preview").scrollIntoViewIfNeeded();
    await expect(page.getByTestId("faq-preview")).toBeVisible();

    await page.getByTestId("marketing-lang-en").click();
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.locator("body")).toContainText(/What is Assistify|Get started|One workspace/i);

    await page.reload({ waitUntil: "domcontentloaded" });
    const stored = await page.evaluate(() => localStorage.getItem("assistify_locale"));
    expect(stored).toBe("en");
    await expect(page.getByTestId("what-is-assistify")).toContainText(/What is Assistify/i);

    await context.close();
  });
});
