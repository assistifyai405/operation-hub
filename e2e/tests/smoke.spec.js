/**
 * Highest-value browser smoke — local docker/compose or external staging.
 *
 * Env:
 *   STAGING_BASE_URL  optional alias for frontend origin (staging)
 *   E2E_BASE_URL      frontend origin (default http://127.0.0.1:3000)
 *   E2E_API_URL       backend origin (default http://127.0.0.1:8000)
 *
 * Frontend must be built with REACT_APP_BACKEND_URL matching E2E_API_URL.
 * Auth is cookie-only — tests must not rely on localStorage JWTs.
 */
const { test, expect } = require("@playwright/test");

const BASE = (process.env.STAGING_BASE_URL || process.env.E2E_BASE_URL || "http://127.0.0.1:3000").replace(/\/$/, "");
const API = (process.env.E2E_API_URL || process.env.STAGING_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function apiReachable(request) {
  try {
    const r = await request.get(`${API}/api/health/live`, { timeout: 5000 });
    return r.ok();
  } catch {
    return false;
  }
}

async function assertNoStoredJwt(page) {
  const stored = await page.evaluate(() => ({
    local: localStorage.getItem("assistify_token"),
    session: sessionStorage.getItem("assistify_token"),
  }));
  expect(stored.local).toBeNull();
  expect(stored.session).toBeNull();
}

test.describe("Assistify OS smoke", () => {
  test.beforeAll(async ({ request }) => {
    const ok = await apiReachable(request);
    test.skip(!ok, `Backend not reachable at ${API} — start the stack or set STAGING_BASE_URL/E2E_API_URL`);
  });

  test("live + ready + alerts health endpoints", async ({ request }) => {
    const live = await request.get(`${API}/api/health/live`);
    expect(live.ok()).toBeTruthy();
    const body = await live.json();
    expect(body.check).toBe("live");

    const ready = await request.get(`${API}/api/health/ready`);
    expect([200, 503]).toContain(ready.status());
    const readyBody = await ready.json();
    expect(readyBody.check).toBe("ready");
    expect(readyBody.checks.mongodb).toBeTruthy();

    const alerts = await request.get(`${API}/api/health/alerts`);
    expect([200, 503]).toContain(alerts.status());
    const alertsBody = await alerts.json();
    expect(Array.isArray(alertsBody.alerts)).toBeTruthy();
  });

  test("register → session reload → dashboard CRUD → agents → settings → logout → login", async ({ page, context, request }) => {
    const email = `e2e_${Date.now()}@example.com`;
    const password = "Password123!";

    await page.goto(`${BASE}/register`);
    // Prefer UI register when present; otherwise API register + UI login
    const hasRegister = await page.getByTestId("register-form").count();
    if (hasRegister) {
      await page.getByTestId("register-firstname").or(page.locator('input[name="firstName"]')).first().fill("E2E");
      await page.getByTestId("register-lastname").or(page.locator('input[name="lastName"]')).first().fill("User");
      await page.getByTestId("register-email").or(page.locator('input[type="email"]')).first().fill(email);
      await page.getByTestId("register-password").or(page.locator('input[type="password"]')).first().fill(password);
      const company = page.getByTestId("register-company").or(page.locator('input[name="company"]'));
      if (await company.count()) await company.first().fill("E2E Co");
      await page.getByTestId("register-submit").or(page.getByRole("button", { name: /create|sign up|register/i })).first().click();
      await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 45_000 });
    } else {
      const reg = await request.post(`${API}/api/auth/register`, {
        data: {
          firstName: "E2E",
          lastName: "User",
          email,
          password,
          company: "E2E Co",
        },
      });
      expect(reg.ok(), await reg.text()).toBeTruthy();
      const regBody = await reg.json();
      expect(regBody.accessToken).toBeUndefined();

      await page.goto(`${BASE}/login`);
      await expect(page.getByTestId("login-form")).toBeVisible();
      await page.getByTestId("login-email").fill(email);
      await page.getByTestId("login-password").fill(password);
      await page.getByTestId("login-submit").click();
      await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 30_000 });
    }

    await assertNoStoredJwt(page);

    // Complete onboarding via cookie session (no localStorage token)
    if (page.url().includes("onboarding")) {
      const cookies = await context.cookies();
      const csrf = cookies.find((c) => c.name === "csrf_token")?.value;
      await page.request
        .post(`${API}/api/onboarding/complete`, {
          headers: csrf ? { "X-CSRF-Token": csrf } : {},
        })
        .catch(() => {});
      await page.goto(`${BASE}/dashboard`);
    }

    // Session persists after reload
    await page.reload();
    await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 30_000 });
    if (page.url().includes("onboarding")) {
      await page.goto(`${BASE}/dashboard`);
    }
    await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 30_000 });
    await assertNoStoredJwt(page);

    // Clients
    await page.goto(`${BASE}/clients`);
    await expect(page.getByTestId("clients-page")).toBeVisible();
    await page.getByTestId("add-client-btn").click();
    await page.getByTestId("client-name-input").fill("E2E Client");
    await page.getByTestId("client-contact-input").fill("Pat");
    await page.getByTestId("client-email-input").fill("pat@e2e.test");
    await page.getByTestId("client-save-btn").click();
    await expect(page.getByText("E2E Client")).toBeVisible({ timeout: 15_000 });

    // Projects
    await page.goto(`${BASE}/projects`);
    await expect(page.getByTestId("projects-page")).toBeVisible();
    await page.getByTestId("new-project-btn").click();
    await page.getByTestId("project-name-input").fill("E2E Project");
    await page.getByTestId("project-save-btn").click();
    await expect(page.getByText("E2E Project")).toBeVisible({ timeout: 15_000 });

    // Tasks
    await page.goto(`${BASE}/tasks`);
    await expect(page.getByTestId("tasks-page")).toBeVisible();
    await page.getByTestId("add-task-btn").click();
    await page.getByTestId("task-title-input").fill("E2E Task");
    await page.getByTestId("task-save-btn").click();
    await expect(page.getByText("E2E Task")).toBeVisible({ timeout: 15_000 });

    await page.goto(`${BASE}/ai-agents`);
    await expect(page.getByTestId("ai-agents-page")).toBeVisible();

    await page.goto(`${BASE}/ai-chat`);
    await expect(page.getByTestId("copilot-page")).toBeVisible({ timeout: 15_000 });

    await page.goto(`${BASE}/settings`);
    await expect(page.getByTestId("settings-page")).toBeVisible({ timeout: 15_000 });

    for (const path of ["/dashboard", "/clients", "/projects", "/tasks", "/documents", "/analytics"]) {
      await page.goto(`${BASE}${path}`);
      await expect(page.locator("body")).not.toContainText("Something went wrong");
    }

    // Logout
    const logoutItem = page.getByTestId("logout-btn").or(page.getByText("Log out")).or(page.getByText("Sign out"));
    if (await logoutItem.count()) {
      const avatar = page.getByTestId("user-menu").or(page.locator('[data-testid="avatar-menu"]'));
      if (await avatar.count()) await avatar.first().click();
      await logoutItem.first().click().catch(() => {});
    } else {
      await page.request.post(`${API}/api/auth/logout`).catch(() => {});
      await context.clearCookies();
    }

    await page.goto(`${BASE}/login`);
    await expect(page.getByTestId("login-form")).toBeVisible({ timeout: 15_000 });
    await assertNoStoredJwt(page);

    // Login again
    await page.getByTestId("login-email").fill(email);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 30_000 });
    await assertNoStoredJwt(page);
  });
});
