import PageIntro from "@/components/PageIntro";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  Brain, Search, Sparkles, Loader2, Pin, PinOff, Pencil, Trash2, Power, PowerOff,
  Send, RefreshCw, GitMerge, X, Plus, Clock, TrendingUp, Zap,
} from "lucide-react";
import { memoryApi } from "@/lib/api";
import { AiIcon } from "@/components/ai/aiHelpers";
import { useLocale } from "@/context/LocaleContext";
import { formatRelativeTime } from "@/i18n/format";

const confColor = (c) => (c >= 85 ? "bg-emerald-500" : c >= 65 ? "bg-brand-500" : c >= 45 ? "bg-yellow-500" : "bg-orange-500");
const inputCls = "w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:border-brand-500/50 focus:outline-none";
const CATEGORIES = ["Business", "Writing Style", "Pricing", "Customers", "Projects", "Processes", "Frequently Used Terms", "Products", "Services", "Brand Voice", "Policies", "Preferences", "Relationships"];

function MemoryCard({ m, onChange, selectMode, selected, onSelect }) {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const act = async (fn, ok) => { try { await fn(); onChange(); if (ok) toast.success(ok); } catch (e) { toast.error(e.message); } };
  return (
    <div data-testid="memory-card" className={`group rounded-2xl border bg-zinc-950 p-4 transition-all animate-fade-up ${selected ? "border-brand-500" : "border-white/10 hover:border-brand-500/30"} ${m.learning_enabled === false ? "opacity-60" : ""}`}>
      <div className="flex items-start gap-3">
        {selectMode && <input type="checkbox" checked={selected} onChange={onSelect} data-testid="memory-select" className="mt-1 h-4 w-4 accent-brand-500" />}
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-600/15 text-brand-300"><AiIcon name={m.icon} className="h-4 w-4" /></span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {m.pinned && <Pin className="h-3.5 w-3.5 text-brand-400" />}
            <p className="text-sm font-semibold text-zinc-100">{m.title}</p>
          </div>
          <p className="mt-0.5 text-xs text-zinc-500">{m.category}</p>
          {m.content && <p className="mt-1.5 text-sm leading-snug text-zinc-400">{m.content}</p>}
          <div className="mt-2.5">
            <div className="mb-1 flex items-center justify-between text-[11px] text-zinc-500"><span>{t("knowledge.confidence")}</span><span>{m.confidence}%</span></div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/5"><div className={`h-full rounded-full ${confColor(m.confidence)} transition-all`} style={{ width: `${m.confidence}%` }} /></div>
          </div>
          <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-600">
            <span>{m.source}</span><span>· {t("knowledge.used", { count: m.times_used })}</span><span>· {formatRelativeTime(m.updated_at, locale, t)}</span>
          </div>
          <div className="mt-2.5 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            <IconBtn testid="memory-pin" onClick={() => act(() => memoryApi.pin(m.id, !m.pinned), m.pinned ? t("knowledge.toasts.unpinned") : t("knowledge.toasts.pinned"))} title={m.pinned ? t("knowledge.actions.unpin") : t("knowledge.actions.pin")}>{m.pinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}</IconBtn>
            <IconBtn testid="memory-edit" onClick={() => onChange(m)} title={t("common.edit")}><Pencil className="h-3.5 w-3.5" /></IconBtn>
            <IconBtn testid="memory-toggle-learning" onClick={() => act(() => memoryApi.toggleLearning(m.id, m.learning_enabled === false), m.learning_enabled === false ? t("knowledge.toasts.learningOn") : t("knowledge.toasts.learningPaused"))} title={t("knowledge.actions.toggleLearning")}>{m.learning_enabled === false ? <PowerOff className="h-3.5 w-3.5" /> : <Power className="h-3.5 w-3.5" />}</IconBtn>
            <IconBtn testid="memory-delete" onClick={() => window.confirm(t("knowledge.confirmDelete")) && act(() => memoryApi.remove(m.id), t("knowledge.toasts.deleted"))} title={t("common.delete")} danger><Trash2 className="h-3.5 w-3.5" /></IconBtn>
          </div>
        </div>
      </div>
    </div>
  );
}

const IconBtn = ({ children, onClick, title, testid, danger }) => (
  <button onClick={onClick} title={title} data-testid={testid} className={`rounded-lg p-1.5 text-zinc-500 hover:bg-white/5 ${danger ? "hover:text-red-400" : "hover:text-zinc-200"}`}>{children}</button>
);

