import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Users, FolderKanban, CheckCircle2, ListTodo, FileText, ScrollText, Receipt,
  DollarSign, Loader2, Clock, Search, Plus, UserPlus, Sparkles, FileSignature,
  Rocket, FilePlus2, FileUp, RotateCcw, CircleDot, TrendingUp, ArrowRight, X,
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { dashboardApi } from "@/lib/api";
import { toast } from "sonner";
import OnboardingChecklist from "@/components/OnboardingChecklist";
import DashboardAIAssistant from "@/components/DashboardAIAssistant";
import DashboardOpportunities from "@/components/DashboardOpportunities";

const money = (v) => `$${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
const fmtTime = (d) => d ? new Date(d).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "";
const fmtDue = (d) => d ? new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "No due date";

const kpiDefs = [
  { key: "total_clients", label: "Total Clients", icon: Users, to: "/clients" },
  { key: "active_projects", label: "Active Projects", icon: FolderKanban, to: "/projects" },
  { key: "completed_projects", label: "Completed Projects", icon: CheckCircle2, to: "/projects" },
  { key: "open_tasks", label: "Open Tasks", icon: ListTodo, to: "/tasks" },
  { key: "completed_tasks", label: "Completed Tasks", icon: CheckCircle2, to: "/tasks" },
  { key: "pending_proposals", label: "Pending Proposals", icon: FileText, to: "/projects" },
  { key: "sent_contracts", label: "Sent Contracts", icon: ScrollText, to: "/projects" },
  { key: "outstanding_invoices", label: "Outstanding Invoices", icon: Receipt, to: "/projects" },
  { key: "paid_invoices", label: "Paid Invoices", icon: CheckCircle2, to: "/projects" },
  { key: "revenue", label: "Revenue", icon: DollarSign, to: "/projects", money: true },
];

const activityIcon = {
  project_created: Rocket, task_created: Plus, task_completed: CheckCircle2,
  proposal_generated: FileText, proposal_saved: FilePlus2, proposal_exported: FileUp,
  contract_generated: ScrollText, contract_saved: FilePlus2, contract_exported: FileUp, contract_restored: RotateCcw,
  invoice_generated: Receipt, invoice_saved: FilePlus2, invoice_exported: FileUp, invoice_restored: RotateCcw,
  plan_generated: Sparkles, document_uploaded: FileUp,
};

const statusColor = { "In Progress": "#8b5cf6", Review: "#22d3ee", Completed: "#34d399", Planning: "#f59e0b", Blocked: "#f87171" };
const priorityDot = { High: "bg-red-400", Medium: "bg-amber-400", Low: "bg-zinc-500" };
const PROJECT_STAGES = ["Planning", "In Progress", "Review", "Completed"];

const quickActions = [
  { label: "Create Client", icon: UserPlus, to: "/clients" },
  { label: "Create Project", icon: Plus, to: "/projects" },
  { label: "Generate AI Plan", icon: Sparkles, to: "/projects" },
  { label: "Generate Proposal", icon: FileText, to: "/projects" },
  { label: "Generate Contract", icon: FileSignature, to: "/projects" },
  { label: "Generate Invoice", icon: Receipt, to: "/projects" },
];

function GlobalSearch({ navigate }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!q.trim()) { setResults(null); return; }
    const t = setTimeout(() => {
      dashboardApi.search(q).then((r) => { setResults(r); setOpen(true); }).catch(() => {});
    }, 250);
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

export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi.summary().then(setData).catch((e) => toast.error(e.message)).finally(() => setLoading(false));
  }, []);

  const financeChart = useMemo(() => {
    if (!data) return [];
    const bs = data.financial.by_status || {};
    return ["Draft", "Sent", "Paid", "Overdue", "Cancelled"].map((s) => ({ name: s, total: bs[s]?.total || 0, count: bs[s]?.count || 0 }));
  }, [data]);

  if (loading || !data) {
    return <div className="flex items-center justify-center py-32 text-zinc-500" data-testid="dashboard-loading"><Loader2 className="h-7 w-7 animate-spin" /></div>;
  }

  const { kpis, financial, project_status, recent_activity, upcoming_tasks, recent_clients } = data;
  const totalProjects = Object.values(project_status).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <OnboardingChecklist />
      <GlobalSearch navigate={navigate} />
      <DashboardAIAssistant />
      <DashboardOpportunities />

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {kpiDefs.map((k, i) => (
          <button key={k.key} onClick={() => navigate(k.to)} style={{ animationDelay: `${i * 40}ms` }}
            className="animate-fade-up rounded-xl border border-white/10 bg-zinc-950 p-4 text-left transition-all hover:border-violet-500/40" data-testid={`kpi-${k.key}`}>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-600/15 text-violet-400"><k.icon className="h-4.5 w-4.5" /></div>
            <p className="mt-3 text-xl font-bold tracking-tight text-zinc-50" data-testid={`kpi-value-${k.key}`}>{k.money ? money(kpis[k.key]) : kpis[k.key]}</p>
            <p className="mt-0.5 text-xs text-zinc-500">{k.label}</p>
          </button>
        ))}
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2">
        {quickActions.map((a) => (
          <button key={a.label} onClick={() => navigate(a.to)} data-testid={`quick-${a.label.toLowerCase().replace(/\s/g, "-")}`}
            className="flex items-center gap-2 rounded-lg border border-white/10 bg-zinc-950 px-3.5 py-2 text-sm font-medium text-zinc-300 transition-all hover:border-violet-500/40 hover:text-white">
            <a.icon className="h-4 w-4 text-violet-400" />{a.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Financial summary */}
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5 lg:col-span-2" data-testid="financial-summary">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-100"><DollarSign className="h-4 w-4 text-violet-400" /> Financial Summary</h3>
          </div>
          <div className="mb-4 grid grid-cols-3 gap-3">
            <div className="rounded-lg bg-zinc-900 p-3"><p className="text-xs text-zinc-500">Revenue</p><p className="mt-1 text-lg font-bold text-emerald-400" data-testid="fin-revenue">{money(financial.revenue)}</p></div>
            <div className="rounded-lg bg-zinc-900 p-3"><p className="text-xs text-zinc-500">Outstanding</p><p className="mt-1 text-lg font-bold text-amber-400" data-testid="fin-outstanding">{money(financial.outstanding_revenue)}</p></div>
            <div className="rounded-lg bg-zinc-900 p-3"><p className="text-xs text-zinc-500">Avg Invoice</p><p className="mt-1 text-lg font-bold text-zinc-100" data-testid="fin-avg">{money(financial.average_invoice_value)}</p></div>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={financeChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="name" stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#71717a" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip cursor={{ fill: "rgba(139,92,246,0.08)" }} contentStyle={{ background: "#09090b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }} formatter={(v, n, p) => [`${money(v)} (${p.payload.count})`, "Total"]} />
              <Bar dataKey="total" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                {financeChart.map((e) => <Cell key={e.name} fill={e.name === "Paid" ? "#34d399" : e.name === "Overdue" ? "#f87171" : "#8b5cf6"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Project status */}
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5" data-testid="project-status">
          <h3 className="mb-4 text-sm font-semibold text-zinc-100">Project Status</h3>
          {totalProjects === 0 ? <p className="py-8 text-center text-sm text-zinc-600">No projects yet</p> : (
            <div className="space-y-3">
              {PROJECT_STAGES.map((s) => {
                const count = project_status[s] || 0;
                const pct = totalProjects ? Math.round((count / totalProjects) * 100) : 0;
                return (
                  <div key={s} data-testid={`project-stage-${s.replace(/\s/g, "-")}`}>
                    <div className="mb-1 flex items-center justify-between text-xs"><span className="text-zinc-300">{s}</span><span className="text-zinc-500">{count}</span></div>
                    <div className="h-2 overflow-hidden rounded-full bg-zinc-800"><div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: statusColor[s] }} /></div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Recent activity */}
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5" data-testid="recent-activity">
          <h3 className="mb-4 text-sm font-semibold text-zinc-100">Recent Activity</h3>
          {recent_activity.length === 0 ? <p className="py-6 text-center text-sm text-zinc-600">No activity yet</p> : (
            <div className="space-y-3">
              {recent_activity.map((a, i) => {
                const Icon = activityIcon[a.type] || CircleDot;
                return (
                  <button key={i} onClick={() => a.project_id && navigate(`/projects/${a.project_id}`)} data-testid={`activity-item-${a.type}`}
                    className="flex w-full items-start gap-3 text-left transition-opacity hover:opacity-80">
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-violet-600/15 text-violet-400"><Icon className="h-3.5 w-3.5" /></span>
                    <div className="min-w-0 flex-1"><p className="truncate text-sm text-zinc-200">{a.message}</p><p className="text-xs text-zinc-500">{a.project_name || ""} · {fmtTime(a.created_at)}</p></div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Upcoming tasks */}
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5" data-testid="upcoming-tasks">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-100"><Clock className="h-4 w-4 text-violet-400" /> Upcoming Tasks</h3>
            <button onClick={() => navigate("/tasks")} className="text-xs font-medium text-violet-400 hover:text-violet-300">View all</button>
          </div>
          {upcoming_tasks.length === 0 ? <p className="py-6 text-center text-sm text-zinc-600">No open tasks</p> : (
            <div className="space-y-3">
              {upcoming_tasks.map((t) => (
                <button key={t.id} onClick={() => navigate(t.project_id ? `/projects/${t.project_id}` : "/tasks")} data-testid={`upcoming-task-${t.id}`}
                  className="flex w-full items-start gap-3 text-left transition-opacity hover:opacity-80">
                  <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${priorityDot[t.priority]}`} />
                  <div className="min-w-0 flex-1"><p className="truncate text-sm text-zinc-200">{t.title}</p><p className="text-xs text-zinc-500">{t.project_name || "No project"} · {fmtDue(t.due)} · {t.priority}</p></div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Recent clients */}
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5" data-testid="recent-clients">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-100">Recent Clients</h3>
            <button onClick={() => navigate("/clients")} className="text-xs font-medium text-violet-400 hover:text-violet-300">View all</button>
          </div>
          {recent_clients.length === 0 ? <p className="py-6 text-center text-sm text-zinc-600">No clients yet</p> : (
            <div className="space-y-3">
              {recent_clients.map((c) => (
                <div key={c.id} className="flex items-center gap-3" data-testid={`recent-client-${c.id}`}>
                  <Avatar className="h-9 w-9 border border-white/10"><AvatarFallback className="bg-violet-600/20 text-violet-300">{c.name[0]}</AvatarFallback></Avatar>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-zinc-100">{c.name}</p><p className="truncate text-xs text-zinc-500">{c.projects_count} project{c.projects_count !== 1 && "s"} · {fmtDue(c.created_at)}</p></div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
