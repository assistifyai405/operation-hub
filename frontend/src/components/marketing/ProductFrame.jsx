/**
 * CSS product frame — realistic Assistify UI mock without fake metrics.
 * Visual-only; not connected to live workspace data.
 */
export default function ProductFrame({
  title = "Assistify",
  subtitle,
  children,
  className = "",
  alt = "Assistify product preview",
}) {
  return (
    <figure
      className={`overflow-hidden rounded-2xl border border-white/10 bg-zinc-950 shadow-[0_30px_80px_-40px_rgba(34,197,94,0.35)] ${className}`}
      data-testid="product-frame"
      aria-label={alt}
    >
      <div className="flex items-center gap-2 border-b border-white/10 bg-zinc-900/80 px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-zinc-600" aria-hidden="true" />
        <span className="h-2.5 w-2.5 rounded-full bg-zinc-600" aria-hidden="true" />
        <span className="h-2.5 w-2.5 rounded-full bg-zinc-600" aria-hidden="true" />
        <div className="ml-3 min-w-0 flex-1">
          <p className="truncate text-xs font-medium text-zinc-300">{title}</p>
          {subtitle ? <p className="truncate text-[10px] text-zinc-500">{subtitle}</p> : null}
        </div>
      </div>
      <div className="bg-gradient-to-br from-zinc-950 via-zinc-950 to-zinc-900 p-4 sm:p-5">
        {children}
      </div>
    </figure>
  );
}

/** Neutral dashboard-style mock using Assistify green brand tokens. */
export function DashboardMock({ t }) {
  const items = [
    { label: t("marketing.mock.clients"), hint: t("marketing.mock.clientsHint") },
    { label: t("marketing.mock.projects"), hint: t("marketing.mock.projectsHint") },
    { label: t("marketing.mock.tasks"), hint: t("marketing.mock.tasksHint") },
  ];
  return (
    <ProductFrame title="Assistify" subtitle={t("marketing.mock.dashboardSub")} alt={t("marketing.mock.dashboardAlt")}>
      <div className="grid gap-3 sm:grid-cols-[140px_1fr]">
        <aside className="hidden space-y-2 rounded-xl border border-white/5 bg-black/40 p-3 sm:block" aria-hidden="true">
          {["Dashboard", "Clients", "Projects", "Copilot"].map((x) => (
            <div key={x} className="rounded-lg px-2 py-1.5 text-[11px] text-zinc-400">
              <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-brand-500/80" />
              {x}
            </div>
          ))}
        </aside>
        <div className="space-y-3">
          <div className="rounded-xl border border-brand-500/20 bg-brand-600/10 p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-300">{t("marketing.mock.brief")}</p>
            <p className="mt-1 text-sm text-zinc-200">{t("marketing.mock.briefBody")}</p>
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            {items.map((it) => (
              <div key={it.label} className="rounded-xl border border-white/10 bg-zinc-900/80 p-3">
                <p className="text-xs font-medium text-zinc-200">{it.label}</p>
                <p className="mt-1 text-[11px] leading-relaxed text-zinc-500">{it.hint}</p>
              </div>
            ))}
          </div>
          <div className="rounded-xl border border-white/10 bg-zinc-900/60 p-3">
            <p className="text-[11px] font-medium text-zinc-400">{t("marketing.mock.copilot")}</p>
            <p className="mt-1 text-sm text-zinc-300">{t("marketing.mock.copilotLine")}</p>
          </div>
        </div>
      </div>
    </ProductFrame>
  );
}
