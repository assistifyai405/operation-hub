/**
 * Theme preference helpers (Light / Dark / System).
 * Sprint 31.5: authenticated app defaults to Light for new users.
 * Marketing pages force light via MarketingShell regardless of preference.
 */

export const THEME_STORAGE_KEY = "assistify_theme";
export const THEME_OPTIONS = ["light", "dark", "system"];

/** True once the user (or app) has explicitly stored a preference. */
export function hasStoredTheme() {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    return THEME_OPTIONS.includes(value);
  } catch {
    return false;
  }
}

/**
 * Preference priority:
 * explicit stored preference → Light fallback for new users
 * (System is an explicit choice once selected.)
 */
export function getStoredTheme() {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    if (THEME_OPTIONS.includes(value)) return value;
  } catch {
    /* ignore */
  }
  return "light";
}

export function setStoredTheme(theme) {
  if (!THEME_OPTIONS.includes(theme)) return;
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    /* ignore */
  }
  applyTheme(theme);
}

export function resolveTheme(theme = getStoredTheme()) {
  if (theme === "system") {
    if (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: light)").matches) {
      return "light";
    }
    return "dark";
  }
  return theme === "dark" ? "dark" : "light";
}

/**
 * Apply theme to <html>.
 * data-theme = resolved light|dark (drives CSS tokens)
 * data-theme-preference = light|dark|system (user choice)
 */
export function applyTheme(theme = getStoredTheme()) {
  if (typeof document === "undefined") return;
  const preference = THEME_OPTIONS.includes(theme) ? theme : "light";
  const resolved = resolveTheme(preference);
  const root = document.documentElement;
  root.setAttribute("data-theme", resolved);
  root.setAttribute("data-theme-preference", preference);
  root.dataset.resolvedTheme = resolved;
}

export function watchSystemTheme(callback) {
  if (typeof window === "undefined" || !window.matchMedia) return () => {};
  const mq = window.matchMedia("(prefers-color-scheme: light)");
  const handler = () => callback();
  if (mq.addEventListener) mq.addEventListener("change", handler);
  else mq.addListener(handler);
  return () => {
    if (mq.removeEventListener) mq.removeEventListener("change", handler);
    else mq.removeListener(handler);
  };
}
