/**
 * Sprint 24 — release polish static guards.
 * @jest-environment node
 */
const fs = require("fs");
const path = require("path");

const read = (rel) => fs.readFileSync(path.join(__dirname, rel), "utf8");

describe("Sprint 24 custom agent entry", () => {
  const agents = read("AIAgents.jsx");

  test("hides New Agent creation CTA (no dead clickable entry)", () => {
    expect(agents).not.toMatch(/new-agent-btn/);
    expect(agents).not.toMatch(/>\s*New Agent\s*</);
    expect(agents).toMatch(/custom-agents-note/);
    expect(agents).toMatch(/aiAgents\.customUnavailable/);
    const en = JSON.parse(read("../i18n/locales/en.json"));
    expect(en.aiAgents.customUnavailable).toMatch(/not available in this release/);
  });

  test("agent chat routes through Copilot with a real prompt", () => {
    expect(agents).toMatch(/\/ai-chat\?q=/);
  });
});

describe("Sprint 24 product tour", () => {
  const tour = read("../components/ProductTour.jsx");
  const layout = read("../components/Layout.jsx");

  test("tour is skippable, persisted, and capped at 5 steps", () => {
    expect(tour).toMatch(/product-tour-skip/);
    expect(tour).toMatch(/markProductTourDone/);
    expect(tour).toMatch(/STEPS/);
    const stepCount = (tour.match(/id:\s*"/g) || []).length;
    expect(stepCount).toBeGreaterThanOrEqual(4);
    expect(stepCount).toBeLessThanOrEqual(5);
    expect(read("../lib/productTour.js")).toMatch(/assistify_product_tour_/);
  });

  test("layout mounts tour for completed onboarding users only", () => {
    expect(layout).toMatch(/ProductTour/);
    expect(layout).toMatch(/onboardingCompleted !== false/);
  });
});

describe("Sprint 24 command palette", () => {
  const palette = read("../components/CommandPalette.jsx");

  test("navigates real modules and does not surface New Agent", () => {
    expect(palette).toMatch(/\/opportunities/);
    expect(palette).toMatch(/\/automations/);
    expect(palette).toMatch(/\/knowledge-brain/);
    expect(palette).toMatch(/\/ai-workspace/);
    expect(palette).not.toMatch(/New Agent/i);
    expect(palette).not.toMatch(/demo/i);
  });

  test("AI actions deep-link Copilot with q=", () => {
    expect(palette).toMatch(/\/ai-chat\?q=/);
  });
});

describe("Sprint 24 error / failure UX", () => {
  test("error boundary has friendly fallback without stack in production UI", () => {
    const eb = read("../components/ErrorBoundary.jsx");
    expect(eb).toMatch(/error-boundary-reload/);
    expect(eb).toMatch(/error-boundary-retry/);
    expect(eb).toMatch(/Something went wrong/);
    expect(eb).toMatch(/NODE_ENV === \"development\"/);
  });

  test("major pages distinguish API failure from empty", () => {
    expect(read("Clients.jsx")).toMatch(/clients-load-error/);
    expect(read("Projects.jsx")).toMatch(/projects-load-error/);
    expect(read("Tasks.jsx")).toMatch(/tasks-load-error/);
    expect(read("Dashboard.jsx")).toMatch(/dashboard-load-error/);
    expect(read("../components/LoadError.jsx")).toMatch(/Try again/);
  });
});

describe("Sprint 24 checklist dismiss persistence", () => {
  test("reads and writes session dismiss key", () => {
    const checklist = read("../components/OnboardingChecklist.jsx");
    expect(checklist).toMatch(/onb_checklist_dismissed/);
    expect(checklist).toMatch(/sessionStorage\.getItem/);
    expect(checklist).toMatch(/dismissChecklist/);
  });
});
