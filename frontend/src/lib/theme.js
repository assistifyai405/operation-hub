/**
 * Theme preference helpers (Light / Dark / System).
 * Authenticated app remains dark by default (Sprint 31).
 * Marketing pages force light via data-theme on their shell.
 */

export const THEME_STORAGE_KEY = "assistify_theme";
export const THEME_OPTIONS = ["light", "dark", "system"];

export function getStoredTheme() {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    if (THEME_OPTIONS.includes(value)) return value;
  } catch {
    /* ignore */
  }
  return "dark";
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
  return theme === "light" ? "light" : "dark";
}

export function applyTheme(theme = getStoredTheme()) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.setAttribute("data-theme", theme);
  root.dataset.resolvedTheme = resolveTheme(theme);
}
