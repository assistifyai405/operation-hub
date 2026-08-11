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

export function formatDateTime(value, locale, options = {}) {
  if (!value) return "—";
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat(localeTag(locale), {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    ...options,
  }).format(d);
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

/** Whole-currency amounts for KPI cards (no cents). */
export function formatCurrencyCompact(amount, locale, currency = "EUR") {
  const n = Number(amount);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat(localeTag(locale), {
    style: "currency",
    currency: currency || "EUR",
    maximumFractionDigits: 0,
  }).format(n);
}

export function formatNumber(amount, locale, options = {}) {
  const n = Number(amount);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat(localeTag(locale), options).format(n);
}

/**
 * Relative time for activity feeds. Pass `t` from useTranslation for localized labels,
 * or omit for English fallbacks.
 */
export function formatRelativeTime(value, locale, t) {
  if (!value) return "";
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const s = (Date.now() - d.getTime()) / 1000;
  const tr = (key, fallback, vars) => (typeof t === "function" ? t(key, { defaultValue: fallback, ...vars }) : fallback);
  if (s < 60) return tr("time.justNow", "just now");
  if (s < 3600) return tr("time.minutesAgo", "{{count}}m ago", { count: Math.floor(s / 60) });
  if (s < 86400) return tr("time.hoursAgo", "{{count}}h ago", { count: Math.floor(s / 3600) });
  if (s < 604800) return tr("time.daysAgo", "{{count}}d ago", { count: Math.floor(s / 86400) });
  return formatDateShort(d, locale);
}
