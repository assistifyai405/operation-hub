// Feature flags. Billing/monetization stays OFF until Stripe is integrated.
export const BILLING_ENABLED = process.env.REACT_APP_BILLING_ENABLED === "true";

// Ephemeral demo login ("Explore demo workspace"). Must match backend ENABLE_DEMO_LOGIN.
// Off by default — never imply production demo access without an explicit build flag.
export const DEMO_LOGIN_ENABLED = process.env.REACT_APP_ENABLE_DEMO_LOGIN === "true";
