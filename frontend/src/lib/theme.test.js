/**
 * @jest-environment node
 */
import {
  getStoredTheme,
  setStoredTheme,
  resolveTheme,
  applyTheme,
  THEME_STORAGE_KEY,
} from "./theme";

describe("theme preference", () => {
  const store = {};
  beforeEach(() => {
    Object.keys(store).forEach((k) => delete store[k]);
    global.localStorage = {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
    };
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.removeAttribute("data-theme-preference");
  });

  test("defaults to light for new users", () => {
    expect(getStoredTheme()).toBe("light");
  });

  test("persists explicit preference and applies resolved theme", () => {
    setStoredTheme("dark");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme-preference")).toBe("dark");
  });

  test("system resolves via matchMedia", () => {
    window.matchMedia = () => ({ matches: true, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} });
    expect(resolveTheme("system")).toBe("light");
    applyTheme("system");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(document.documentElement.getAttribute("data-theme-preference")).toBe("system");
  });
});
