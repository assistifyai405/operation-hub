/**
 * Product frame — CSS Assistify UI preview for marketing.
 * Light-theme friendly; no fake metrics or private data.
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
      className={`overflow-hidden rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] shadow-brand-soft ${className}`}
      data-testid="product-frame"
      aria-label={alt}
    >
      <div className="flex items-center gap-2 border-b border-[var(--theme-border)] bg-[var(--theme-surface-muted)] px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-zinc-300" aria-hidden="true" />
        <span className="h-2.5 w-2.5 rounded-full bg-zinc-300" aria-hidden="true" />
        <span className="h-2.5 w-2.5 rounded-full bg-zinc-300" aria-hidden="true" />
        <div className="ml-3 min-w-0 flex-1">
          <p className="truncate text-xs font-medium text-[var(--theme-text-primary)]">{title}</p>
          {subtitle ? <p className="truncate text-[10px] text-[var(--theme-text-secondary)]">{subtitle}</p> : null}
        </div>
      </div>
      <div className="bg-[var(--theme-surface)] p-4 sm:p-5">
        {children}
      </div>
    </figure>
  );
}

/** Neutral dashboard-style mock using Assistify brand tokens. */
export function DashboardMock({ t }) {
  const items = [
    { label: t("marketing.mock.clients"), hint: t("marketing.mock.clientsHint") },
    { label: t("marketing.mock.projects"), hint: t("marketing.mock.projectsHint") },
    { label: t("marketing.mock.tasks"), hint: t("marketing.mock.tasksHint") },
  ];
  return (
    <ProductFrame title="Assistify" subtitle={t("marketing.mock.dashboardSub")} alt={t("marketing.mock.dashboardAlt")}>
      <div className="grid gap-3 sm:grid-cols-[140px_1fr]">
        <aside className="hidden space-y-2 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface-muted)] p-3 sm:block" aria-hidden="true">
          {["Dashboard", "Clients", "Projects", "Copilot"].map((x) => (
            <div key={x} className="rounded-lg px-2 py-1.5 text-[11px] text-[var(--theme-text-secondary)]">
              <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-[var(--theme-brand)]" />
              {x}
            </div>
          ))}
        </aside>
        <div className="space-y-3">
          <div className="rounded-xl border border-[var(--theme-brand-border)] bg-[var(--theme-brand-soft)] p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-brand)]">{t("marketing.mock.brief")}</p>
            <p className="mt-1 text-sm text-[var(--theme-text-primary)]">{t("marketing.mock.briefBody")}</p>
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            {items.map((it) => (
              <div key={it.label} className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 shadow-soft">
                <p className="text-xs font-medium text-[var(--theme-text-primary)]">{it.label}</p>
                <p className="mt-1 text-[11px] leading-relaxed text-[var(--theme-text-secondary)]">{it.hint}</p>
              </div>
            ))}
          </div>
          <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface-muted)] p-3">
            <p className="text-[11px] font-medium text-[var(--theme-text-secondary)]">{t("marketing.mock.copilot")}</p>
            <p className="mt-1 text-sm text-[var(--theme-text-primary)]">{t("marketing.mock.copilotLine")}</p>
          </div>
        </div>
      </div>
    </ProductFrame>
  );
}

/** Showcase mock that changes with the active product tab. */
export function ShowcaseMock({ tab, t }) {
  const title = t(`marketing.showcase.items.${tab}.visualTitle`);
  const lines = t(`marketing.showcase.items.${tab}.visualLines`, { returnObjects: true });
  const bullets = Array.isArray(lines) ? lines : [];
  return (
    <ProductFrame title="Assistify" subtitle={title} alt={title}>
      <div className="space-y-3" data-testid={`showcase-visual-${tab}`}>
        <div className="rounded-xl border border-[var(--theme-brand-border)] bg-[var(--theme-brand-soft)] p-4">
          <p className="text-sm font-semibold text-[var(--theme-text-primary)]">{title}</p>
          <p className="mt-1 text-xs text-[var(--theme-text-secondary)]">{t(`marketing.showcase.items.${tab}.summary`)}</p>
        </div>
        <ul className="space-y-2">
          {bullets.map((line) => (
            <li key={line} className="rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface-muted)] px-3 py-2 text-sm text-[var(--theme-text-primary)]">
              {line}
            </li>
          ))}
        </ul>
      </div>
    </ProductFrame>
  );
}
