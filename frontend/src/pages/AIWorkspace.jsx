import PageIntro from "@/components/PageIntro";
import { useEffect, useMemo, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  Sparkles, Clock, Zap, Gauge, TrendingUp, Search, Loader2, ArrowRight,
  MessageSquare, FolderPlus, BarChart3, FolderOpen, History, Layers,
} from "lucide-react";
import { aiApi } from "@/lib/api";
import { AiIcon, fmtDuration } from "@/components/ai/aiHelpers";
import { useLocale } from "@/context/LocaleContext";
import { formatRelativeTime } from "@/i18n/format";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";

const RANGES = [
  "all", "today", "week", "month",
];
const SORTS = [
  "newest", "oldest", "most_saved",
];

const groupByDay = (items) => {
  const now = new Date();
  const key = (iso) => {
    const d = new Date(iso);
    const days = Math.floor((now.setHours(0, 0, 0, 0) - new Date(iso).setHours(0, 0, 0, 0)) / 86400000);
    if (days <= 0) return "today";
    if (days === 1) return "yesterday";
    if (days <= 7) return "week";
    return "earlier";
  };
  const order = ["today", "yesterday", "week", "earlier"];
  const map = {};
  items.forEach((it) => { (map[key(it.created_at)] ||= []).push(it); });
  return order.filter((k) => map[k]).map((k) => ({ label: k, items: map[k] }));
};

