/**
 * @jest-environment node
 */
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname); // frontend/src/help
const read = (rel) => fs.readFileSync(path.join(root, rel), "utf8");
const readJson = (rel) => JSON.parse(fs.readFileSync(path.join(root, "..", rel), "utf8"));

describe("Sprint 31 help system", () => {
  const registry = read("registry.js");
  const panel = read("HelpPanel.jsx");
  const tour = read("GuidedTour.jsx");
  const walk = read("MiniWalkthrough.jsx");
  const persistence = read("persistence.js");
  const analytics = read("analytics.js");
  const helpEn = readJson("i18n/locales/help-en.json");
  const helpNl = readJson("i18n/locales/help-nl.json");
  const pageIntro = fs.readFileSync(path.join(root, "..", "components/PageIntro.jsx"), "utf8");
  const crm = fs.readFileSync(path.join(root, "..", "pages/CRM.jsx"), "utf8");
  const pipeline = fs.readFileSync(path.join(root, "..", "pages/Pipeline.jsx"), "utf8");

  test("registry covers required modules", () => {
    for (const id of [
      "dashboard", "clients", "crm", "pipeline", "projects", "tasks",
      "copilot", "agents", "proposals", "documents", "automations",
      "knowledge", "opportunities", "integrations",
    ]) {
      expect(registry).toMatch(new RegExp(`${id}:`));
    }
  });

  test("CRM has full tutorial + guided tour prototype", () => {
    expect(registry).toMatch(/crm:[\s\S]*hasFullTutorial:\s*true/);
    expect(registry).toMatch(/crm:[\s\S]*hasGuidedTour:\s*true/);
    expect(registry).toMatch(/pipeline-new-lead/);
    expect(registry).toMatch(/lead-save/);
  });

  test("Dashboard, Projects and Copilot have full help prototypes", () => {
    expect(registry).toMatch(/dashboard:[\s\S]*hasFullTutorial:\s*true/);
    expect(registry).toMatch(/projects:[\s\S]*hasFullTutorial:\s*true/);
    expect(registry).toMatch(/copilot:[\s\S]*hasFullTutorial:\s*true/);
    expect(helpEn.help.modules.dashboard.tutorial.steps.length).toBeGreaterThanOrEqual(3);
    expect(helpNl.help.modules.projects.tutorial.steps.length).toBeGreaterThanOrEqual(3);
    expect(helpEn.help.modules.copilot.tutorial.steps.length).toBeGreaterThanOrEqual(4);
  });

  test("NL and EN help copy for CRM", () => {
    expect(helpEn.help.modules.crm.title).toBe("CRM");
    expect(helpNl.help.modules.crm.title).toBe("CRM");
    expect(helpNl.help.modules.crm.description).toMatch(/leads|klanten/i);
    expect(helpEn.help.modules.crm.tutorial.steps.length).toBeGreaterThanOrEqual(5);
    expect(helpNl.help.modules.crm.tutorial.steps.length).toBeGreaterThanOrEqual(5);
    expect(helpNl.help.tryYourself).toMatch(/Probeer/i);
    expect(helpEn.help.tryYourself).toMatch(/Try/i);
  });

  test("help panel and tour controls exist", () => {
    expect(panel).toMatch(/help-start-tutorial/);
    expect(panel).toMatch(/help-try-yourself/);
    expect(walk).toMatch(/mini-walkthrough/);
    expect(tour).toMatch(/guided-tour/);
    expect(tour).toMatch(/guided-tour-skip/);
    expect(tour).toMatch(/guided-tour-back/);
    expect(tour).toMatch(/guided-tour-next|guided-tour-done/);
    expect(tour).toMatch(/Escape/);
  });

  test("tour safety — no auto destructive actions", () => {
    expect(tour).toMatch(/never auto-operates|will not act|waitForClick/i);
    expect(tour).not.toMatch(/crmApi\.createLead/);
    expect(tour).not.toMatch(/aiApi\.|sendEmail|stripe/i);
    expect(walk).toMatch(/never writes|Isolated visual|sandboxed/i);
  });

  test("persistence tracks completed/skipped/version", () => {
    expect(persistence).toMatch(/tutorialStatus/);
    expect(persistence).toMatch(/tourStatus/);
    expect(persistence).toMatch(/tutorialVersion/);
    expect(persistence).toMatch(/tourVersion/);
  });

  test("analytics events include module only", () => {
    expect(analytics).toMatch(/help_opened/);
    expect(analytics).toMatch(/tutorial_started/);
    expect(analytics).toMatch(/tutorial_completed/);
    expect(analytics).toMatch(/tutorial_skipped/);
    expect(analytics).toMatch(/guided_tour_started/);
    expect(analytics).toMatch(/guided_tour_completed/);
    expect(analytics).toMatch(/guided_tour_skipped/);
    expect(analytics).toMatch(/module/);
    expect(analytics).not.toMatch(/email|password|prompt/i);
  });

  test("CRM and Pipeline wire PageHelp entry", () => {
    expect(pageIntro).toMatch(/helpModule/);
    expect(crm).toMatch(/helpModule="crm"/);
    expect(pipeline).toMatch(/helpModule="pipeline"/);
  });

  test("automations help does not overpromise", () => {
    expect(helpEn.help.modules.automations.betaNote).toMatch(/limited|beta/i);
    expect(helpNl.help.modules.automations.betaNote).toMatch(/beperkt|beta/i);
  });
});
