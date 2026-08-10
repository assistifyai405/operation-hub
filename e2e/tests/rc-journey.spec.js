/**
 * Sprint 25 — Release Candidate browser journey.
 * Cookie-only auth. No API keys in fixtures.
 * External AI generate steps are soft when the provider rejects the key.
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

test.describe("Sprint 25 RC journey", () => {
  test.beforeAll(async ({ request }) => {
    const ok = await apiReachable(request);
    test.skip(!ok, `Backend not reachable at ${API}`);
  });

  test("register → onboarding → CRUD → workspace AI tabs → agents → copilot → logout/login persistence", async ({
    page,
    context,
  }) => {
    test.setTimeout(180_000);
    const runId = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const email = `rc25_${runId}@example.com`;
    const password = "Password123!";
    const clientName = `RC Client ${runId}`;
    const projectName = `RC Project ${runId}`;
    const taskTitle = `RC Task ${runId}`;

    await page.goto("/register", { waitUntil: "domcontentloaded", timeout: 30_000 });
    await expect(page.getByTestId("register-form")).toBeVisible({ timeout: 20_000 });
    await page.getByTestId("register-firstname").fill("RC");
    await page.getByTestId("register-lastname").fill("User");
    await page.getByTestId("register-email").fill(email);
    await page.getByTestId("register-password").fill(password);
    const company = page.getByTestId("register-company");
    if (await company.count()) await company.fill("RC Co");
    await page.getByTestId("register-submit").click();
    await expect(page).toHaveURL(/dashboard|onboarding/, { timeout: 45_000 });
    await assertNoStoredJwt(page);

    if (page.url().includes("onboarding")) {
      const skip = page.getByTestId("onboarding-skip").or(page.getByRole("button", { name: /skip|get started|finish|continue/i }));
      if (await skip.count()) {
        // Prefer completing via API for reliability, then land on dashboard
        await page.request
          .post(`${API}/api/onboarding/complete`, { headers: await csrfHeaders(context), timeout: 15_000 })
          .catch(() => {});
        await page.goto("/dashboard");
      }
    }

    await dismissTourIfPresent(page);
    await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 30_000 });

    // Create client
    await page.goto("/clients");
    await expect(page.getByTestId("clients-page")).toBeVisible();
    await page.getByTestId("add-client-btn").click();
    await page.getByTestId("client-name-input").fill(clientName);
    await page.getByTestId("client-contact-input").fill("Pat");
    await page.getByTestId("client-email-input").fill(`pat_${runId}@rc.test`);
    await page.getByTestId("client-save-btn").click();
    await expect(page.getByText(clientName)).toBeVisible({ timeout: 15_000 });

    // Create project
    await page.goto("/projects");
    await expect(page.getByTestId("projects-page")).toBeVisible();
    await page.getByTestId("new-project-btn").click();
    await page.getByTestId("project-name-input").fill(projectName);
    // Link client if selector exists
    const clientSelect = page.getByTestId("project-client-select");
    if (await clientSelect.count()) {
      await clientSelect.click();
      const option = page.getByRole("option", { name: clientName });
      if (await option.count()) await option.click();
      else await page.keyboard.press("Escape");
    }
    await page.getByTestId("project-save-btn").click();
    await expect(page.getByText(projectName)).toBeVisible({ timeout: 15_000 });

    // Create task
    await page.goto("/tasks");
    await expect(page.getByTestId("tasks-page")).toBeVisible();
    await page.getByTestId("add-task-btn").click();
    await page.getByTestId("task-title-input").fill(taskTitle);
    await page.getByTestId("task-save-btn").click();
    await expect(page.getByText(taskTitle)).toBeVisible({ timeout: 15_000 });

    // Open project workspace — resolve id via API
    const projectsRes = await page.request.get(`${API}/api/projects`);
    expect(projectsRes.ok()).toBeTruthy();
    const projects = await projectsRes.json();
    const plist = Array.isArray(projects) ? projects : projects.items || projects.projects || [];
    const project = plist.find((p) => p.name === projectName);
    expect(project?.id).toBeTruthy();
    const pid = project.id;

    await page.goto(`/projects/${pid}`);
    await expect(page.locator("body")).not.toContainText("Something went wrong");

    // Walk primary workspace tabs (route + no crash)
    const tabs = [
      { q: "overview", testid: null },
      { q: "plan", testid: "generate-plan-btn" },
      { q: "proposal", testid: "generate-proposal-btn" },
      { q: "contract", testid: "generate-contract-btn" },
      { q: "invoice", testid: "generate-invoice-btn" },
      { q: "tasks", testid: null },
      { q: "documents", testid: null },
      { q: "notes", testid: null },
      { q: "activity", testid: null },
    ];
    for (const tab of tabs) {
      await page.goto(`/projects/${pid}?tab=${tab.q}`);
      await expect(page.locator("body")).not.toContainText("Something went wrong");
      if (tab.testid) {
        const btn = page.getByTestId(tab.testid);
        if (await btn.count()) {
          await expect(btn.first()).toBeVisible({ timeout: 10_000 });
          // Soft-click generate once — success or graceful toast; never leak keys in UI
          await btn.first().click();
          await page.waitForTimeout(2500);
          const bodyText = await page.locator("body").innerText();
          expect(bodyText.toLowerCase()).not.toContain("sk-");
          expect(bodyText.toLowerCase()).not.toContain("incorrect api key");
        }
      }
    }

    // AI Agents + Copilot
    await page.goto("/ai-agents");
    await expect(page.getByTestId("ai-agents-page")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("new-agent-btn")).toHaveCount(0);

    await page.goto("/ai-chat");
    await expect(page.getByTestId("copilot-page")).toBeVisible({ timeout: 20_000 });

    await page.goto("/opportunities");
    await expect(page.getByTestId("opportunities-page")).toBeVisible({ timeout: 20_000 });

    await page.goto("/dashboard");
    await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 20_000 });

    // Refresh persistence
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("dashboard-page")).toBeVisible({ timeout: 30_000 });
    await page.goto("/clients");
    await expect(page.getByText(clientName)).toBeVisible({ timeout: 15_000 });
    await page.goto("/projects");
    await expect(page.getByText(projectName)).toBeVisible({ timeout: 15_000 });

    // Logout → login → persistence
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

    await page.goto("/clients");
    await expect(page.getByText(clientName)).toBeVisible({ timeout: 15_000 });
    await page.goto("/projects");
    await expect(page.getByText(projectName)).toBeVisible({ timeout: 15_000 });

    test.info().annotations.push({ type: "env", description: `rc:${BASE}` });
  });
});
