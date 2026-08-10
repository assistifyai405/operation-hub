/**
 * Lightweight product-event abstraction.
 * No paid provider yet — events are queued in-memory and optionally mirrored
 * to console in development. Swap `sink` later for Segment/PostHog/etc.
 *
 * Never log AI prompts, tokens, passwords, or other sensitive content.
 */

const FORBIDDEN_KEYS = /password|token|secret|prompt|authorization|cookie|apikey|api_key/i;

let sink = null;
const buffer = [];
const MAX_BUFFER = 200;

export function setAnalyticsSink(fn) {
  sink = typeof fn === "function" ? fn : null;
}

function sanitizeProps(props) {
  if (!props || typeof props !== "object") return {};
  const out = {};
  for (const [k, v] of Object.entries(props)) {
    if (FORBIDDEN_KEYS.test(k)) continue;
    if (typeof v === "string" && v.length > 120) {
      out[k] = `${v.slice(0, 117)}…`;
    } else if (typeof v === "number" || typeof v === "boolean" || v == null) {
      out[k] = v;
    } else if (typeof v === "string") {
      out[k] = v;
    }
    // skip nested objects / arrays of content
  }
  return out;
}

/**
 * @param {string} eventName
 * @param {Record<string, string|number|boolean|null|undefined>} [props]
 */
export function track(eventName, props = {}) {
  if (!eventName || typeof eventName !== "string") return;
  const payload = {
    event: eventName,
    props: sanitizeProps(props),
    ts: new Date().toISOString(),
  };
  buffer.push(payload);
  if (buffer.length > MAX_BUFFER) buffer.shift();

  try {
    if (sink) sink(payload);
    else if (process.env.NODE_ENV === "development" && typeof console !== "undefined") {
      // Quiet breadcrumb for local debugging — never includes secrets by construction
      console.debug("[analytics]", payload.event, payload.props);
    }
  } catch {
    /* never break UX for analytics */
  }
}

export function getAnalyticsBuffer() {
  return [...buffer];
}

export function clearAnalyticsBuffer() {
  buffer.length = 0;
}

// Named helpers for common product events
export const events = {
  userRegistered: (props) => track("user_registered", props),
  onboardingStarted: (props) => track("onboarding_started", props),
  onboardingCompleted: (props) => track("onboarding_completed", props),
  onboardingSkipped: (props) => track("onboarding_skipped", props),
  clientCreated: (props) => track("client_created", props),
  projectCreated: (props) => track("project_created", props),
  taskCreated: (props) => track("task_created", props),
  copilotUsed: (props) => track("copilot_used", props),
  agentOpened: (props) => track("agent_opened", props),
  proposalCreated: (props) => track("proposal_created", props),
};