function EditModal({ mem, onClose, onSaved }) {
  const { t } = useTranslation();
  const isNew = !mem?.id;
  const [f, setF] = useState({ title: mem?.title || "", category: mem?.category || "Business", content: mem?.content || "", confidence: mem?.confidence ?? 80, keywords: (mem?.keywords || []).join(", ") });
  const set = (k, v) => setF((s) => ({ ...s, [k]: v }));
  const save = async () => {
    const body = { title: f.title, category: f.category, content: f.content, confidence: Number(f.confidence), keywords: String(f.keywords).split(",").map((x) => x.trim()).filter(Boolean) };
    try { isNew ? await memoryApi.create(body) : await memoryApi.update(mem.id, body); toast.success(t("knowledge.toasts.saved")); onSaved(); } catch (e) { toast.error(e.message); }
  };
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4" data-testid="memory-edit-modal">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in" onClick={onClose} />
      <div className="relative w-full max-w-lg rounded-2xl border border-white/10 bg-zinc-950 p-5 animate-fade-up">
        <div className="mb-4 flex items-center justify-between"><h3 className="text-lg font-bold text-zinc-50">{isNew ? t("knowledge.modal.new") : t("knowledge.modal.edit")}</h3><button onClick={onClose} aria-label={t("common.close")} className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/5"><X className="h-5 w-5" /></button></div>
        <div className="space-y-3">
          <input value={f.title} onChange={(e) => set("title", e.target.value)} placeholder={t("knowledge.modal.title")} data-testid="memory-title-input" className={inputCls} />
          <select value={f.category} onChange={(e) => set("category", e.target.value)} data-testid="memory-category-select" className={inputCls}>{CATEGORIES.map((c) => <option key={c} value={c}>{t(`knowledge.categories.${c}`, { defaultValue: c })}</option>)}</select>
          <textarea value={f.content} onChange={(e) => set("content", e.target.value)} rows={3} placeholder={t("knowledge.modal.content")} className={inputCls} />
          <div><div className="mb-1 flex justify-between text-xs text-zinc-500"><span>{t("knowledge.confidence")}</span><span>{f.confidence}%</span></div><input type="range" min="0" max="100" value={f.confidence} onChange={(e) => set("confidence", e.target.value)} className="w-full accent-brand-500" /></div>
          <input value={f.keywords} onChange={(e) => set("keywords", e.target.value)} placeholder={t("knowledge.modal.keywords")} className={inputCls} />
          <button onClick={save} data-testid="memory-save" className="w-full rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-500">{t("knowledge.modal.save")}</button>
        </div>
      </div>
    </div>
  );
}

