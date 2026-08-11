import { normalizeLocale, DEFAULT_LOCALE } from "./index";

export function localeTag(locale) {
  const n = normalizeLocale(locale) || DEFAULT_LOCALE;
  return n === "nl" ? "nl-NL" : "en-US";
}

export function formatDate(value, locale, options = {}) {
  if (!value) return "—";
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const opts = { year: "numeric", month: "long", day: "numeric", ...options };
  return new Intl.DateTimeFormat(localeTag(locale), opts).format(d);
}

export function formatDateShort(value, locale) {
  return formatDate(value, locale, { year: "numeric", month: "short", day: "numeric" });
}

export function formatCurrency(amount, locale, currency = "EUR") {
  const n = Number(amount);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat(localeTag(locale), {
    style: "currency",
    currency: currency || "EUR",
    maximumFractionDigits: 2,
  }).format(n);
}

export function formatNumber(amount, locale, options = {}) {
  const n = Number(amount);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat(localeTag(locale), options).format(n);
}
