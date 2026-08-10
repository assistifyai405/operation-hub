/**
 * Highest-value browser smoke — local stack OR external staging.
 *
 * Env:
 *   STAGING_BASE_URL  frontend origin for real staging (https://…)
 *   E2E_BASE_URL      frontend origin (default http://127.0.0.1:3000 for local)
 *   E2E_API_URL       backend origin (default http://127.0.0.1:8000 for local)
 *   STAGING_API_URL   alias for E2E_API_URL
 *
 * Auth is cookie-only — tests must not rely on localStorage JWTs.
 * Unique email per run. Best-effort cleanup of created CRM rows.
 */
const { test, expect } = require("@playwright/test");

const BASE = (process.env.STAGING_BASE_URL || process.env.E2E_BASE_URL || "http://127.0.0.1:3000").replace(/\/$/, "");
const API = (process.env.E2E_API_URL || process.env.STAGING_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const isLocalhost = (url) => /localhost|127\.0\.0\.1/i.test(url);
const isExternalStaging = Boolean(process.env.STAGING_BASE_URL) && !isLocalhost(process.env.STAGING_BASE_URL);

async function apiReachable(request) {
  try {
    const r = await request.get(`${API}/api/health/live`, { timeout: 8_000 });
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

async function csrfHeaders(context) {
  const cookies = await context.cookies();
  const csrf = cookies.find((c) => c.name === "csrf_token")?.value;
  return csrf ? { "X-CSRF-Token": csrf } : {};
}

test.describe("Assistify OS smoke", () => {
  test.beforeAll(async ({ request }) => {
    const ok = await apiReachable(request);
    test.skip(!ok, `Backend not reachable at ${API} — start the stack or set STAGING_BASE_URL/E2E_API_URL`);
  });

  test("live + ready + alerts health endpoints", async ({ request }) => {
    const live = await request.get(`${API}/api/health/live`, { timeout: 15_000 });
    expect(live.ok()).toBeTruthy();
    const body = await live.json();
    expect(body.check).toBe("live");

    const ready = await request.get(`${API}/api/health/ready`, { timeout: 15_000 });
    expect([200, 503]).toContain(ready.status());
    const readyBody = await ready.json();
    expect(readyBody.check).toBe("ready");
    expect(readyBody.checks.mongodb).toBeTruthy();

    // On external staging we expect ready to be green
    if (isExternalStaging) {
      expect(ready.status(), "staging ready must be 200").toBe(200);
    }

    const alerts = await request.get(`${API}/api/health/alerts`, { timeout: 15_000 });
    expect([200, 503]).toContain(alerts.status());
    const alertsBody = await alerts.json();
    expect(Array.isArray(alertsBody.alerts)).toBeTruthy();

    const pub = await request.get(`${API}/api/config/public`, { timeout: 15_000 });
    expect(pub.ok()).toBeTruthy();
    const cfg = await pub.json();
    expect(cfg.billingEnabled).toBeFalsy();
    if (isExternalStaging) {
      expect(cfg.demoLoginEnabled).toBeFalsy();
      expect(cfg.demoSeedEnabled).toBeFalsy();
    }
  });

  test("register → session reload → dashboard CRUD → agents → settings → logout → login", async ({ page, context }) => {
    test.setTimeout(120_000);
    const runId = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const email = `e2e_${runId}@example.com`;
    const password = "Password123!";
    const clientName = `E2E Client ${runId}`;
    const projectName = `E2E Project ${runId}`;
    const taskTitle = `E2E Task ${runId}`;
    let created = { clientId: null, projectId: null, taskId: null };

    await page.goto("/register", { waitUntil: "domcontentloaded", timeout: 30_000 });
    const hasRegister = await page.getByTestId("register-form").count();
    if (hasRegister) {
      await page.getByTestId("register-firstname").fill("E2E");
      await page.getByTestId("register-lastname").fill("User");
      await page.getByTestId("register-email").fill(email);
      await page.getByTestId("register-password").fill(password);
      const company = page.getByTestId("register-company");
      if (await company.count()) await company.fill("E2E Co");
      await page.getByTestId("register-submit").click();
      await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 45_000 });
    } else {
      // Fallback: API register (cookie jar on request context) + UI login
      const reg = await context.request.post(`${API}/api/auth/register`, {
        data: {
          firstName: "E2E",
          lastName: "User",
          email,
          password,
          company: "E2E Co",
        },
        timeout: 30_000,
      });
      expect(reg.ok(), await reg.text()).toBeTruthy();
      const regBody = await reg.json();
      expect(regBody.accessToken).toBeUndefined();

      await page.goto("/login");
      await expect(page.getByTestId("login-form")).toBeVisible();
      await page.getByTestId("login-email").fill(email);
      await page.getByTestId("login-password").fill(password);
      await page.getByTestId("login-submit").click();
      await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 30_000 });
    }

    await assertNoStoredJwt(page);

    if (page.url().includes("onboarding")) {
      await page.request
        .post(`${API}/api/onboarding/complete`, { headers: await csrfHeaders(context), timeout: 15_000 })
        .catch(() => {});
      await page.goto("/dashboard");
    }

    // Session persists after reload (cookie refresh)
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 30_000 });
    if (page.url().includes("onboarding")) {
      await page.goto("/dashboard");
    }
    await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 30_000 });
    await assertNoStoredJwt(page);

    // Clients
    await page.goto("/clients");
    await expect(page.getByTestId("clients-page")).toBeVisible();
    await page.getByTestId("add-client-btn").click();
    await page.getByTestId("client-name-input").fill(clientName);
    await page.getByTestId("client-contact-input").fill("Pat");
    await page.getByTestId("client-email-input").fill(`pat_${runId}@e2e.test`);
    await page.getByTestId("client-save-btn").click();
    await expect(page.getByText(clientName)).toBeVisible({ timeout: 15_000 });

    // Projects
    await page.goto("/projects");
    await expect(page.getByTestId("projects-page")).toBeVisible();
    await page.getByTestId("new-project-btn").click();
    await page.getByTestId("project-name-input").fill(projectName);
    await page.getByTestId("project-save-btn").click();
    await expect(page.getByText(projectName)).toBeVisible({ timeout: 15_000 });

    // Tasks
    await page.goto("/tasks");
    await expect(page.getByTestId("tasks-page")).toBeVisible();
    await page.getByTestId("add-task-btn").click();
    await page.getByTestId("task-title-input").fill(taskTitle);
    await page.getByTestId("task-save-btn").click();
    await expect(page.getByText(taskTitle)).toBeVisible({ timeout: 15_000 });

    await page.goto("/ai-agents");
    await expect(page.getByTestId("ai-agents-page")).toBeVisible({ timeout: 20_000 });

    await page.goto("/ai-chat");
    await expect(page.getByTestId("copilot-page")).toBeVisible({ timeout: 20_000 });

    await page.goto("/opportunities");
    await expect(page.getByTestId("opportunities-page")).toBeVisible({ timeout: 20_000 });

    await page.goto("/settings");
    await expect(page.getByTestId("settings-page")).toBeVisible({ timeout: 20_000 });

    for (const path of ["/dashboard", "/clients", "/projects", "/tasks"]) {
      await page.goto(path);
      await expect(page.locator("body")).not.toContainText("Something went wrong");
    }

    // Best-effort cleanup via API (safe deletes)
    try {
      const headers = await csrfHeaders(context);
      const clients = await page.request.get(`${API}/api/clients`);
      if (clients.ok()) {
        const list = await clients.json();
        const c = (Array.isArray(list) ? list : []).find((x) => x.name === clientName);
        if (c?.id) {
          created.clientId = c.id;
          await page.request.delete(`${API}/api/clients/${c.id}`, { headers }).catch(() => {});
        }
      }
      const projects = await page.request.get(`${API}/api/projects`);
      if (projects.ok()) {
        const list = await projects.json();
        const p = (Array.isArray(list) ? list : []).find((x) => x.name === projectName);
        if (p?.id) {
          created.projectId = p.id;
          await page.request.delete(`${API}/api/projects/${p.id}`, { headers }).catch(() => {});
        }
      }
      const tasks = await page.request.get(`${API}/api/tasks`);
      if (tasks.ok()) {
        const list = await tasks.json();
        const t = (Array.isArray(list) ? list : []).find((x) => x.title === taskTitle);
        if (t?.id) {
          created.taskId = t.id;
          await page.request.delete(`${API}/api/tasks/${t.id}`, { headers }).catch(() => {});
        }
      }
    } catch {
      /* cleanup is best-effort */
    }

    // Logout
    const logoutItem = page.getByTestId("logout-btn").or(page.getByText("Log out")).or(page.getByText("Sign out"));
    if (await logoutItem.count()) {
      const avatar = page.getByTestId("user-menu");
      if (await avatar.count()) await avatar.first().click();
      await logoutItem.first().click().catch(() => {});
    } else {
      await page.request.post(`${API}/api/auth/logout`, { headers: await csrfHeaders(context) }).catch(() => {});
      await context.clearCookies();
    }

    await page.goto("/login");
    await expect(page.getByTestId("login-form")).toBeVisible({ timeout: 15_000 });
    await assertNoStoredJwt(page);

    await page.getByTestId("login-email").fill(email);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 30_000 });
    await assertNoStoredJwt(page);

    // Annotate run mode for reporters
    test.info().annotations.push({
      type: "env",
      description: isExternalStaging ? `staging:${BASE}` : `local:${BASE}`,
    });
  });
});
