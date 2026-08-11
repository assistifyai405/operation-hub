import PageIntro from "@/components/PageIntro";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Search, Plus, GripVertical, Loader2, Filter, Target } from "lucide-react";
import { crmApi } from "@/lib/api";
import { STAGES, STAGE_META, SCORE_COLOR, fmtMoney, fmtMoneyFull } from "@/components/crm/crmShared";
import { LeadDrawer } from "@/components/crm/LeadDrawer";
import { useLocale } from "@/context/LocaleContext";

function ScoreDot({ score }) {
  return <span className={`text-[11px] font-bold ${SCORE_COLOR(score).split(" ")[0]}`}>{score}</span>;
}

function LeadCard({ lead, onDragStart, onOpen }) {
  const { locale } = useLocale();
  const meta = STAGE_META[lead.stage] || STAGE_META.New;
  return (
    <div draggable onDragStart={(e) => onDragStart(e, lead)} onClick={() => onOpen(lead.id)}
      data-testid="pipeline-lead-card" data-lead-id={lead.id}
      className="group cursor-pointer rounded-xl border border-white/10 bg-zinc-950 p-3 transition-all hover:border-brand-500/40 active:cursor-grabbing">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-zinc-100">{lead.title}</p>
        <GripVertical className="h-4 w-4 shrink-0 text-zinc-700 opacity-0 transition-opacity group-hover:opacity-100" />
      </div>
      {lead.client_name && <p className="mt-0.5 truncate text-xs text-zinc-500">{lead.client_name}</p>}
      <div className="mt-2.5 flex items-center justify-between">
        <span className="text-sm font-bold text-emerald-300">{fmtMoney(lead.value, locale)}</span>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-zinc-500">{lead.probability}%</span>
          <div className="flex h-6 w-6 items-center justify-center rounded-full border border-white/10"><ScoreDot score={lead.score} /></div>
        </div>
      </div>
      {lead.tags?.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {lead.tags.slice(0, 3).map((t) => <span key={t} className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-zinc-400">{t}</span>)}
        </div>
      )}
    </div>
  );
}

export default function Pipeline() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("score");
  const [dragOver, setDragOver] = useState(null);
  const [openId, setOpenId] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    crmApi.pipeline({ q, sort }).then(setData).catch(() => setData(null)).finally(() => setLoading(false));
  }, [q, sort]);
  useEffect(() => { const t = setTimeout(load, q ? 250 : 0); return () => clearTimeout(t); }, [load, q]);

  const onDragStart = (e, lead) => { e.dataTransfer.setData("leadId", lead.id); e.dataTransfer.effectAllowed = "move"; };
  const onDrop = async (e, stage) => {
    e.preventDefault(); setDragOver(null);
    const id = e.dataTransfer.getData("leadId");
    if (!id) return;
    const col = data.columns.find((c) => c.items.some((l) => l.id === id));
    if (col?.stage === stage) return;
    // optimistic move
    setData((d) => {
      const cols = d.columns.map((c) => ({ ...c, items: c.items.filter((l) => l.id !== id) }));
      let moved;
      d.columns.forEach((c) => { const f = c.items.find((l) => l.id === id); if (f) moved = f; });
      if (moved) { moved = { ...moved, stage }; cols.find((c) => c.stage === stage).items.unshift(moved); }
      return { ...d, columns: cols };
    });
    try { await crmApi.moveStage(id, stage); toast.success(t("pipeline.toasts.moved", { stage: t(`pipeline.stages.${stage}`, { defaultValue: stage }) })); load(); }
    catch (err) { toast.error(t("pipeline.toasts.moveFailed")); load(); }
  };

  const newLead = async () => {
    try { const l = await crmApi.createLead({ title: t("pipeline.newLead"), stage: "New", value: 0 }); load(); setOpenId(l.id); }
    catch (e) { toast.error(e.message); }
  };

  const totalPipeline = data ? data.columns.filter((c) => !["Won", "Lost"].includes(c.stage)).reduce((a, c) => a + c.value, 0) : 0;

  return (
    <div className="space-y-5" data-testid="pipeline-page">
      <PageIntro title={t("pages.pipeline.title")} description={t("pages.pipeline.description")} helpModule="pipeline" />

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2.5 text-3xl font-bold tracking-tight text-zinc-50">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 glow-brand"><Target className="h-5 w-5 text-white" /></span>
            {t("pipeline.title")}
          </h1>
          <p className="mt-1.5 text-sm text-zinc-400">
            {t("pipeline.intro")}
            {data ? ` ${t("pipeline.openValue", { amount: fmtMoneyFull(totalPipeline, locale) })}` : ""}
          </p>
        </div>
        <button type="button" onClick={newLead} data-testid="pipeline-new-lead" className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3.5 py-2 text-sm font-semibold text-white hover:bg-brand-500"><Plus className="h-4 w-4" aria-hidden="true" /> {t("pipeline.newLead")}</button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <input value={q} onChange={(e) => setQ(e.target.value)} data-testid="pipeline-search" placeholder={t("pipeline.search")}
            className="w-full rounded-lg border border-white/10 bg-zinc-900 py-2 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-brand-500/50 focus:outline-none" />
        </div>
        <div className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-2">
          <Filter className="h-3.5 w-3.5 text-zinc-500" />
          <select value={sort} onChange={(e) => setSort(e.target.value)} data-testid="pipeline-sort" className="bg-transparent text-sm text-zinc-200 focus:outline-none">
            <option value="score">{t("pipeline.sort.score")}</option>
            <option value="value">{t("pipeline.sort.value")}</option>
            <option value="close">{t("pipeline.sort.close")}</option>
          </select>
        </div>
      </div>

      {loading && !data ? (
        <div className="flex items-center justify-center py-24 text-zinc-600"><Loader2 className="h-7 w-7 animate-spin" /></div>
      ) : (data?.columns || []).every((c) => (c.items || []).length === 0) ? (
        <div className="rounded-2xl border border-dashed border-white/10 bg-zinc-950 px-4 py-16 text-center" data-testid="pipeline-empty">
          <Target className="mx-auto h-9 w-9 text-zinc-600" aria-hidden="true" />
          <p className="mt-3 text-sm font-semibold text-zinc-200">{t("pipeline.empty.title")}</p>
          <p className="mx-auto mt-1 max-w-md text-xs text-zinc-500">
            {t("pipeline.empty.description")}
          </p>
          <button type="button" onClick={newLead} data-testid="pipeline-empty-action" className="mt-5 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500">
            <Plus className="h-4 w-4" aria-hidden="true" /> {t("pipeline.empty.action")}
          </button>
        </div>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-4" data-testid="pipeline-board">
          {data?.columns.map((col) => {
            const meta = STAGE_META[col.stage] || STAGE_META.New;
            return (
              <div key={col.stage} data-testid={`pipeline-col-${col.stage.replace(/\s/g, "-").toLowerCase()}`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(col.stage); }} onDragLeave={() => setDragOver(null)} onDrop={(e) => onDrop(e, col.stage)}
                className={`flex w-72 shrink-0 flex-col rounded-2xl border-t-2 ${meta.bar} border border-white/10 bg-zinc-900/40 transition-colors ${dragOver === col.stage ? "bg-brand-500/[0.06] ring-1 ring-brand-500/40" : ""}`}>
                <div className="flex items-center justify-between px-3 py-2.5">
                  <div className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${meta.dot}`} /><span className="text-sm font-semibold text-zinc-200">{t(`pipeline.stages.${col.stage}`, { defaultValue: col.stage })}</span><span className="rounded-full bg-white/5 px-1.5 text-[10px] text-zinc-400">{col.count}</span></div>
                  <span className="text-xs font-medium text-zinc-500">{fmtMoney(col.value, locale)}</span>
                </div>
                <div className="flex-1 space-y-2 overflow-y-auto px-2 pb-3" style={{ minHeight: 120 }}>
                  {col.items.map((lead) => <LeadCard key={lead.id} lead={lead} onDragStart={onDragStart} onOpen={setOpenId} />)}
                  {col.items.length === 0 && <div className="rounded-lg border border-dashed border-white/10 py-6 text-center text-xs text-zinc-600">{t("pipeline.dropHere")}</div>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {openId && <LeadDrawer leadId={openId} navigate={navigate} onClose={() => setOpenId(null)} onChanged={load} />}
    </div>
  );
}
