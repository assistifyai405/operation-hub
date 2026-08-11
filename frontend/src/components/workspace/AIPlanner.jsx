import { useCallback, useEffect, useState } from "react";
import {
  Sparkles, Loader2, RefreshCw, Save, Download, History, GitCompare,
  Pencil, X, FileText, Target, Cpu, ListChecks, Flag, ListTodo,
  CalendarClock, AlertTriangle, ArrowRightCircle,
} from "lucide-react";
import { toast } from "sonner";
import { plansApi } from "@/lib/api";
import { AIWorkflow } from "@/components/ai/AIWorkflow";
import { AIActionReport } from "@/components/ai/AIActionReport";
import { useAssistantDocument } from "@/context/AssistantContext";
import { useTranslation } from "react-i18next";
import { useLocale } from "@/context/LocaleContext";
import { formatDateShort, localeTag } from "@/i18n/format";

const SECTIONS = [
  { key: "executive_summary", label: "Executive Summary", icon: FileText, type: "text" },
  { key: "business_goal", label: "Business Goal", icon: Target, type: "text" },
  { key: "technical_requirements", label: "Technical Requirements", icon: Cpu, type: "list" },
  { key: "recommended_plan", label: "Recommended Project Plan", icon: ListChecks, type: "list" },
  { key: "milestones", label: "Milestones", icon: Flag, type: "list" },
  { key: "suggested_tasks", label: "Suggested Task List", icon: ListTodo, type: "list" },
  { key: "estimated_timeline", label: "Estimated Timeline", icon: CalendarClock, type: "text" },
  { key: "risks", label: "Risks & Challenges", icon: AlertTriangle, type: "list" },
  { key: "next_actions", label: "Recommended Next Actions", icon: ArrowRightCircle, type: "list" },
];

const emptySections = () => SECTIONS.reduce((a, s) => ({ ...a, [s.key]: s.type === "list" ? [] : "" }), {});
const asList = (v) => Array.isArray(v) ? v : (v ? [v] : []);
function SectionView({ section, value }) {
  const { t } = useTranslation();
  const Icon = section.icon;
  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950 p-5" data-testid={`plan-section-${section.key}`}>
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-100">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-600/15 text-brand-400"><Icon className="h-4 w-4" /></span>
        {t(`planner.sections.${section.key}`)}
      </h3>
      {section.type === "text" ? (
        <p className="text-sm leading-relaxed text-zinc-400">{value || "—"}</p>
      ) : (
        <ul className="space-y-1.5">
          {asList(value).length === 0 ? <li className="text-sm text-zinc-600">—</li> :
            asList(value).map((item, i) => (
              <li key={i} className="flex gap-2 text-sm leading-relaxed text-zinc-300"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />{item}</li>
            ))}
        </ul>
      )}
    </div>
  );
}

function SectionEdit({ section, value, onChange }) {
  const { t } = useTranslation();
  const Icon = section.icon;
  const text = section.type === "list" ? asList(value).join("\n") : (value || "");
  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-100">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-600/15 text-brand-400"><Icon className="h-4 w-4" /></span>
        {t(`planner.sections.${section.key}`)}
        {section.type === "list" && <span className="ml-auto text-xs font-normal text-zinc-500">{t("planner.onePerLine")}</span>}
      </h3>
      <textarea
        value={text}
        onChange={(e) => onChange(section.type === "list" ? e.target.value.split("\n").filter((l) => l.trim() !== "") : e.target.value)}
        data-testid={`plan-edit-${section.key}`}
        rows={section.type === "list" ? 4 : 3}
        className="w-full resize-none rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm leading-relaxed text-zinc-200 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40"
      />
    </div>
  );
}

