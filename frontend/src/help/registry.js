/**
 * Central module-help registry.
 * Copy lives in i18n under `help.modules.<id>` — this file holds structure + selectors.
 *
 * Safety: guided tours never auto-submit, delete, email, pay, or call AI.
 */

export const HELP_MODULES = {
  dashboard: {
    id: "dashboard",
    route: "/dashboard",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: false,
    hasGuidedTour: false,
  },
  clients: {
    id: "clients",
    route: "/clients",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: false,
    hasGuidedTour: false,
  },
  crm: {
    id: "crm",
    route: "/crm",
    /** Full prototype: mini tutorial + guided tour (tour runs on Pipeline UI). */
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: true,
    hasGuidedTour: true,
    tourRoute: "/pipeline",
    tourSteps: [
      {
        id: "new-lead",
        selector: '[data-testid="pipeline-new-lead"]',
        waitForClick: true,
      },
      {
        id: "fill-form",
        selector: '[data-testid="lead-title-input"]',
        waitForVisible: '[data-testid="lead-drawer"]',
      },
      {
        id: "save",
        selector: '[data-testid="lead-save"]',
        waitForClick: true,
      },
      {
        id: "follow-up",
        selector: '[data-testid="lead-stage-select"], [data-testid="pipeline-lead-card"]',
        optional: true,
      },
    ],
  },
  pipeline: {
    id: "pipeline",
    route: "/pipeline",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: true,
    hasGuidedTour: true,
    /** Reuse CRM lead tour content (same UI). */
    aliasOf: "crm",
    tourSteps: null, // resolved via alias
  },
  projects: {
    id: "projects",
    route: "/projects",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: false,
    hasGuidedTour: false,
  },
  tasks: {
    id: "tasks",
    route: "/tasks",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: false,
    hasGuidedTour: false,
  },
  copilot: {
    id: "copilot",
    route: "/ai-chat",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: false,
    hasGuidedTour: false,
  },
  agents: {
    id: "agents",
    route: "/ai-agents",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: false,
    hasGuidedTour: false,
  },
  proposals: {
    id: "proposals",
    route: "/proposals",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: false,
    hasGuidedTour: false,
  },
  documents: {
    id: "documents",
    route: "/documents",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: false,
    hasGuidedTour: false,
  },
  automations: {
    id: "automations",
    route: "/automations",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: false,
    hasGuidedTour: false,
    betaLimited: true,
  },
  knowledge: {
    id: "knowledge",
    route: "/knowledge-brain",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: false,
    hasGuidedTour: false,
  },
  opportunities: {
    id: "opportunities",
    route: "/opportunities",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: false,
    hasGuidedTour: false,
  },
  integrations: {
    id: "integrations",
    route: "/integrations",
    tutorialVersion: "1",
    tourVersion: "1",
    hasFullTutorial: false,
    hasGuidedTour: false,
  },
};

export function getHelpModule(moduleId) {
  const mod = HELP_MODULES[moduleId];
  if (!mod) return null;
  if (mod.aliasOf) {
    const base = HELP_MODULES[mod.aliasOf];
    return {
      ...base,
      ...mod,
      id: mod.id,
      tourSteps: base.tourSteps,
      hasFullTutorial: base.hasFullTutorial,
      hasGuidedTour: base.hasGuidedTour,
      contentId: mod.aliasOf,
    };
  }
  return { ...mod, contentId: mod.id };
}

export function listHelpModules() {
  return Object.keys(HELP_MODULES);
}
