/**
 * Sprint 28 — Dutch UI copy and email/inbox polish guards.
 * @jest-environment node
 */
const fs = require("fs");
const path = require("path");

const read = (rel) => fs.readFileSync(path.join(__dirname, "..", rel), "utf8");

describe("Sprint 28 beta polish", () => {
  test("nlCopy provides Dutch email tabs and blocked banner without env var leak", () => {
    const copy = read("lib/nlCopy.js");
    expect(copy).toMatch(/Concepten/);
    expect(copy).toMatch(/Wacht op goedkeuring/);
    expect(copy).toMatch(/Verstuurd/);
    expect(copy).toMatch(/Mislukt/);
    expect(copy).toMatch(/blockedBanner/);
    expect(copy).not.toMatch(/EMAIL_SENDING_ENABLED/);
  });

  test("EmailCenter gates send when outbound is blocked", () => {
    const src = read("pages/EmailCenter.jsx");
    expect(src).toMatch(/emailsNl/);
    expect(src).toMatch(/email-blocked-banner/);
    expect(src).toMatch(/sendBlockedToast/);
    expect(src).toMatch(/transportBlocked \|\| blocked/);
    expect(src).toMatch(/detail-send/);
  });

  test("Inbox guides disconnected users to Integrations", () => {
    const src = read("pages/Inbox.jsx");
    expect(src).toMatch(/inbox-go-integrations/);
    expect(src).toMatch(/noMailboxTitle/);
    expect(src).toMatch(/\/integrations/);
    expect(src).toMatch(/syncDisabled/);
  });

  test("Analytics shows Dutch zero-data empties instead of fake charts", () => {
    const src = read("pages/Analytics.jsx");
    expect(src).toMatch(/analyticsNl/);
    expect(src).toMatch(/docsEmpty/);
    expect(src).toMatch(/tasksTotal/);
    expect(src).toMatch(/analytics-empty/);
  });

  test("sidebar nav uses Dutch labels via nlCopy", () => {
    const layout = read("components/Layout.jsx");
    expect(layout).toMatch(/navNl/);
    expect(layout).toMatch(/Facturatie is niet beschikbaar tijdens de beta/);
    const copy = read("lib/nlCopy.js");
    expect(copy).toMatch(/Klanten/);
    expect(copy).toMatch(/Projecten/);
    expect(copy).toMatch(/Instellingen/);
  });
});