function exportPdf(projectName, version, sections, t, locale) {
  const win = window.open("", "_blank");
  if (!win) { toast.error(t("planner.popupBlocked")); return; }
  const block = (s) => {
    const v = sections[s.key];
    const body = s.type === "list"
      ? `<ul>${asList(v).map((i) => `<li>${String(i).replace(/</g, "&lt;")}</li>`).join("")}</ul>`
      : `<p>${String(v || "—").replace(/</g, "&lt;")}</p>`;
    return `<section><h2>${t(`planner.sections.${s.key}`)}</h2>${body}</section>`;
  };
  win.document.write(`<!doctype html><html><head><title>${projectName} — ${t("planner.plan")}${version ? ` v${version}` : ""}</title>
    <style>
      *{font-family:'Outfit',Arial,sans-serif;}
      body{max-width:800px;margin:40px auto;padding:0 24px;color:#18181b;}
      h1{font-size:28px;margin-bottom:4px;} .sub{color:#71717a;margin-bottom:28px;}
      h2{font-size:15px;text-transform:uppercase;letter-spacing:.05em;color:#7c3aed;border-bottom:2px solid #ede9fe;padding-bottom:6px;margin-top:28px;}
      p,li{font-size:14px;line-height:1.6;color:#27272a;} ul{padding-left:20px;}
      .brand{color:#7c3aed;font-weight:700;}
    </style></head><body>
    <h1>${projectName}</h1>
    <div class="sub"><span class="brand">Assistify</span> — ${t("planner.aiProjectPlan")}${version ? ` · ${t("planner.version")} ${version}` : ` (${t("planner.draft")})`} · ${formatDateShort(new Date(), locale)}</div>
    ${SECTIONS.map(block).join("")}
    </body></html>`);
  win.document.close();
  setTimeout(() => win.print(), 400);
}