export default function KnowledgeBrain() {
  const { t } = useTranslation();
  const [mems, setMems] = useState([]);
  const [stats, setStats] = useState(null);
  const [insights, setInsights] = useState([]);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [sort, setSort] = useState("recent");
  const [editing, setEditing] = useState(null);
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState([]);
  const [ask, setAsk] = useState("");
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [genProfile, setGenProfile] = useState(false);

  const load = useCallback(() => {
    memoryApi.memories({ q, category: cat, sort }).then(setMems).catch(() => setMems([]));
    memoryApi.stats().then(setStats).catch(() => {});
  }, [q, cat, sort]);
  useEffect(() => {
    const t = setTimeout(load, q ? 250 : 0);
    return () => clearTimeout(t);
  }, [load, q]);
  useEffect(() => {
    setLoading(true);
    Promise.all([memoryApi.memories({ sort: "recent" }).then(setMems), memoryApi.stats().then(setStats),
      memoryApi.insights().then(setInsights).catch(() => setInsights([])),
      memoryApi.businessProfile().then((p) => setProfile(p?.sections ? p : null)).catch(() => {})]).finally(() => setLoading(false));
  }, []);

  const doAsk = async () => {
    if (!ask.trim()) return; setAsking(true); setAnswer(null);
    try { const r = await memoryApi.ask(ask); setAnswer(r.answer); } catch (e) { toast.error(e.message); } finally { setAsking(false); }
  };
  const analyze = async () => {
    setAnalyzing(true);
    try { const r = await memoryApi.analyze(); toast.success(r.learned ? t("knowledge.toasts.learned", { count: r.learned }) : t("knowledge.toasts.noPatterns")); load(); } catch (e) { toast.error(e.message); } finally { setAnalyzing(false); }
  };
  const generateProfile = async () => {
    setGenProfile(true);
    try { setProfile(await memoryApi.generateProfile()); toast.success(t("knowledge.toasts.profileUpdated")); } catch (e) { toast.error(e.message); } finally { setGenProfile(false); }
  };
  const doMerge = async () => {
    if (selected.length < 2) { toast.error(t("knowledge.toasts.selectTwo")); return; }
    const first = mems.find((m) => m.id === selected[0]);
    try { await memoryApi.merge({ ids: selected, title: first.title, category: first.category }); toast.success(t("knowledge.toasts.merged")); setSelected([]); setSelectMode(false); load(); } catch (e) { toast.error(e.message); }
  };

  const onCardChange = (maybeMem) => { if (maybeMem && maybeMem.id) setEditing(maybeMem); else load(); };

  return (
    <div className="space-y-6" data-testid="knowledge-brain-page">
      <PageIntro title={t("pages.knowledgeBrain.title")} description={t("pages.knowledgeBrain.description")} help={t("help.knowledgeBrain")} />

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2.5 text-3xl font-bold tracking-tight text-zinc-50">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 glow-brand"><Brain className="h-5 w-5 text-white" /></span>
            {t("knowledge.title")}
          </h1>
          <p className="mt-1.5 text-sm text-zinc-400">
            {t("knowledge.intro")}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={analyze} disabled={analyzing} data-testid="analyze-learning" className="relative inline-flex items-center gap-1.5 rounded-lg border border-brand-500/30 bg-brand-500/[0.06] px-3.5 py-2 text-sm font-semibold text-brand-200 hover:bg-brand-500/15 disabled:opacity-60">
            {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} {t("knowledge.actions.analyze")}
            {stats?.pending_learning > 0 && <span className="absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-brand-500 px-1 text-[10px] font-bold text-white">{stats.pending_learning}</span>}
          </button>
          <button onClick={() => setEditing({})} data-testid="new-memory" className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3.5 py-2 text-sm font-semibold text-white hover:bg-brand-500"><Plus className="h-4 w-4" /> {t("knowledge.actions.memory")}</button>
        </div>
      </div>

      {/* Ask your Brain */}
      <div className="rounded-2xl border border-brand-500/20 bg-brand-500/[0.05] p-4" data-testid="ask-brain">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-brand-300" />
          <input value={ask} onChange={(e) => setAsk(e.target.value)} onKeyDown={(e) => e.key === "Enter" && doAsk()} data-testid="ask-input"
            placeholder={t("knowledge.askPlaceholder")} className="flex-1 bg-transparent text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none" />
          <button onClick={doAsk} disabled={asking} data-testid="ask-send" className="rounded-lg bg-brand-600 p-2 text-white hover:bg-brand-500 disabled:opacity-50">{asking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</button>
        </div>
        {answer && <p className="mt-3 border-t border-white/10 pt-3 text-sm text-zinc-200" data-testid="ask-answer">{answer}</p>}
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4" data-testid="brain-stats">
          <Stat label={t("knowledge.stats.memories")} value={stats.total} />
          <Stat label={t("knowledge.stats.avgConfidence")} value={`${stats.avg_confidence}%`} />
          <Stat label={t("knowledge.stats.timesReused")} value={stats.total_uses} />
          <Stat label={t("knowledge.stats.learnedToday")} value={stats.learned_today.length} />
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: memories */}
        <div className="space-y-4 lg:col-span-2">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <input value={q} onChange={(e) => setQ(e.target.value)} data-testid="memory-search" placeholder={t("knowledge.search")} className="w-full rounded-lg border border-white/10 bg-zinc-900 py-2 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-brand-500/50 focus:outline-none" />
            </div>
            <select value={sort} onChange={(e) => setSort(e.target.value)} data-testid="memory-sort" className="rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 focus:outline-none">
              <option value="recent">{t("knowledge.sort.recent")}</option><option value="used">{t("knowledge.sort.used")}</option><option value="confidence">{t("knowledge.sort.confidence")}</option><option value="created">{t("knowledge.sort.newest")}</option>
            </select>
            <button onClick={() => { setSelectMode(!selectMode); setSelected([]); }} data-testid="merge-mode" className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm ${selectMode ? "border-brand-500 bg-brand-600/15 text-brand-200" : "border-white/10 bg-zinc-900 text-zinc-400"}`}><GitMerge className="h-4 w-4" /> {t("knowledge.actions.merge")}</button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <Chip active={!cat} onClick={() => setCat("")}>{t("knowledge.all")}</Chip>
            {(stats?.by_category || []).map((c) => <Chip key={c.category} active={cat === c.category} onClick={() => setCat(c.category)}>{c.category} <span className="opacity-60">{c.count}</span></Chip>)}
          </div>
          {selectMode && selected.length > 0 && (
            <div className="flex items-center justify-between rounded-lg border border-brand-500/30 bg-brand-500/[0.06] px-3 py-2 text-sm text-brand-200">
              <span>{t("knowledge.selected", { count: selected.length })}</span>
              <button onClick={doMerge} data-testid="merge-confirm" className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-500">{t("knowledge.actions.mergeOne")}</button>
            </div>
          )}
          {loading ? <div className="flex justify-center py-16 text-zinc-600"><Loader2 className="h-6 w-6 animate-spin" /></div>
            : mems.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 bg-zinc-950 px-4 py-14 text-center" data-testid="memory-empty">
                <Brain className="mx-auto h-9 w-9 text-zinc-600" aria-hidden="true" />
                <p className="mt-3 text-sm font-semibold text-zinc-200">{t("knowledge.empty.title")}</p>
                <p className="mx-auto mt-1 max-w-md text-xs text-zinc-500">
                  {t("knowledge.empty.description")}
                </p>
                <button type="button" onClick={() => setEditing({})} data-testid="memory-empty-action" className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500">
                  <Plus className="h-4 w-4" aria-hidden="true" /> {t("knowledge.empty.action")}
                </button>
              </div>
            )
            : <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">{mems.map((m) => <MemoryCard key={m.id} m={m} onChange={onCardChange} selectMode={selectMode} selected={selected.includes(m.id)} onSelect={() => setSelected((s) => s.includes(m.id) ? s.filter((x) => x !== m.id) : [...s, m.id])} />)}</div>}
        </div>

        {/* Right: insights + profile */}
        <div className="space-y-6">
          <div>
            <p className="mb-2.5 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500"><Zap className="h-3.5 w-3.5 text-brand-400" /> {t("knowledge.insights")}</p>
            {insights.length === 0 ? <div className="rounded-2xl border border-white/10 bg-zinc-950 p-4 text-center text-xs text-zinc-500">{t("knowledge.noInsights")}</div>
              : <div className="space-y-2" data-testid="brain-insights">{insights.map((it, i) => (
                  <div key={i} className="rounded-xl border border-white/10 bg-zinc-950 p-3.5" data-testid="brain-insight">
                    <div className="flex items-start gap-2.5"><span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-600/15 text-brand-300"><AiIcon name={it.icon} className="h-3.5 w-3.5" /></span>
                      <div><p className="text-sm font-medium text-zinc-200">{it.insight}</p><p className="mt-0.5 text-xs text-zinc-500">{it.explanation}</p></div></div>
                  </div>))}</div>}
          </div>
          <div>
            <div className="mb-2.5 flex items-center justify-between">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500"><Brain className="h-3.5 w-3.5 text-brand-400" /> {t("knowledge.profile.title")}</p>
              <button onClick={generateProfile} disabled={genProfile} data-testid="generate-profile" className="inline-flex items-center gap-1 text-xs text-brand-300 hover:text-brand-200">{genProfile ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />} {profile ? t("common.refresh") : t("knowledge.profile.generate")}</button>
            </div>
            {!profile?.sections ? <div className="rounded-2xl border border-white/10 bg-zinc-950 p-4 text-center text-xs text-zinc-500" data-testid="profile-empty">{t("knowledge.profile.empty")}</div>
              : <div className="space-y-2 rounded-2xl border border-white/10 bg-zinc-950 p-4" data-testid="business-profile">
                  {Object.entries(profile.sections).map(([k, v]) => v && (
                    <div key={k}><p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">{k.replace(/_/g, " ")}</p>
                      <p className="text-sm text-zinc-300">{Array.isArray(v) ? v.join(", ") : String(v)}</p></div>))}
                </div>}
          </div>
        </div>
      </div>

      {editing && <EditModal mem={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />}
    </div>
  );
}

const Stat = ({ label, value }) => (<div className="rounded-2xl border border-white/10 bg-zinc-950 p-4" data-testid="brain-stat"><p className="text-2xl font-extrabold text-zinc-50">{value}</p><p className="text-xs text-zinc-500">{label}</p></div>);
const Chip = ({ active, onClick, children }) => (<button onClick={onClick} className={`rounded-full border px-2.5 py-1 text-xs font-medium transition-all ${active ? "border-brand-500 bg-brand-600/15 text-brand-200" : "border-white/10 bg-zinc-900 text-zinc-400 hover:text-zinc-200"}`}>{children}</button>);
