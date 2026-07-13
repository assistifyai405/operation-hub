import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, ArrowRight, X } from "lucide-react";
import { toast } from "sonner";
import { dashboardApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import OnboardingChecklist from "@/components/OnboardingChecklist";
import DemoDataBanner from "@/components/DemoDataBanner";
import { ExecHero } from "@/components/dashboard/ExecHero";
import { HealthScore } from "@/components/dashboard/HealthScore";
import { RevenueSnapshot } from "@/components/dashboard/RevenueSnapshot";
import { ExecInsights } from "@/components/dashboard/ExecInsights";
import { TodayPriorities } from "@/components/dashboard/TodayPriorities";
import { AiActivityTimeline } from "@/components/dashboard/AiActivityTimeline";
import { WorkspaceSnapshot } from "@/components/dashboard/WorkspaceSnapshot";
import { RecentDocuments } from "@/components/dashboard/RecentDocuments";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { Skeleton } from "@/components/dashboard/execShared";

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
    { key: "documents", label: "Documents", items: results.documents, to: () => "/documents", title: (i) => i.name },
  ].filter((g) => g.items?.length) : [];

  return (
    <div className="relative" data-testid="dashboard-search">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
      <input value={q} onChange={(e) => setQ(e.target.value)} onFocus={() => results && setOpen(true)}
        data-testid="dashboard-search-input" placeholder="Search clients, projects, invoices, contracts, proposals…"
        className="w-full rounded-xl border border-white/10 bg-zinc-950 py-2.5 pl-10 pr-9 text-sm text-zinc-200 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
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
      <Skeleton className="h-10 w-72" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Skeleton className="h-44 lg:col-span-2" />
        <div className="space-y-3"><Skeleton className="h-[52px]" /><Skeleton className="h-[52px]" /><Skeleton className="h-[52px]" /></div>
      </div>
      <Skeleton className="h-48" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">{[...Array(6)].map((_, i) => <Skeleton key={i} className="h-20" />)}</div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-32" />)}</div>
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi.executive().then(setData).catch((e) => toast.error(e.message)).finally(() => setLoading(false));
  }, []);

  if (loading || !data) return <DashboardSkeleton />;

  const firstName = (user?.firstName || (user?.email || "").split("@")[0] || "").trim();

  return (
    <div className="space-y-8" data-testid="dashboard-page">
      <OnboardingChecklist />
      <DemoDataBanner />
      <GlobalSearch navigate={navigate} />
      <ExecHero hero={data.hero} userName={firstName} />
      <HealthScore health={data.health} />
      <RevenueSnapshot revenue={data.revenue} />
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <ExecInsights insights={data.insights} />
        <TodayPriorities priorities={data.priorities} total={data.priorities_total} />
      </div>
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <AiActivityTimeline activity={data.ai_activity} />
        <WorkspaceSnapshot workspace={data.workspace} />
      </div>
      <RecentDocuments documents={data.documents} />
      <QuickActions />
    </div>
  );
}
