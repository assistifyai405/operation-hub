import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, ArrowRight, X, Bot, Sun } from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { dashboardApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
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
import { Skeleton, money } from "@/components/dashboard/execShared";

function GlobalSearch({ navigate }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!q.trim()) { setResults(null); return; }
    const t = setTimeout(() => { dashboardApi.search(q).then((r) => { setResults(r); setOpen(true); }).catch(() => {}); }, 250);
    return () => clearTimeout(t);
  }, [q]);
  const groups = results ? [
    { key: "clients", label: "Clients", items: results.clients, to: () => "/clients", title: (i) => i.name },
    { key: "projects", label: "Projects", items: results.projects, to: (i) => `/projects/${i.id}`, title: (i) => i.name },
    { key: "invoices", label: "Invoices", items: results.invoices, to: (i) => `/projects/${i.project_id}?tab=invoice`, title: (i) => `${i.invoice_number} · ${i.title}` },
    { key: "contracts", label: "Contracts", items: results.contracts, to: (i) => `/projects/${i.project_id}?tab=contract`, title: (i) => i.title },
    { key: "proposals", label: "Proposals", items: results.proposals, to: (i) => `/projects/${i.project_id}?tab=proposal`, title: (i) => i.title },
  ].filter((g) => g.items?.length) : [];
  return (
    <div className="relative w-full sm:w-80" data-testid="dashboard-search">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
      <input value={q} onChange={(e) => setQ(e.target.value)} onFocus={() => results && setOpen(true)}
        data-testid="dashboard-search-input" placeholder="Search everything…"
        className="w-full rounded-xl border border-white/10 bg-zinc-950/80 py-2 pl-10 pr-9 text-sm text-zinc-200 outline-none backdrop-blur focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
      {q && <button onClick={() => { setQ(""); setOpen(false); }} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-200"><X className="h-4 w-4" /></button>}
      {open && results && (
        <div className="absolute z-30 mt-2 max-h-96 w-full overflow-y-auto rounded-xl border border-white/10 bg-zinc-950 p-2 shadow-2xl" data-testid="dashboard-search-results">
          {groups.length === 0 ? <p className="px-3 py-4 text-center text-sm text-zinc-500">No results for "{q}"</p> :
            groups.map((g) => (
              <div key={g.key} className="mb-1">
                <p className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">{g.label}</p>
                {g.items.map((i, idx) => (
                  <button key={idx} onClick={() => { navigate(g.to(i)); setOpen(false); setQ(""); }} data-testid={`search-result-${g.key}`}
                    className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-zinc-200 transition-colors hover:bg-zinc-900">
                    <span className="truncate">{g.title(i)}</span><ArrowRight className="h-3.5 w-3.5 text-zinc-500" />
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
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [briefOpen, setBriefOpen] = useState(false);
  useEffect(() => {
    dashboardApi.executive().then(setData).catch((e) => toast.error(e.message)).finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (!user) return;
    const key = `mb_seen_${user.id}_${new Date().toISOString().slice(0, 10)}`;
    if (!localStorage.getItem(key)) { setBriefOpen(true); localStorage.setItem(key, "1"); }
  }, [user]);
  if (loading || !data) return <DashboardSkeleton />;

  const firstName = (user?.firstName || (user?.email || "").split("@")[0] || "").trim();
  const { hero } = data;

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <OnboardingChecklist />
      <DemoDataBanner />

      {/* Hero */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-2xl font-bold tracking-tight text-zinc-50 sm:text-3xl">
            {hero.greeting}{firstName ? `, ${firstName}` : ""}
          </motion.h1>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1" data-testid="hero-brief">
            {(hero.brief_lines || []).slice(0, 3).map((l, i) => (
              <span key={i} className="inline-flex items-center gap-1.5 text-xs text-zinc-400" data-testid="hero-brief-line">
                <AiIcon name={l.icon} className="h-3.5 w-3.5 text-violet-400" /> {l.text}
              </span>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <GlobalSearch navigate={navigate} />
          <button onClick={() => setBriefOpen(true)} data-testid="open-morning-brief" className="inline-flex shrink-0 items-center gap-1.5 rounded-xl border border-white/10 bg-zinc-950/80 px-3.5 py-2 text-sm font-medium text-zinc-300 backdrop-blur transition-all hover:border-violet-500/40 hover:text-zinc-100">
            <Sun className="h-4 w-4 text-amber-400" /> Morning Brief
          </button>
          <button onClick={() => navigate("/ai-chat")} data-testid="hero-ask-ai" className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-violet-600 px-3.5 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">
            <Bot className="h-4 w-4" /> Ask AI
          </button>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard id="health" title="Business Health" kpi={data.kpi_cards.health} format={(v) => `${Math.round(v)}`} color="#34d399" delay={0}
          tooltip="Overall health (0–100) from overdue invoices, unanswered leads, stalled deals, overdue tasks, inactive clients, proposal conversion, automation success and AI activity." />
        <KpiCard id="pipeline" title="Pipeline Value" kpi={data.kpi_cards.pipeline} format={money} color="#8b5cf6" delay={0.08}
          tooltip="Total value of your open deals across the sales pipeline." />
        <KpiCard id="hours_saved" title="Hours Saved" kpi={data.kpi_cards.hours_saved} format={(v) => `${v.toFixed(1)}h`} color="#22d3ee" delay={0.16}
          tooltip="Hours Assistify saved you this week across AI documents and executed automations." />
        <KpiCard id="revenue_month" title="Revenue This Month" kpi={data.kpi_cards.revenue_month} format={money} color="#f472b6" delay={0.24}
          tooltip="Revenue from invoices marked paid in the last 30 days." />
      </div>

      {/* Main split */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2"><BusinessPerformanceChart trends={data.trends} /></div>
        <AIExecutiveBrief insights={data.insights} hero={data.hero} health={data.health} />
      </div>

      {/* Bottom split */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <AiActivityTimeline activity={data.ai_activity} />
        <TodayPriorities priorities={data.priorities} total={data.priorities_total} />
      </div>

      <QuickActions />
      <MorningBrief open={briefOpen} onOpenChange={setBriefOpen} />
    </div>
  );
}
