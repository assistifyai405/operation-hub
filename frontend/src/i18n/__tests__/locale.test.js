/**
 * @jest-environment node
 */
import {
  DEFAULT_LOCALE,
  LOCALE_STORAGE_KEY,
  detectBrowserLocale,
  normalizeLocale,
  resolveInitialLocale,
} from "../index";
import { formatCurrency, formatDate } from "../format";

describe("locale detection", () => {
  const store = {};

  beforeEach(() => {
    Object.keys(store).forEach((key) => delete store[key]);
    global.localStorage = {
      getItem: (key) => (key in store ? store[key] : null),
      setItem: (key, value) => { store[key] = String(value); },
      removeItem: (key) => { delete store[key]; },
    };
    Object.defineProperty(global, "navigator", {
      configurable: true,
      value: { language: "en-US", languages: ["en-US"] },
    });
  });

  afterAll(() => {
    delete global.localStorage;
    delete global.navigator;
  });

  test("normalizes supported regional locales and rejects unsupported ones", () => {
    expect(normalizeLocale("nl-NL")).toBe("nl");
    expect(normalizeLocale("en_US")).toBe("en");
    expect(normalizeLocale("de-DE")).toBeNull();
  });

  test("detects the first supported browser locale and falls back to English", () => {
    expect(detectBrowserLocale({ languages: ["de-DE", "nl-NL"], language: "de-DE" })).toBe("nl");
    expect(detectBrowserLocale({ languages: ["fr-FR"], language: "fr-FR" })).toBe(DEFAULT_LOCALE);
    expect(detectBrowserLocale(null)).toBe("en");
  });

  test("resolves user preference before storage, browser, and English fallback", () => {
    store[LOCALE_STORAGE_KEY] = "en";
    Object.defineProperty(global, "navigator", {
      configurable: true,
      value: { language: "nl-NL", languages: ["nl-NL"] },
    });
    expect(resolveInitialLocale("nl")).toBe("nl");

    expect(resolveInitialLocale(null)).toBe("en");

    delete store[LOCALE_STORAGE_KEY];
    expect(resolveInitialLocale(null)).toBe("nl");

    Object.defineProperty(global, "navigator", {
      configurable: true,
      value: { language: "de-DE", languages: ["de-DE"] },
    });
    expect(resolveInitialLocale(null)).toBe("en");
  });
});

describe("localized formatting", () => {
  const normalizeSpaces = (value) => value.replace(/\s/g, " ");

  test("formats dates for Dutch and English", () => {
    const date = new Date(2026, 7, 11);
    expect(formatDate(date, "nl")).toBe("11 augustus 2026");
    expect(formatDate(date, "en")).toBe("August 11, 2026");
  });

  test("formats EUR currency for Dutch and English", () => {
    expect(normalizeSpaces(formatCurrency(1234.5, "nl", "EUR"))).toBe("€ 1.234,50");
    expect(normalizeSpaces(formatCurrency(1234.5, "en", "EUR"))).toBe("€1,234.50");
  });
});
