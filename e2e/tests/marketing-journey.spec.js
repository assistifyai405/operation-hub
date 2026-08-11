/**
 * Sprint 30 — Public marketing journey.
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

test.describe("Sprint 30 marketing journey", () => {
  test.beforeAll(async ({ request }) => {
    const ok = await apiReachable(request);
    test.skip(!ok, `Backend not reachable at ${API}`);
  });

  test("NL homepage → product → pricing/FAQ/security → EN switch → register", async ({ browser }) => {
    test.setTimeout(180_000);
    const context = await browser.newContext({ locale: "nl-NL" });
    const page = await context.newPage();

    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 30_000 });
    await expect(page.getByTestId("marketing-home")).toBeVisible({ timeout: 20_000 });
    await expect(page.locator("body")).toContainText(/Beheer je bedrijf slimmer met AI|Aan de slag/i);

    // Product pages (direct navigation keeps journey stable with sticky nav)
    await page.goto("/product/copilot", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/product\/copilot/, { timeout: 20_000 });
    await expect(page.getByTestId("marketing-product-copilot")).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("body")).toContainText(/Copilot|assistent|AI/i);

    // Module cards exist on homepage
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("marketing-modules")).toBeVisible();
    await expect(page.locator('a[href="/product/copilot"]').first()).toHaveCount(1);

    await page.goto("/pricing", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("marketing-pricing")).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("body")).not.toContainText(/Checkout|Pay now|Stripe/i);
    await expect(page.locator("body")).toContainText(/beta|Beta|aan de slag|Join|Starter|Pro|Business/i);

    await page.goto("/faq", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("marketing-faq")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("marketing-faq")).toContainText(/Assistify|FAQ|Veelgestelde/i);

    await page.goto("/security", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("marketing-security")).toBeVisible({ timeout: 15_000 });
    const securityText = await page.locator("body").innerText();
    expect(securityText).not.toMatch(/SOC 2|ISO 27001|HIPAA certified/i);

    // Switch to English
    const langEn = page.getByTestId("marketing-lang-en").or(page.getByTestId("marketing-footer-lang-en"));
    await expect(langEn.first()).toBeVisible({ timeout: 10_000 });
    await langEn.first().click();
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.locator("body")).toContainText(/Run your business with AI|Get started/i);

    await page.reload({ waitUntil: "domcontentloaded" });
    const stored = await page.evaluate(() => localStorage.getItem("assistify_locale"));
    expect(stored).toBe("en");
    await expect(page.locator("body")).toContainText(/Run your business with AI|Get started/i);

    // Unauthenticated public pages work
    await page.goto("/product", { waitUntil: "domcontentloaded" });
    await expect(page.locator("body")).toContainText(/Product|Copilot|CRM|Assistify/i);

    // Register CTA
    const registerCta = page.getByTestId("marketing-cta-primary").or(page.locator('a[href="/register"]')).first();
    await registerCta.click();
    await expect(page).toHaveURL(/register/, { timeout: 20_000 });
    await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 15_000 });

    await context.close();
  });

  test("English browser defaults to English homepage", async ({ browser }) => {
    const context = await browser.newContext({ locale: "en-US" });
    const page = await context.newPage();
    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 30_000 });
    await expect(page.locator("body")).toContainText(/Run your business with AI|Get started/i);
    await context.close();
  });
});