const StatCard = ({ icon: Icon, label, value, accent, testid }) => (
  <div data-testid={testid} className="rounded-2xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-brand-500/30">
    <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${accent}`}><Icon className="h-4 w-4" /></div>
    <p className="mt-3 text-2xl font-extrabold tracking-tight text-zinc-50">{value}</p>
    <p className="mt-0.5 text-xs text-zinc-500">{label}</p>
  </div>
);

const Sparkline = ({ data, locale }) => {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div className="flex items-end gap-1.5" data-testid="ai-workspace-sparkline">
      {data.map((d) => (
        <div key={d.date} className="flex flex-1 flex-col items-center gap-1.5" title={`${d.date}: ${d.count}`}>
          <div className="w-full rounded-t bg-gradient-to-t from-brand-600/40 to-brand-400/80 transition-all"
            style={{ height: `${8 + (d.count / max) * 48}px` }} />
          <span className="text-[9px] text-zinc-600">{new Date(d.date).toLocaleDateString(locale === "nl" ? "nl-NL" : "en-US", { weekday: "narrow" })}</span>
        </div>
      ))}
    </div>
  );
};

const QUICK = [
  { icon: MessageSquare, key: "copilot", to: "/ai-chat" },
  { icon: FolderPlus, key: "project", to: "/projects" },
  { icon: FolderOpen, key: "documents", to: "/documents" },
  { icon: BarChart3, key: "analytics", to: "/analytics" },
];

export default function AIWorkspace() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [insights, setInsights] = useState([]);
  const [versions, setVersions] = useState([]);
  const [results, setResults] = useState(null);
  const [types, setTypes] = useState([]);
  const [searching, setSearching] = useState(true);
  const [compareDoc, setCompareDoc] = useState(null);

  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [range, setRange] = useState("all");
  const [sort, setSort] = useState("newest");

  useEffect(() => {
    aiApi.workspaceStats().then(setStats).catch(() => setStats(null));
    aiApi.insights().then(setInsights).catch(() => setInsights([]));
    aiApi.workspaceVersions().then(setVersions).catch(() => setVersions([]));
  }, []);

  const runSearch = useCallback(() => {
    setSearching(true);
    const params = { sort, range };
    if (q) params.q = q;
    if (type) params.type = type;
    aiApi.workspaceSearch(params)
      .then((r) => { setResults(r.items); if (r.types) setTypes(r.types); })
      .catch(() => setResults([]))
      .finally(() => setSearching(false));
  }, [q, type, range, sort]);

  useEffect(() => {
    const t = setTimeout(runSearch, q ? 300 : 0);
    return () => clearTimeout(t);
  }, [runSearch, q]);

  const groups = useMemo(() => groupByDay(results || []), [results]);

  return (
    <div className="space-y-8" data-testid="ai-workspace-page">
      <PageIntro title={t("pages.aiWorkspace.title")} description={t("pages.aiWorkspace.description")} />

      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2.5 text-3xl font-bold tracking-tight text-zinc-50">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 glow-brand"><Sparkles className="h-5 w-5 text-white" /></span>
            {t("aiWorkspace.title")}
          </h1>
          <p className="mt-1.5 text-sm text-zinc-400">
            {t("aiWorkspace.intro")}
          </p>
        </div>
        <div className="rounded-xl border border-brand-500/20 bg-brand-500/[0.06] px-4 py-2.5 text-right">
          <p className="flex items-center justify-end gap-1.5 text-xs text-zinc-500"><Clock className="h-3.5 w-3.5" /> {t("aiWorkspace.lifetimeSaved")}</p>
          <p className="bg-gradient-to-r from-brand-300 to-cyan-300 bg-clip-text text-xl font-extrabold text-transparent" data-testid="ai-workspace-lifetime-saved">
            {stats ? fmtDuration(stats.total_time_saved) : "—"}
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5" data-testid="ai-workspace-stats">
        <StatCard testid="stat-total-actions" icon={Sparkles} label={t("aiWorkspace.stats.actions")} accent="bg-brand-600/15 text-brand-300" value={stats ? stats.total_actions : "—"} />
        <StatCard testid="stat-week" icon={TrendingUp} label={t("aiWorkspace.stats.week")} accent="bg-cyan-500/15 text-cyan-300" value={stats ? stats.week_count : "—"} />
        <StatCard testid="stat-confidence" icon={Gauge} label={t("aiWorkspace.stats.confidence")} accent="bg-emerald-500/15 text-emerald-300" value={stats ? `${stats.avg_confidence}%` : "—"} />
        <StatCard testid="stat-gen-time" icon={Zap} label={t("aiWorkspace.stats.speed")} accent="bg-amber-500/15 text-amber-300" value={stats && stats.avg_gen_ms ? `${(stats.avg_gen_ms / 1000).toFixed(1)}s` : "—"} />
        <div className="col-span-2 rounded-2xl border border-white/10 bg-zinc-950 p-4 md:col-span-3 lg:col-span-1">
          <p className="mb-2 text-xs text-zinc-500">{t("aiWorkspace.lastDays", { count: 7 })}</p>
          {stats ? <Sparkline data={stats.sparkline} locale={locale} /> : <div className="h-14" />}
        </div>
      </div>

      {/* Quick actions */}
      <div>
        <p className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">{t("aiWorkspace.quick.title")}</p>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4" data-testid="ai-workspace-quick-actions">
          {QUICK.map((a) => (
            <button key={a.to} onClick={() => navigate(a.to)} data-testid={`quick-action-${a.to.replace("/", "")}`}
              className="group flex items-center gap-3 rounded-xl border border-white/10 bg-zinc-950 p-3.5 text-left transition-all hover:border-brand-500/40 hover:bg-brand-500/[0.04]">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600/15 text-brand-300 transition-transform group-hover:scale-105"><a.icon className="h-4 w-4" /></span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-zinc-100">{t(`aiWorkspace.quick.${a.key}.label`)}</span>
                <span className="block truncate text-xs text-zinc-500">{t(`aiWorkspace.quick.${a.key}.hint`)}</span>
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: search + filters + timeline */}
        <div className="space-y-4 lg:col-span-2">
          <div className="rounded-2xl border border-white/10 bg-zinc-950 p-4">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <input value={q} onChange={(e) => setQ(e.target.value)} data-testid="ai-workspace-search-input"
                placeholder={t("aiWorkspace.search")}
                className="w-full rounded-xl border border-white/10 bg-zinc-900 py-2.5 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-brand-500/50 focus:outline-none" />
            </div>
            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
              <select value={type} onChange={(e) => setType(e.target.value)} data-testid="ai-workspace-filter-type"
                className="rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 focus:border-brand-500/50 focus:outline-none">
                <option value="">{t("aiWorkspace.filters.allTypes")}</option>
                {(types.length ? types : []).map((t) => <option key={t.type} value={t.type}>{t.label}</option>)}
              </select>
              <select value={range} onChange={(e) => setRange(e.target.value)} data-testid="ai-workspace-filter-range"
                className="rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 focus:border-brand-500/50 focus:outline-none">
                {RANGES.map((r) => <option key={r} value={r}>{t(`aiWorkspace.ranges.${r}`)}</option>)}
              </select>
              <select value={sort} onChange={(e) => setSort(e.target.value)} data-testid="ai-workspace-filter-sort"
                className="rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 focus:border-brand-500/50 focus:outline-none">
                {SORTS.map((s) => <option key={s} value={s}>{t(`aiWorkspace.sorts.${s}`)}</option>)}
              </select>
            </div>
          </div>

          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
            <History className="h-3.5 w-3.5" /> {t("aiWorkspace.timeline")}
            {results && <span className="rounded-full bg-white/5 px-2 py-0.5 text-[10px] font-medium text-zinc-400">{results.length}</span>}
          </p>

          {searching && !results ? (
            <div className="flex items-center justify-center py-16 text-zinc-600" data-testid="ai-workspace-timeline-loading"><Loader2 className="h-6 w-6 animate-spin" /></div>
          ) : !results || results.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 bg-zinc-950 px-4 py-14 text-center" data-testid="ai-workspace-timeline-empty">
              <Sparkles className="mx-auto h-8 w-8 text-zinc-700" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium text-zinc-300">{t("aiWorkspace.empty.title")}</p>
              <p className="mx-auto mt-1 max-w-sm text-xs text-zinc-500">
                {t("aiWorkspace.empty.description")}
              </p>
              <button type="button" onClick={() => navigate("/ai-chat")} data-testid="ai-workspace-empty-action" className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500">
                {t("aiWorkspace.empty.action")} <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          ) : (
            groups.map((g) => (
              <div key={g.label} data-testid={`ai-workspace-group-${g.label.replace(/\s/g, "-").toLowerCase()}`}>
                <p className="mb-2 mt-1 text-[11px] font-semibold uppercase tracking-wide text-zinc-600">{t(`aiWorkspace.groups.${g.label}`)}</p>
                <div className="space-y-2">
                  {g.items.map((a) => (
                    <div key={a.id} data-testid="ai-workspace-item"
                      onClick={() => a.related?.project_id && navigate(`/projects/${a.related.project_id}`)}
                      className={`flex items-start gap-3 rounded-xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-brand-500/30 ${a.related?.project_id ? "cursor-pointer" : ""}`}>
                      <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-600/15 text-brand-300"><AiIcon name={a.icon} className="h-4 w-4" /></span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="truncate text-sm font-semibold text-zinc-100">{a.title}</p>
                          <span className="shrink-0 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-400">{t("aiWorkspace.minutesSaved", { count: a.time_saved })}</span>
                          {a.gen_ms ? <span className="shrink-0 rounded-full bg-white/5 px-2 py-0.5 text-[10px] font-medium text-zinc-400">{(a.gen_ms / 1000).toFixed(1)}s</span> : null}
                        </div>
                        <p className="mt-1 text-sm leading-snug text-zinc-400">{a.explanation}</p>
                        <p className="mt-1.5 text-xs text-zinc-600">{a.source_page} · {formatRelativeTime(a.created_at, locale, t)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Right: insights + version compare */}
        <div className="space-y-6">
          <div>
            <p className="mb-2.5 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500"><Zap className="h-3.5 w-3.5" /> {t("aiWorkspace.insights")}</p>
            {insights.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5 text-center text-xs text-zinc-500" data-testid="ai-workspace-insights-empty">
                {t("aiWorkspace.noInsights")}
              </div>
            ) : (
              <div className="space-y-2" data-testid="ai-workspace-insights">
                {insights.map((it) => (
                  <div key={it.id} className="rounded-xl border border-white/10 bg-zinc-950 p-3.5 transition-all hover:border-brand-500/30" data-testid="ai-workspace-insight">
                    <div className="flex items-start gap-2.5">
                      <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${it.severity === "high" ? "bg-rose-500/15 text-rose-300" : it.severity === "medium" ? "bg-amber-500/15 text-amber-300" : "bg-zinc-500/15 text-zinc-300"}`}><AiIcon name={it.icon} className="h-3.5 w-3.5" /></span>
                      <p className="text-xs leading-snug text-zinc-300">{it.explanation}</p>
                    </div>
                    <button onClick={() => navigate(it.link)} className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-brand-300 hover:text-brand-200">
                      {it.action_label} <ArrowRight className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <p className="mb-2.5 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500"><Layers className="h-3.5 w-3.5" /> {t("aiWorkspace.versions.title")}</p>
            {versions.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5 text-center text-xs text-zinc-500" data-testid="ai-workspace-versions-empty">
                {t("aiWorkspace.versions.empty")}
              </div>
            ) : (
              <div className="space-y-2" data-testid="ai-workspace-versions">
                {versions.map((v) => (
                  <button key={v.key} onClick={() => setCompareDoc(v)} data-testid="ai-workspace-version-item"
                    className="flex w-full items-center gap-3 rounded-xl border border-white/10 bg-zinc-950 p-3.5 text-left transition-all hover:border-brand-500/30">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-600/15 text-brand-300"><AiIcon name={v.icon} className="h-4 w-4" /></span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-zinc-100">{v.project_name}</span>
                      <span className="block text-xs text-zinc-500">{v.label}</span>
                    </span>
                    <span className="shrink-0 rounded-full bg-white/5 px-2 py-0.5 text-[10px] font-medium text-zinc-300">{t("aiWorkspace.versions.count", { count: v.versions.length })}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <Dialog open={!!compareDoc} onOpenChange={(o) => !o && setCompareDoc(null)}>
        <DialogContent className="border-white/10 bg-zinc-950" data-testid="ai-workspace-compare-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-zinc-100">
              {compareDoc && <AiIcon name={compareDoc.icon} className="h-4 w-4 text-brand-300" />}
              {compareDoc?.project_name} — {compareDoc?.label}
            </DialogTitle>
            <DialogDescription className="text-zinc-500">{t("aiWorkspace.versions.description")}</DialogDescription>
          </DialogHeader>
          {compareDoc && (
            <div className="space-y-3">
              <div className="max-h-72 space-y-2 overflow-y-auto">
                {compareDoc.versions.map((ver, i) => (
                  <div key={ver.version} className="flex items-center gap-3 rounded-lg border border-white/10 bg-zinc-900 p-3">
                    <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${i === 0 ? "bg-brand-600 text-white" : "bg-white/5 text-zinc-400"}`}>v{ver.version}</span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-zinc-200">{ver.title || t("aiWorkspace.versions.version", { version: ver.version })}</p>
                      <p className="text-xs text-zinc-600">{formatRelativeTime(ver.created_at, locale, t)}{ver.status ? ` · ${ver.status}` : ""}</p>
                    </div>
                    {i === 0 && <span className="shrink-0 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-400">{t("aiWorkspace.versions.current")}</span>}
                  </div>
                ))}
              </div>
              <button onClick={() => { navigate(compareDoc.link); setCompareDoc(null); }} data-testid="ai-workspace-open-compare"
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-500">
                {t("aiWorkspace.versions.openCompare")} <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
