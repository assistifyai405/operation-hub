/**
 * Assistify i18n bootstrap (Sprint 29).
 *
 * Preference priority:
 * 1. authenticated user.language (nl|en)
 * 2. localStorage assistify_locale (explicit manual choice)
 * 3. browser/device language
 * 4. English fallback
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import en from "./locales/en.json";
import nl from "./locales/nl.json";

export const SUPPORTED_LOCALES = ["nl", "en"];
export const DEFAULT_LOCALE = "en";
export const LOCALE_STORAGE_KEY = "assistify_locale";

export function normalizeLocale(raw) {
  if (!raw || typeof raw !== "string") return null;
  const lower = raw.trim().toLowerCase().replace("_", "-");
  if (lower === "nl" || lower.startsWith("nl-")) return "nl";
  if (lower === "en" || lower.startsWith("en-")) return "en";
  return null;
}

export function detectBrowserLocale(nav = typeof navigator !== "undefined" ? navigator : null) {
  if (!nav) return DEFAULT_LOCALE;
  const list = Array.isArray(nav.languages) && nav.languages.length ? nav.languages : [nav.language];
  for (const item of list) {
    const n = normalizeLocale(item);
    if (n) return n;
  }
  return DEFAULT_LOCALE;
}

export function readStoredLocale() {
  try {
    return normalizeLocale(localStorage.getItem(LOCALE_STORAGE_KEY));
  } catch {
    return null;
  }
}

export function writeStoredLocale(locale) {
  const n = normalizeLocale(locale);
  if (!n) return;
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, n);
  } catch {
    /* ignore */
  }
}

export function resolveInitialLocale(userLanguage) {
  const fromUser = normalizeLocale(userLanguage);
  if (fromUser) return fromUser;
  const stored = readStoredLocale();
  if (stored) return stored;
  return detectBrowserLocale();
}

if (!i18n.isInitialized) {
  i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      resources: {
        en: { translation: en },
        nl: { translation: nl },
      },
      supportedLngs: SUPPORTED_LOCALES,
      fallbackLng: DEFAULT_LOCALE,
      lng: resolveInitialLocale(null),
      interpolation: { escapeValue: false },
      detection: {
        // We manage order ourselves via LocaleProvider; detector is fallback only.
        order: ["localStorage", "navigator"],
        lookupLocalStorage: LOCALE_STORAGE_KEY,
        caches: [],
      },
      react: { useSuspense: false },
    });
}

export default i18n;
