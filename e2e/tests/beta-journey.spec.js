/**
 * Sprint 28 — Closed beta journey.
 * Cookie-only auth. No invented PASS for AI when the provider is unavailable.
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

async function dismissTourIfPresent(page) {
  const skip = page.getByTestId("product-tour-skip").or(page.getByRole("button", { name: /skip|got it|close tour/i }));
  if (await skip.count()) {
    await skip.first().click().catch(() => {});
  }
}

test.describe("Sprint 28 beta journey", () => {
  test.beforeAll(async ({ request }) => {
    const ok = await apiReachable(request);
    test.skip(!ok, `Backend not reachable at ${API}`);
  });

  test("register → onboarding → CRUD → feedback → dashboard → logout/login persistence", async ({
    page,
    context,
    request,
  }) => {
    test.setTimeout(180_000);
    const runId = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const email = `beta28_${runId}@example.com`;
    const password = "Password123!";
    const clientName = `Beta Client ${runId}`;
    const projectName = `Beta Project ${runId}`;
    const taskTitle = `Beta Task ${runId}`;

    // Public config: beta + no secrets
    const pub = await request.get(`${API}/api/config/public`);
    expect(pub.ok()).toBeTruthy();
    const pubBody = await pub.json();
    expect(pubBody.billingEnabled).toBeFalsy();
    expect(pubBody.demoLoginEnabled).toBeFalsy();
    const pubText = JSON.stringify(pubBody);
    expect(pubText).not.toMatch(/sk-/);
    expect(pubText.toLowerCase()).not.toContain("jwt_secret");

    await page.goto("/register", { waitUntil: "domcontentloaded", timeout: 30_000 });
    await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
    await page.getByTestId("register-firstname").fill("Beta");
    await page.getByTestId("register-lastname").fill("User");
    await page.getByTestId("register-email").fill(email);
    await page.getByTestId("register-password").fill(password);
    const company = page.getByTestId("register-company");
    if (await company.count()) await company.fill("Beta Co");
    await page.getByTestId("register-submit").click();
    await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 45_000 });
    await assertNoStoredJwt(page);

    if (page.url().includes("onboarding")) {
      await page.request
        .post(`${API}/api/onboarding/complete`, { headers: await csrfHeaders(context), timeout: 15_000 })
        .catch(() => {});
      await page.goto("/dashboard");
    }
    await dismissTourIfPresent(page);

    // First-run empty state — no fake Northwind metrics required
    await expect(page.getByTestId("dashboard-page").or(page.getByTestId("dashboard-first-run")).first()).toBeVisible({ timeout: 20_000 });

    // Create client
    await page.goto("/clients");
    await dismissTourIfPresent(page);
    const newClient = page.getByTestId("new-client-btn").or(page.getByRole("button", { name: /new client|add client|create/i }));
    if (await newClient.count()) {
      await newClient.first().click();
      const nameInput = page.getByTestId("client-name").or(page.getByLabel(/name/i)).first();
      await nameInput.fill(clientName);
      const save = page.getByTestId("client-save").or(page.getByRole("button", { name: /save|create|add/i })).first();
      await save.click();
    } else {
      // API fallback
      await page.request.post(`${API}/api/clients`, {
        headers: { ...(await csrfHeaders(context)), "Content-Type": "application/json" },
        data: { name: clientName, email: `c_${runId}@example.com` },
      });
      await page.reload();
    }
    await expect(page.getByText(clientName).first()).toBeVisible({ timeout: 20_000 });

    // Create project
    const clients = await page.request.get(`${API}/api/clients`, { headers: await csrfHeaders(context) });
    const clientList = await clients.json();
    const client = (Array.isArray(clientList) ? clientList : []).find((c) => c.name === clientName) || clientList[0];
    const projRes = await page.request.post(`${API}/api/projects`, {
      headers: { ...(await csrfHeaders(context)), "Content-Type": "application/json" },
      data: { name: projectName, client_id: client?.id, status: "In Progress" },
    });
    expect(projRes.ok()).toBeTruthy();
    const project = await projRes.json();

    // Create task
    const taskRes = await page.request.post(`${API}/api/tasks`, {
      headers: { ...(await csrfHeaders(context)), "Content-Type": "application/json" },
      data: { title: taskTitle, project_id: project.id, priority: "Medium" },
    });
    expect(taskRes.ok()).toBeTruthy();

    // Optional AI — separate soft check
    let aiAvailable = false;
    try {
      const aiRes = await page.request.post(`${API}/api/copilot/message`, {
        headers: { ...(await csrfHeaders(context)), "Content-Type": "application/json" },
        data: { message: "Say hello in one short sentence.", session_id: `beta-${runId}` },
        timeout: 45_000,
      });
      if (aiRes.ok()) {
        aiAvailable = true;
        const aiBody = await aiRes.json().catch(() => ({}));
        const blob = JSON.stringify(aiBody);
        expect(blob).not.toMatch(/sk-/);
      } else {
        test.info().annotations.push({ type: "note", description: `AI skipped/unavailable: HTTP ${aiRes.status()}` });
      }
    } catch (e) {
      test.info().annotations.push({ type: "note", description: `AI skipped: ${e.message}` });
    }
    // Do not fail the journey solely because AI provider is down.
    void aiAvailable;

    // Beta feedback (UI if beta mode, else API)
    const feedbackBtn = page.getByTestId("beta-feedback-open");
    if (await feedbackBtn.count()) {
      await feedbackBtn.click();
      await expect(page.getByTestId("beta-feedback-modal")).toBeVisible();
      await page.getByTestId("beta-feedback-cat-idea").click();
      await page.getByTestId("beta-feedback-message").fill("Beta journey feedback — dashboard feels clear.");
      await page.getByTestId("beta-feedback-submit").click();
      await expect(page.getByTestId("beta-feedback-modal")).toBeHidden({ timeout: 15_000 });
    } else {
      const fb = await page.request.post(`${API}/api/feedback`, {
        headers: { ...(await csrfHeaders(context)), "Content-Type": "application/json" },
        data: { category: "Idea", message: "Beta journey feedback via API", page: "/dashboard" },
      });
      expect(fb.ok()).toBeTruthy();
    }

    // Dashboard persistence check
    await page.goto("/dashboard");
    await dismissTourIfPresent(page);

    // Logout / login
    const logout = page.getByTestId("logout-btn");
    if (await logout.count()) {
      await logout.click();
    } else {
      await page.request.post(`${API}/api/auth/logout`, { headers: await csrfHeaders(context) });
      await page.goto("/login");
    }
    await expect(page).toHaveURL(/login/, { timeout: 20_000 });
    await assertNoStoredJwt(page);

    await page.getByTestId("login-email").fill(email);
    await page.getByTestId("login-password").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 45_000 });
    await dismissTourIfPresent(page);

    await page.goto("/clients");
    await expect(page.getByText(clientName).first()).toBeVisible({ timeout: 20_000 });
    await assertNoStoredJwt(page);
  });
});
