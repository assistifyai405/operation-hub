import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  THEME_OPTIONS,
  applyTheme,
  getStoredTheme,
  setStoredTheme,
  resolveTheme,
  watchSystemTheme,
} from "@/lib/theme";

const ThemeContext = createContext(null);

/**
 * Provides Light / Dark / System for the authenticated product.
 * MarketingShell still forces light independently.
 */
export function ThemeProvider({ children, forceTheme = null }) {
  const [theme, setThemeState] = useState(() => (forceTheme && THEME_OPTIONS.includes(forceTheme) ? forceTheme : getStoredTheme()));

  const apply = useCallback((next) => {
    if (forceTheme) {
      applyTheme(forceTheme);
      return;
    }
    setStoredTheme(next);
    setThemeState(next);
  }, [forceTheme]);

  useEffect(() => {
    applyTheme(forceTheme || theme);
  }, [theme, forceTheme]);

  useEffect(() => {
    if (forceTheme) return undefined;
    if (theme !== "system") return undefined;
    return watchSystemTheme(() => applyTheme("system"));
  }, [theme, forceTheme]);

  const value = useMemo(() => ({
    theme: forceTheme || theme,
    resolved: resolveTheme(forceTheme || theme),
    setTheme: apply,
    options: THEME_OPTIONS,
  }), [theme, forceTheme, apply]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}

export function useThemeOptional() {
  return useContext(ThemeContext);
}
