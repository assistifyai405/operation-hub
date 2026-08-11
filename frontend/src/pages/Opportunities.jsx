import PageIntro from "@/components/PageIntro";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Loader2, Sparkles, Target, CheckCircle2 } from "lucide-react";
import { opportunitiesApi } from "@/lib/api";
import { OpportunityCard } from "@/components/opportunities/OpportunityCard";
import { HealthWidget } from "@/components/opportunities/HealthWidget";
import { useOpportunityActions } from "@/components/opportunities/shared";

const FILTERS = [
  { v: "all", label: "All" }, { v: "Critical", label: "Critical" }, { v: "High", label: "High" },
  { v: "Medium", label: "Medium" }, { v: "Low", label: "Low" },
];

export default function Opportunities() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  const load = () => {
    setLoading(true);
    Promise.all([
      opportunitiesApi.list().then(setData).catch(() => setData({ items: [], counts: {}, total: 0, total_time_saved: 0 })),
      opportunitiesApi.health().then(setHealth).catch(() => setHealth(null)),
    ]).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const { run, dismiss } = useOpportunityActions(load);
  const items = (data?.items || []).filter((i) => filter === "all" || i.priority === filter);

  return (
    <div className="space-y-6" data-testid="opportunities-page">
      <PageIntro title={t("pages.opportunities.title")} description={t("pages.opportunities.description")} helpModule="opportunities" help={t("help.opportunities")} />

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2.5 text-3xl font-bold tracking-tight text-zinc-50">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 glow-brand"><Target className="h-5 w-5 text-white" /></span>
            Opportunities
          </h1>
          <p className="mt-1.5 text-sm text-zinc-400">
            AI-suggested next actions from your real workspace data — not the same as Pipeline deals or CRM contacts.
          </p>
        </div>
        {data && (
          <div className="rounded-xl border border-brand-500/20 bg-brand-500/[0.06] px-4 py-2.5 text-right">
            <p className="text-xs text-zinc-500">Time you could save</p>
            <p className="bg-gradient-to-r from-brand-300 to-cyan-300 bg-clip-text text-xl font-extrabold text-transparent" data-testid="opp-total-saved">
              {Math.round(data.total_time_saved / 60) ? `${Math.floor(data.total_time_saved / 60)}h ${data.total_time_saved % 60}m` : `${data.total_time_saved}m`}
            </p>
          </div>
        )}
      </div>

      <HealthWidget data={health} loading={loading} />

      <div className="flex flex-wrap items-center gap-2" data-testid="opportunity-filters">
        {FILTERS.map((f) => {
          const count = f.v === "all" ? (data?.total || 0) : (data?.counts?.[f.v.toLowerCase()] || 0);
          return (
            <button key={f.v} onClick={() => setFilter(f.v)} data-testid={`opp-filter-${f.v.toLowerCase()}`}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all ${filter === f.v ? "border-brand-500 bg-brand-600/15 text-brand-200" : "border-white/10 bg-zinc-900 text-zinc-400 hover:text-zinc-200"}`}>
              {f.label} <span className="rounded-full bg-white/10 px-1.5 text-[10px]">{count}</span>
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-600"><Loader2 className="h-7 w-7 animate-spin" /></div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 bg-zinc-950 px-4 py-16 text-center" data-testid="opportunities-empty">
          <CheckCircle2 className={`mx-auto h-9 w-9 ${health?.has_workspace_data === false ? "text-zinc-600" : "text-emerald-500"}`} aria-hidden="true" />
          <p className="mt-3 text-sm font-semibold text-zinc-200">
            {filter !== "all"
              ? `No ${filter.toLowerCase()}-priority items`
              : health?.has_workspace_data === false
                ? "No opportunities yet"
                : "You're all caught up"}
          </p>
          <p className="mx-auto mt-1 max-w-sm text-xs text-zinc-500">
            {filter !== "all"
              ? "Assistify didn't find anything that needs your attention here."
              : health?.has_workspace_data === false
                ? "Opportunities come from real clients, projects, overdue tasks, and pipeline deals. Add workspace data to see recommendations — nothing is invented."
                : "Assistify didn't find anything that needs your attention here. Nice work."}
          </p>
          {filter === "all" && health?.has_workspace_data === false && (
            <button type="button" onClick={() => navigate("/clients")} data-testid="opportunities-empty-action" className="mt-5 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500">
              Create your first client
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {items.map((it) => <OpportunityCard key={it.id} item={it} onRun={run} onDismiss={dismiss} />)}
        </div>
      )}
    </div>
  );
}
