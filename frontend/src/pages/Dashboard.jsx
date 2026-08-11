import PageIntro from "@/components/PageIntro";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Search, ArrowRight, X, Bot, Sun } from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { dashboardApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/context/LocaleContext";
import { AiIcon } from "@/components/ai/aiHelpers";
import OnboardingChecklist from "@/components/OnboardingChecklist";
import DemoDataBanner from "@/components/DemoDataBanner";
import { MorningBrief } from "@/components/dashboard/MorningBrief";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { BusinessPerformanceChart } from "@/components/dashboard/BusinessPerformanceChart";
import { AIExecutiveBrief } from "@/components/dashboard/AIExecutiveBrief";
import { AiActivityTimeline } from "@/components/dashboard/AiActivityTimeline";
import { TodayPriorities } from "@/components/dashboard/TodayPriorities";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { DashboardFirstRun } from "@/components/dashboard/DashboardFirstRun";
import { Skeleton, money } from "@/components/dashboard/execShared";
import { LoadError } from "@/components/LoadError";

function GlobalSearch({ navigate }) {
  const { t } = useTranslation();
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!q.trim()) { setResults(null); return; }
    const t = setTimeout(() => { dashboardApi.search(q).then((r) => { setResults(r); setOpen(true); }).catch(() => {}); }, 250);
    return () => clearTimeout(t);
  }, [q]);
  const groups = results ? [
    { key: "clients", label: t("nav.clients"), items: results.clients, to: () => "/clients", title: (i) => i.name },
    { key: "projects", label: t("nav.projects"), items: results.projects, to: (i) => `/projects/${i.id}`, title: (i) => i.name },
    { key: "invoices", label: t("nav.invoices"), items: results.invoices, to: (i) => `/projects/${i.project_id}?tab=invoice`, title: (i) => `${i.invoice_number} · ${i.title}` },
    { key: "contracts", label: t("nav.contracts"), items: results.contracts, to: (i) => `/projects/${i.project_id}?tab=contract`, title: (i) => i.title },
    { key: "proposals", label: t("nav.proposals"), items: results.proposals, to: (i) => `/projects/${i.project_id}?tab=proposal`, title: (i) => i.title },
  ].filter((g) => g.items?.length) : [];
  return (
    <div className="relative w-full sm:w-80" data-testid="dashboard-search">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" aria-hidden="true" />
      <label htmlFor="dashboard-search-input" className="sr-only">{t("dashboard.search.label")}</label>
      <input
        id="dashboard-search-input"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => results && setOpen(true)}
        data-testid="dashboard-search-input"
        placeholder={t("dashboard.search.placeholder")}
        className="w-full rounded-xl border border-white/10 bg-zinc-950/80 py-2 pl-10 pr-9 text-sm text-zinc-200 outline-none backdrop-blur focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40"
      />
      {q && (
        <button type="button" onClick={() => { setQ(""); setOpen(false); }} aria-label={t("dashboard.search.clear")} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-200">
          <X className="h-4 w-4" />
        </button>
      )}
      {open && results && (
        <div className="absolute z-30 mt-2 max-h-96 w-full overflow-y-auto rounded-xl border border-white/10 bg-zinc-950 p-2 shadow-2xl" data-testid="dashboard-search-results">
          {groups.length === 0 ? <p className="px-3 py-4 text-center text-sm text-zinc-500">{t("dashboard.search.noResults", { query: q })}</p> :
            groups.map((g) => (
              <div key={g.key} className="mb-1">
                <p className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">{g.label}</p>
                {g.items.map((i, idx) => (
                  <button key={idx} type="button" onClick={() => { navigate(g.to(i)); setOpen(false); setQ(""); }} data-testid={`search-result-${g.key}`}
                    className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-zinc-200 transition-colors hover:bg-zinc-900">
                    <span className="truncate">{g.title(i)}</span><ArrowRight className="h-3.5 w-3.5 text-zinc-500" aria-hidden="true" />
                  </button>
                ))}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6" data-testid="dashboard-loading">
      <Skeleton className="h-10 w-80" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-32" />)}</div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3"><Skeleton className="h-80 lg:col-span-2" /><Skeleton className="h-80" /></div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2"><Skeleton className="h-56" /><Skeleton className="h-56" /></div>
    </div>
  );
}

export default function Dashboard() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [briefOpen, setBriefOpen] = useState(false);
  const load = useCallback(() => {
    setLoading(true);
    setLoadError(null);
    dashboardApi.executive()
      .then(setData)
      .catch((e) => { toast.error(e.message); setLoadError(e.message || t("dashboard.loadError")); })
      .finally(() => setLoading(false));
  }, [t]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!user || !data) return;
    // Don't auto-open Morning Brief on an empty workspace — it feels like fake insights
    if (data.workspace_empty) return;
    const key = `mb_seen_${user.id}_${new Date().toISOString().slice(0, 10)}`;
    if (!localStorage.getItem(key)) {
      setBriefOpen(true);
      localStorage.setItem(key, "1");
    }
  }, [user, data]);
  if (loading) return <DashboardSkeleton />;
  if (loadError || !data) {
    return <LoadError message={loadError || t("dashboard.loadError")} onRetry={load} testid="dashboard-load-error" />;
  }

  const firstName = (user?.firstName || (user?.email || "").split("@")[0] || "").trim();
  const { hero } = data;
  const workspaceEmpty = Boolean(data.workspace_empty);

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <PageIntro title={t("pages.dashboard.title")} description={t("pages.dashboard.description")} help={t("help.morningBrief")} />

      <OnboardingChecklist />
      <DemoDataBanner />

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-2xl font-bold tracking-tight text-zinc-50 sm:text-3xl" data-testid="dashboard-greeting">
            {workspaceEmpty ? t("dashboard.welcome") : hero.greeting}{firstName ? `, ${firstName}` : ""}
          </motion.h1>
          {!workspaceEmpty && (
            <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1" data-testid="hero-brief">
              {(hero.brief_lines || []).slice(0, 3).map((l, i) => (
                <span key={i} className="inline-flex items-center gap-1.5 text-xs text-zinc-400" data-testid="hero-brief-line">
                  <AiIcon name={l.icon} className="h-3.5 w-3.5 text-brand-400" /> {l.text}
                </span>
              ))}
            </div>
          )}
          {workspaceEmpty && (
            <p className="mt-1.5 text-sm text-zinc-500">{t("dashboard.emptyDescription")}</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <GlobalSearch navigate={navigate} />
          <button
            type="button"
            onClick={() => setBriefOpen(true)}
            data-testid="open-morning-brief"
            className="inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-white/10 bg-zinc-950/80 px-3.5 py-2 text-sm font-medium text-zinc-300 backdrop-blur transition-all hover:border-brand-500/40 hover:text-zinc-100"
          >
            <Sun className="h-4 w-4 text-amber-400" aria-hidden="true" /> {t("dashboard.morning.title")}
          </button>
          <button
            type="button"
            onClick={() => navigate("/ai-chat")}
            data-testid="hero-ask-ai"
            className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-brand-600 px-3.5 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-500 glow-brand"
          >
            <Bot className="h-4 w-4" aria-hidden="true" /> {t("dashboard.askAi")}
          </button>
        </div>
      </div>

      {workspaceEmpty ? (
        <DashboardFirstRun />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiCard id="health" title={t("dashboard.kpis.health")} kpi={data.kpi_cards.health} format={(v) => `${Math.round(v)}`} color="#34d399" delay={0}
              tooltip={t("dashboard.kpis.healthTooltip")} />
            <KpiCard id="pipeline" title={t("dashboard.kpis.pipeline")} kpi={data.kpi_cards.pipeline} format={(v) => money(v, locale)} color="#8b5cf6" delay={0.08}
              tooltip={t("dashboard.kpis.pipelineTooltip")} />
            <KpiCard id="hours_saved" title={t("dashboard.kpis.hoursSaved")} kpi={data.kpi_cards.hours_saved} format={(v) => `${Number(v).toFixed(1)}h`} color="#22d3ee" delay={0.16}
              tooltip={t("dashboard.kpis.hoursSavedTooltip")} />
            <KpiCard id="revenue_month" title={t("dashboard.kpis.revenueMonth")} kpi={data.kpi_cards.revenue_month} format={(v) => money(v, locale)} color="#f472b6" delay={0.24}
              tooltip={t("dashboard.kpis.revenueMonthTooltip")} />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2"><BusinessPerformanceChart trends={data.trends} workspaceEmpty={workspaceEmpty} /></div>
            <AIExecutiveBrief insights={data.insights} hero={data.hero} health={data.health} workspaceEmpty={workspaceEmpty} />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <AiActivityTimeline activity={data.ai_activity} />
            <TodayPriorities priorities={data.priorities} total={data.priorities_total} />
          </div>
        </>
      )}

      <QuickActions firstRun={workspaceEmpty} />
      <MorningBrief open={briefOpen} onOpenChange={setBriefOpen} />
    </div>
  );
}
