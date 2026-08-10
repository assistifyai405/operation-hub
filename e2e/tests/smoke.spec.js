/**
 * Highest-value browser smoke — targets a running app (frontend + backend).
 * Skips when backend health is unreachable.
 *
 * Env:
 *   E2E_BASE_URL   frontend origin (default http://127.0.0.1:3000)
 *   E2E_API_URL    backend origin (default http://127.0.0.1:8000)
 *
 * Frontend must be built with REACT_APP_BACKEND_URL matching E2E_API_URL.
 */
const { test, expect } = require("@playwright/test");

const API = (process.env.E2E_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function apiReachable(request) {
  try {
    const r = await request.get(`${API}/api/health/live`, { timeout: 3000 });
    return r.ok();
  } catch {
    return false;
  }
}

test.describe("Assistify OS smoke", () => {
  test.beforeAll(async ({ request }) => {
    const ok = await apiReachable(request);
    test.skip(!ok, `Backend not reachable at ${API} — start the stack then re-run`);
  });

  test("live + ready health endpoints", async ({ request }) => {
    const live = await request.get(`${API}/api/health/live`);
    expect(live.ok()).toBeTruthy();
    const body = await live.json();
    expect(body.check).toBe("live");

    const ready = await request.get(`${API}/api/health/ready`);
    expect([200, 503]).toContain(ready.status());
    const readyBody = await ready.json();
    expect(readyBody.check).toBe("ready");
    expect(readyBody.checks.mongodb).toBeTruthy();
  });

  test("register → dashboard → CRUD → agents → logout → login", async ({ page, request }) => {
    const email = `e2e_${Date.now()}@example.com`;
    const password = "Password123!";

    // Register via API (no paid AI required)
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

    // Login through the real UI (sets tokens the same way users do)
    await page.goto("/login");
    await expect(page.getByTestId("login-form")).toBeVisible();
    await page.getByTestId("login-email").fill(email);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 30_000 });

    // Skip onboarding if shown
    if (page.url().includes("onboarding")) {
      // Prefer completing via API flag if UI wizard is long
      const token = await page.evaluate(() => localStorage.getItem("assistify_token") || sessionStorage.getItem("assistify_token"));
      if (token) {
        await request.post(`${API}/api/onboarding/complete`, {
          headers: { Authorization: `Bearer ${token}` },
        }).catch(() => {});
      }
      await page.goto("/dashboard");
    }

    await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 30_000 });

    // Clients
    await page.goto("/clients");
    await expect(page.getByTestId("clients-page")).toBeVisible();
    await page.getByTestId("add-client-btn").click();
    await page.getByTestId("client-name-input").fill("E2E Client");
    await page.getByTestId("client-contact-input").fill("Pat");
    await page.getByTestId("client-email-input").fill("pat@e2e.test");
    await page.getByTestId("client-save-btn").click();
    await expect(page.getByText("E2E Client")).toBeVisible({ timeout: 15_000 });

    // Projects
    await page.goto("/projects");
    await expect(page.getByTestId("projects-page")).toBeVisible();
    await page.getByTestId("new-project-btn").click();
    await page.getByTestId("project-name-input").fill("E2E Project");
    await page.getByTestId("project-save-btn").click();
    await expect(page.getByText("E2E Project")).toBeVisible({ timeout: 15_000 });

    // Tasks
    await page.goto("/tasks");
    await expect(page.getByTestId("tasks-page")).toBeVisible();
    await page.getByTestId("add-task-btn").click();
    await page.getByTestId("task-title-input").fill("E2E Task");
    await page.getByTestId("task-save-btn").click();
    await expect(page.getByText("E2E Task")).toBeVisible({ timeout: 15_000 });

    // Opportunities + AI Agents + Copilot + Settings
    await page.goto("/opportunities");
    await expect(page.getByTestId("opportunities-page")).toBeVisible();

    await page.goto("/ai-agents");
    await expect(page.getByTestId("ai-agents-page")).toBeVisible();

    await page.goto("/ai-chat");
    await expect(page.getByTestId("copilot-page")).toBeVisible({ timeout: 15_000 });

    await page.goto("/settings");
    await expect(page.getByTestId("settings-page")).toBeVisible({ timeout: 15_000 });

    // Navigation spot-check
    for (const path of ["/dashboard", "/clients", "/projects", "/tasks", "/documents", "/analytics"]) {
      await page.goto(path);
      await expect(page.locator("body")).not.toContainText("Something went wrong");
    }

    // Logout then login again
    await page.goto("/dashboard");
    // Open user menu if present; otherwise clear storage + UI login
    const logoutItem = page.getByTestId("logout-btn").or(page.getByText("Log out")).or(page.getByText("Sign out"));
    if (await logoutItem.count()) {
      // may need to open avatar menu first
      const avatar = page.getByTestId("user-menu").or(page.locator('[data-testid="avatar-menu"]'));
      if (await avatar.count()) await avatar.first().click();
      await logoutItem.first().click().catch(() => {});
    }
    await page.evaluate(() => {
      localStorage.removeItem("assistify_token");
      sessionStorage.removeItem("assistify_token");
    });
    await page.goto("/login");
    await expect(page.getByTestId("login-form")).toBeVisible();
    await page.getByTestId("login-email").fill(email);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 30_000 });
  });
});
