# Assistify Help System

Reusable in-app help for authenticated Assistify modules (Sprint 31).

## Goals

Every important module can eventually support:

1. A short explanation
2. A mini walkthrough / tutorial
3. An interactive “Try it yourself” guided tour

CRM ships the full prototype in this sprint. Other modules register copy + help entry points.

## Architecture

| Piece | Path | Role |
|-------|------|------|
| Registry | `frontend/src/help/registry.js` | Module metadata, tour selectors, versions |
| Context | `frontend/src/help/HelpContext.jsx` | Open panel / tutorial / tour state |
| PageHelp | `frontend/src/help/PageHelp.jsx` | Compact “Help / Uitleg” entry near titles |
| HelpPanel | `frontend/src/help/HelpPanel.jsx` | Side panel (desktop) / bottom sheet (mobile) |
| MiniWalkthrough | `frontend/src/help/MiniWalkthrough.jsx` | Scripted sandboxed slideshow |
| GuidedTour | `frontend/src/help/GuidedTour.jsx` | Highlights real UI; user performs actions |
| Persistence | `frontend/src/help/persistence.js` | completed / skipped / version flags |
| Analytics | `frontend/src/help/analytics.js` | Module-scoped events only |
| Copy | `frontend/src/i18n/locales/help-en.json`, `help-nl.json` | NL + EN strings |

`HelpProvider` wraps the app in `App.js`. `Layout` mounts `HelpPanel`, `MiniWalkthrough`, and `GuidedTour`.

`PageIntro` accepts `helpModule="<id>"` to render the help entry.

## Registry

```js
crm: {
  id: "crm",
  route: "/crm",
  tutorialVersion: "1",
  tourVersion: "1",
  hasFullTutorial: true,
  hasGuidedTour: true,
  tourRoute: "/pipeline",
  tourSteps: [ /* selectors */ ],
}
```

Modules registered: dashboard, clients, crm, pipeline, projects, tasks, copilot, agents, proposals, documents, automations, knowledge, opportunities, integrations.

Pipeline aliases CRM tutorial/tour content (`aliasOf: "crm"`).

## Tutorials

Tutorials are **sandboxed**. The CRM mini walkthrough uses a mock UI stage and never writes to the workspace.

Metadata (in i18n + registry):

- module, locale (via i18n), title, duration, steps, version

Media may later be MP4/WebM; the architecture already supports step-based slideshow demos without external video production.

## Guided tours

Safety rules (non-negotiable):

- Never submit forms without user action
- Never delete data
- Never send emails
- Never trigger paid / external actions
- Never make AI calls automatically
- Never expose secrets

Tours highlight selectors and wait for real clicks when `waitForClick` is set. Controls: Next, Back, Skip, Close, Restart.

## Persistence

Keys: `assistify_help_<userId>_<moduleId>`

Stores only:

- `tutorialStatus` / `tourStatus` (`completed` | `skipped`)
- `tutorialVersion` / `tourVersion`
- `updatedAt`

Returning users are not forced to repeat completed tours for the same version.

## Analytics

Via the existing analytics abstraction:

- `help_opened`
- `tutorial_started` / `tutorial_completed` / `tutorial_skipped`
- `guided_tour_started` / `guided_tour_completed` / `guided_tour_skipped`

Props include `module` only — never user-entered business data.

## Localization

All help chrome and module copy live under `help.*` in NL and EN. Do not ship English-only help panels.

## Accessibility

- Keyboard: Escape closes panel / tutorial / tour; arrow keys in walkthrough
- Focus moves to close control when the panel opens
- `role="dialog"` + labelled titles
- High-contrast highlight ring for tour targets
- `prefers-reduced-motion` respected via global CSS
- Mobile: bottom sheet panel; tour card anchors to the bottom; highlights clamp on-screen

## Adding a tutorial

1. Add or extend the module in `registry.js`
2. Add `help.modules.<id>` copy in `help-en.json` and `help-nl.json`
3. Pass `helpModule="<id>"` from the page’s `PageIntro`
4. If adding a guided tour, define safe selectors and prefer `waitForClick` over auto-advance
5. Bump `tutorialVersion` / `tourVersion` when content changes materially

## CRM prototype

- Help entry on `/crm` and `/pipeline`
- Mini walkthrough: open CRM → new lead → fill → save → stage → note → board
- Try it yourself: navigates to `/pipeline` and highlights `pipeline-new-lead`, form fields, save, follow-up

## Sprint 31.5 expansions

Full mini tutorials + guided tours now ship for:

- Dashboard
- Projects
- Copilot

CRM / Pipeline remains the reference sales-lead prototype.