export default function AIPlanner({ projectId, projectName, onSaved }) {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const fmtTime = (d) => new Intl.DateTimeFormat(localeTag(locale), { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(d));
  const [versions, setVersions] = useState([]);
  const [draft, setDraft] = useState(null);            // sections currently shown
  const [draftVersion, setDraftVersion] = useState(null); // null = unsaved draft, number = saved version
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [compareWith, setCompareWith] = useState(null); // version object
  const [report, setReport] = useState(null);
  const [durationMs, setDurationMs] = useState(0);

  const loadVersions = useCallback(() => {
    plansApi.list(projectId).then((v) => {
      setVersions(v);
      setDraft((current) => {
        if (current === null && v.length) {
          setDraftVersion(v[0].version);
          return v[0].sections;
        }
        return current;
      });
    }).catch(() => {});
  }, [projectId]);

  useEffect(() => { loadVersions(); }, [loadVersions]);

  const generate = async () => {
    if (generating) return;
    setGenerating(true); setCompareWith(null); setEditing(false); setReport(null);
    const start = Date.now();
    try {
      const { sections, report: r } = await plansApi.generate(projectId);
      setDraft(sections); setDraftVersion(null);
      setDurationMs(Date.now() - start); setReport(r || null);
    } catch (e) { toast.error(e.message); } finally { setGenerating(false); }
  };

  const save = async () => {
    if (saving || !draft) return;
    setSaving(true);
    try {
      const saved = await plansApi.save(projectId, draft);
      toast.success(t("planner.savedVersion", { version: saved.version }));
      setDraftVersion(saved.version); setEditing(false);
      await loadVersions();
      onSaved?.();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  const viewVersion = (v) => { setDraft(v.sections); setDraftVersion(v.version); setEditing(false); setCompareWith(null); };
  const setField = (key, val) => setDraft((d) => ({ ...d, [key]: val }));
  useAssistantDocument({ type: "plan", name: `${projectName} — Plan`, sections: SECTIONS, content: draft, setField, active: draft !== null });

  // AI Action Report — shown immediately after a successful generation
  if (report) {
    return (
      <AIActionReport report={report} durationMs={durationMs} actions={{
        onReview: () => { setReport(null); setEditing(false); },
        onEdit: () => { setReport(null); setEditing(true); },
      }} />
    );
  }

  // Initial empty state (no versions, no draft)
  if (draft === null && versions.length === 0) {
    if (generating) {
      return (
        <div data-testid="planner-generating">
          <AIWorkflow running={generating} title={t("planner.workflow.title")} steps={t("planner.workflow.steps", { returnObjects: true })} />
        </div>
      );
    }
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-zinc-950/40 py-20 text-center" data-testid="planner-empty">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600 glow-brand animate-pulse-glow"><Sparkles className="h-8 w-8 text-white" /></div>
        <h3 className="mt-5 text-lg font-semibold text-zinc-100">{t("planner.emptyTitle")}</h3>
        <p className="mt-1 max-w-md text-sm text-zinc-500">{t("planner.emptyDescription")}</p>
        <button onClick={generate} disabled={generating} data-testid="generate-plan-btn" className="mt-6 flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-60 glow-brand">
          {generating ? <><Loader2 className="h-4 w-4 animate-spin" /> {t("planner.generating")}</> : <><Sparkles className="h-4 w-4" /> {t("planner.generate")}</>}
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_260px]" data-testid="tab-planner">
      {/* Main */}
      <div className="space-y-5">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-white/10 bg-zinc-950 p-3">
          <span className="mr-auto flex items-center gap-2 text-sm font-medium text-zinc-200">
            <Sparkles className="h-4 w-4 text-brand-400" />
            {draftVersion === null ? t("planner.unsavedDraft") : t("planner.versionNumber", { version: draftVersion })}
            {compareWith && <span className="text-zinc-500">· {t("planner.comparingWith", { version: compareWith.version })}</span>}
          </span>
          {!compareWith && (
            <>
              <button onClick={() => setEditing((e) => !e)} data-testid="edit-plan-btn" className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${editing ? "border-brand-500 bg-brand-600/15 text-brand-300" : "border-white/10 bg-zinc-900 text-zinc-300 hover:text-white"}`}>
                {editing ? <><X className="h-4 w-4" /> {t("planner.doneEditing")}</> : <><Pencil className="h-4 w-4" /> {t("common.edit")}</>}
              </button>
              <button onClick={generate} disabled={generating} data-testid="regenerate-plan-btn" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-300 transition-all hover:text-white disabled:opacity-60">
                {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} {t("writers.regenerate")}
              </button>
              <button onClick={() => exportPdf(projectName, draftVersion, draft, t, locale)} data-testid="export-pdf-btn" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-300 transition-all hover:text-white">
                <Download className="h-4 w-4" /> {t("planner.exportPdf")}
              </button>
              <button onClick={save} disabled={saving} data-testid="save-plan-btn" className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-60 glow-brand">
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} {t("planner.saveVersion")}
              </button>
            </>
          )}
          {compareWith && (
            <button onClick={() => setCompareWith(null)} data-testid="exit-compare-btn" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-300 hover:text-white">
              <X className="h-4 w-4" /> {t("writers.exitCompare")}
            </button>
          )}
        </div>

        {/* Content */}
        {compareWith ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2" data-testid="plan-compare">
            <div className="space-y-4">
              <div className="sticky top-0 rounded-lg bg-zinc-900 px-3 py-2 text-center text-sm font-semibold text-zinc-300">v{compareWith.version} · {fmtTime(compareWith.created_at)}</div>
              {SECTIONS.map((s) => <SectionView key={s.key} section={s} value={compareWith.sections[s.key]} />)}
            </div>
            <div className="space-y-4">
              <div className="sticky top-0 rounded-lg bg-brand-600/20 px-3 py-2 text-center text-sm font-semibold text-brand-200">{draftVersion === null ? t("writers.currentDraft") : `v${draftVersion}`}</div>
              {SECTIONS.map((s) => <SectionView key={s.key} section={s} value={draft[s.key]} />)}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {SECTIONS.map((s) => editing
              ? <SectionEdit key={s.key} section={s} value={draft[s.key]} onChange={(v) => setField(s.key, v)} />
              : <SectionView key={s.key} section={s} value={draft[s.key]} />)}
          </div>
        )}
      </div>

      {/* Version history sidebar */}
      <div className="space-y-3">
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-100"><History className="h-4 w-4 text-brand-400" /> {t("writers.versionHistory")}</h3>
          {versions.length === 0 ? (
            <p className="text-xs text-zinc-500" data-testid="no-versions">{t("planner.noVersions")}</p>
          ) : (
            <div className="space-y-2" data-testid="version-list">
              {versions.map((v) => (
                <div key={v.id} className={`rounded-lg border p-2.5 transition-all ${draftVersion === v.version && !compareWith ? "border-brand-500/50 bg-brand-600/10" : "border-white/10 bg-zinc-900"}`} data-testid={`version-${v.version}`}>
                  <div className="flex items-center justify-between">
                    <button onClick={() => viewVersion(v)} data-testid={`view-version-${v.version}`} className="text-sm font-medium text-zinc-200 hover:text-brand-300">{t("planner.versionNumber", { version: v.version })}</button>
                    <button onClick={() => { setCompareWith(v); }} disabled={draftVersion === v.version && draftVersion !== null} data-testid={`compare-version-${v.version}`} title={t("writers.compareCurrent")} className="rounded p-1 text-zinc-500 transition-colors hover:text-brand-400 disabled:opacity-30">
                      <GitCompare className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <p className="mt-0.5 text-xs text-zinc-500">{fmtTime(v.created_at)}</p>
                </div>
              ))}
            </div>
          )}
        </div>
        <button onClick={generate} disabled={generating} data-testid="sidebar-generate-btn" className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/10 bg-zinc-950 px-3 py-2.5 text-sm font-medium text-zinc-300 transition-all hover:border-brand-500/40 hover:text-white disabled:opacity-60">
          {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4 text-brand-400" />} {t("planner.newGeneration")}
        </button>
      </div>
    </div>
  );
}
