import { formatCurrencyCompact, formatDateShort, formatRelativeTime } from "@/i18n/format";

/** @deprecated Prefer formatCurrencyCompact with an explicit locale. */
export const money = (v, locale = "en", currency = "EUR") =>
  formatCurrencyCompact(v, locale, currency);

export const relTime = (d, locale = "en", t) => formatRelativeTime(d, locale, t);

export const PRIORITY_META = {
  Critical: { chip: "bg-red-500/15 text-red-300 border-red-500/30", dot: "bg-red-500", ring: "text-red-400" },
  High: { chip: "bg-orange-500/15 text-orange-300 border-orange-500/30", dot: "bg-orange-500", ring: "text-orange-400" },
  Medium: { chip: "bg-amber-500/15 text-amber-300 border-amber-500/30", dot: "bg-amber-500", ring: "text-amber-400" },
  Low: { chip: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30", dot: "bg-emerald-500", ring: "text-emerald-400" },
};

export const healthTone = (score) => {
  const s = Number(score);
  if (!Number.isFinite(s)) {
    return { text: "text-zinc-400", bar: "#71717a", chip: "bg-zinc-500/15 text-zinc-300" };
  }
  return s >= 75 ? { text: "text-emerald-400", bar: "#34d399", chip: "bg-emerald-500/15 text-emerald-300" }
    : s >= 55 ? { text: "text-amber-400", bar: "#f59e0b", chip: "bg-amber-500/15 text-amber-300" }
    : { text: "text-red-400", bar: "#f87171", chip: "bg-red-500/15 text-red-300" };
};

export const DOC_BADGE = {
  proposal: { labelKey: "nav.proposals", chip: "bg-brand-500/15 text-brand-300", icon: "file-text" },
  contract: { labelKey: "nav.contracts", chip: "bg-cyan-500/15 text-cyan-300", icon: "scroll-text" },
  invoice: { labelKey: "nav.invoices", chip: "bg-emerald-500/15 text-emerald-300", icon: "receipt" },
  plan: { labelKey: "planner.plan", chip: "bg-amber-500/15 text-amber-300", icon: "list-checks" },
};

export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-xl bg-zinc-900 ${className}`} />;
}

export function Section({ title, icon: Icon, action, children, testid }) {
  return (
    <section data-testid={testid}>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
          {Icon && <Icon className="h-4 w-4 text-brand-400" />} {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export { formatDateShort };
