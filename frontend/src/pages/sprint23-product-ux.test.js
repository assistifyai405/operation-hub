/**
 * Sprint 23 — first-run UX static guards (no Testing Library).
 * @jest-environment node
 */
const fs = require("fs");
const path = require("path");

const read = (rel) => fs.readFileSync(path.join(__dirname, rel), "utf8");

describe("Sprint 23 onboarding flow", () => {
  const onboarding = read("Onboarding.jsx");
  const welcome = read("../components/onboarding/StepWelcome.jsx");
  const goal = read("../components/onboarding/StepGoal.jsx");
  const ready = read("../components/onboarding/StepReady.jsx");

  test("uses a 5-step welcome → company → goal → first actions → ready flow", () => {
    expect(onboarding).toMatch(/StepWelcome/);
    expect(onboarding).toMatch(/StepCompany/);
    expect(onboarding).toMatch(/StepGoal/);
    expect(onboarding).toMatch(/StepFirstActions/);
    expect(onboarding).toMatch(/StepReady/);
    expect(onboarding).toMatch(/LAST_STEP = 4/);
  });

  test("skip/save-exit marks onboarding complete so returning users are not trapped", () => {
    expect(onboarding).toMatch(/markComplete/);
    expect(onboarding).toMatch(/onboardingApi\.complete/);
    expect(onboarding).toMatch(/onboarding\.skip|onboarding-save-exit/);
    expect(onboarding).toMatch(/user\?\.onboardingCompleted/);
  });

  test("welcome explains the product clearly", () => {
    expect(welcome).toMatch(/onboarding\.welcomeHeadline/);
    expect(welcome).toMatch(/onboarding\.capabilities\.\$\{key\}/);
    expect(welcome).toMatch(/capabilities/);
    const en = JSON.parse(read("../i18n/locales/en.json"));
    expect(en.onboarding.welcomeHeadline).toMatch(/Welcome to Assistify/);
    expect(en.onboarding.welcomeBody).toMatch(/clients, projects, tasks, documents and AI/);
    expect(en.onboarding.capabilities.clients).toMatch(/Clients/);
    expect(en.onboarding.capabilities.projects).toMatch(/Projects/);
    expect(en.onboarding.capabilities.ai).toMatch(/AI/);
  });

  test("goal step persists a primary goal choice", () => {
    expect(goal).toMatch(/primaryGoal/);
    expect(goal).toMatch(/win_clients/);
    expect(goal).toMatch(/save_time_ai/);
    expect(ready).toMatch(/NEXT_BY_GOAL/);
  });
});

describe("Sprint 23 dashboard first-run", () => {
  const dashboard = read("Dashboard.jsx");
  const firstRun = read("../components/dashboard/DashboardFirstRun.jsx");
  const checklist = read("../components/OnboardingChecklist.jsx");

  test("empty workspace shows first-run panel instead of fake KPI dashboards", () => {
    expect(dashboard).toMatch(/DashboardFirstRun/);
    expect(dashboard).toMatch(/workspaceEmpty/);
    expect(dashboard).toMatch(/workspace_empty/);
    expect(firstRun).toMatch(/firstRun\.title|get your workspace working for you/);
    expect(firstRun).toMatch(/firstRun\.body|no sample charts or fake scores/i);
    const en = JSON.parse(read("../i18n/locales/en.json"));
    expect(en.firstRun.title).toMatch(/workspace working for you/);
    expect(en.firstRun.body).toMatch(/no sample charts or fake scores/i);
  });

  test("morning brief does not auto-open on empty workspace", () => {
    expect(dashboard).toMatch(/if \(data\.workspace_empty\) return/);
  });

  test("checklist wording is workspace-oriented and uses real API progress", () => {
    expect(checklist).toMatch(/onboarding\.checklist\.title|Getting started/);
    expect(checklist).not.toMatch(/AI employee/);
    expect(checklist).toMatch(/dismissChecklist/);
    expect(checklist).toMatch(/\.checklist\(\)/);
    const en = JSON.parse(read("../i18n/locales/en.json"));
    expect(en.onboarding.checklist.title).toMatch(/Getting started/);
  });
});

describe("Sprint 23 empty states and CTAs", () => {
  test("major pages explain what/why/next", () => {
    expect(read("Clients.jsx")).toMatch(/clients-empty/);
    expect(read("Projects.jsx")).toMatch(/projects\.empty\.action/);
    expect(read("Tasks.jsx")).toMatch(/tasks\.empty\.action/);
    expect(read("CRM.jsx")).toMatch(/crm-empty/);
    expect(read("Pipeline.jsx")).toMatch(/pipeline-empty/);
    expect(read("Opportunities.jsx")).toMatch(/opportunities-empty/);
    expect(read("Automations.jsx")).toMatch(/automations-empty/);
    expect(read("AIWorkspace.jsx")).toMatch(/ai-workspace-timeline-empty/);
    expect(read("AICopilot.jsx")).toMatch(/copilot-empty/);
  });

  test("AI Agents custom creation is hidden (no dead New Agent CTA)", () => {
    const agents = read("AIAgents.jsx");
    expect(agents).not.toMatch(/new-agent-btn/);
    expect(agents).toMatch(/custom-agents-note/);
  });

  test("landing/auth copy avoids fake trial language", () => {
    const login = read("Login.jsx");
    const shell = read("../components/AuthShell.jsx");
    const en = JSON.parse(read("../i18n/locales/en.json"));
    expect(login).not.toMatch(/Start free trial/);
    expect(login).toMatch(/t\("auth\.createAccount"\)/);
    expect(en.auth.createAccount).toMatch(/Create (an )?account/);
    expect(shell).toMatch(/t\("auth\.heroTitle"\)/);
    expect(en.auth.heroTitle).toMatch(/AI-powered business operating system/);
  });

  test("billing remains setup-pending without fake upgrade when disabled", () => {
    const layout = read("../components/Layout.jsx");
    const en = JSON.parse(read("../i18n/locales/en.json"));
    expect(layout).toMatch(/t\("billing\.notAvailable"\)/);
    expect(en.billing.notAvailable).toMatch(/Billing is not available during beta/);
    expect(layout).toMatch(/sidebar-billing-pending/);
  });
});

describe("Sprint 23 analytics foundation", () => {
  test("analytics module exposes product events without logging secrets", () => {
    const analytics = read("../lib/analytics.js");
    expect(analytics).toMatch(/user_registered/);
    expect(analytics).toMatch(/onboarding_completed/);
    expect(analytics).toMatch(/client_created/);
    expect(analytics).toMatch(/copilot_used/);
    expect(analytics).toMatch(/FORBIDDEN_KEYS/);
    expect(analytics).toMatch(/No paid provider yet/);
    expect(analytics).toMatch(/setAnalyticsSink/);
  });
});
