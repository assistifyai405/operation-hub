import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/context/AuthContext";
import { authApi } from "@/lib/api";
import {
  DEFAULT_LOCALE,
  normalizeLocale,
  resolveInitialLocale,
  writeStoredLocale,
  SUPPORTED_LOCALES,
} from "@/i18n";

const LocaleContext = createContext(null);

export function LocaleProvider({ children }) {
  const { i18n } = useTranslation();
  const { user } = useAuth();
  const [locale, setLocaleState] = useState(() => resolveInitialLocale(null));

  // Sync from authenticated preference whenever user loads/changes
  useEffect(() => {
    if (user && typeof user === "object" && user.language) {
      const fromUser = normalizeLocale(user.language);
      if (fromUser && fromUser !== locale) {
        setLocaleState(fromUser);
        writeStoredLocale(fromUser);
        if (i18n.language !== fromUser) i18n.changeLanguage(fromUser);
      }
    }
  }, [user, i18n]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (i18n.language !== locale) i18n.changeLanguage(locale);
    if (typeof document !== "undefined") {
      document.documentElement.lang = locale;
    }
  }, [locale, i18n]);

  const setLocale = useCallback(async (next, { persistRemote = true } = {}) => {
    const n = normalizeLocale(next) || DEFAULT_LOCALE;
    setLocaleState(n);
    writeStoredLocale(n);
    await i18n.changeLanguage(n);
    if (persistRemote && user && typeof user === "object" && user.id) {
      try {
        await authApi.updateProfile({ language: n });
      } catch {
        /* preference still saved locally */
      }
    }
    return n;
  }, [i18n, user]);

  const value = useMemo(() => ({
    locale,
    setLocale,
    supportedLocales: SUPPORTED_LOCALES,
    isDutch: locale === "nl",
    isEnglish: locale === "en",
  }), [locale, setLocale]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within LocaleProvider");
  return ctx;
}
