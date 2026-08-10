/**
 * @jest-environment node
 */
const { track, events, getAnalyticsBuffer, clearAnalyticsBuffer, setAnalyticsSink } = require("./analytics");

describe("analytics abstraction", () => {
  beforeEach(() => {
    clearAnalyticsBuffer();
    setAnalyticsSink(null);
  });

  test("records events and sanitizes sensitive keys", () => {
    track("user_registered", { plan: "free", password: "secret", token: "abc", ok: true });
    const buf = getAnalyticsBuffer();
    expect(buf).toHaveLength(1);
    expect(buf[0].event).toBe("user_registered");
    expect(buf[0].props.ok).toBe(true);
    expect(buf[0].props.plan).toBe("free");
    expect(buf[0].props.password).toBeUndefined();
    expect(buf[0].props.token).toBeUndefined();
  });

  test("named helpers emit expected event names", () => {
    events.onboardingStarted();
    events.clientCreated({ source: "ui" });
    events.copilotUsed();
    const names = getAnalyticsBuffer().map((e) => e.event);
    expect(names).toEqual(["onboarding_started", "client_created", "copilot_used"]);
  });

  test("custom sink receives payloads", () => {
    const seen = [];
    setAnalyticsSink((p) => seen.push(p));
    track("agent_opened", { agentId: "copilot" });
    expect(seen[0].event).toBe("agent_opened");
    expect(seen[0].props.agentId).toBe("copilot");
  });
});
