import { useCallback, useEffect, useState } from "react";
import {
  ScrollText, Loader2, RefreshCw, Save, Download, History, GitCompare,
  Pencil, X, RotateCcw, FileText, Sparkles,
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { contractWriterApi } from "@/lib/api";
import BrandedDocPreview from "@/components/BrandedDocPreview";
import { AIWorkflow } from "@/components/ai/AIWorkflow";
import { AIActionReport } from "@/components/ai/AIActionReport";
import { useAssistantDocument } from "@/context/AssistantContext";
import { useTranslation } from "react-i18next";
import { useLocale } from "@/context/LocaleContext";
import { localeTag } from "@/i18n/format";

const asList = (v) => Array.isArray(v) ? v : (v ? [v] : []);
const statusStyle = {
  Draft: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  Generated: "bg-brand-500/10 text-brand-400 border-brand-500/20",
  Sent: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  Signed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Expired: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  Cancelled: "bg-red-500/10 text-red-400 border-red-500/20",
  Archived: "bg-zinc-500/10 text-zinc-500 border-zinc-500/20",
};

function SectionView({ section, value, testidPrefix = "contract-section" }) {
  const { t } = useTranslation();
  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950 p-5" data-testid={`${testidPrefix}-${section.key}`}>
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-brand-400">{t(`writers.sections.${section.key}`, { defaultValue: section.label })}</h3>
      {section.type === "text" ? (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-300">{value || "—"}</p>
      ) : (
        <ul className="space-y-1.5">
          {asList(value).length === 0 ? <li className="text-sm text-zinc-600">—</li> :
            asList(value).map((item, i) => <li key={i} className="flex gap-2 text-sm leading-relaxed text-zinc-300"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />{item}</li>)}
        </ul>
      )}
    </div>
  );
}

function SectionEdit({ section, value, onChange }) {
  const { t } = useTranslation();
  const text = section.type === "list" ? asList(value).join("\n") : (value || "");
  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
      <h3 className="mb-3 flex items-center justify-between text-xs font-semibold uppercase tracking-[0.15em] text-brand-400">
        {t(`writers.sections.${section.key}`, { defaultValue: section.label })}{section.type === "list" && <span className="text-[10px] font-normal normal-case tracking-normal text-zinc-500">{t("writers.onePerLine")}</span>}
      </h3>
      <textarea value={text}
        onChange={(e) => onChange(section.type === "list" ? e.target.value.split("\n").filter((l) => l.trim() !== "") : e.target.value)}
        data-testid={`contract-edit-${section.key}`} rows={section.type === "list" ? 4 : 3}
        className="w-full resize-none rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm leading-relaxed text-zinc-200 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" />
    </div>
  );
}

export default function ContractWriter({ projectId, projectName, onSaved }) {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const fmtTime = (d) => d ? new Intl.DateTimeFormat(localeTag(locale), { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(d)) : "—";
  const [sections, setSections] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [contract, setContract] = useState(null);
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("Draft");
  const [content, setContent] = useState(null);
  const [dirtyVersion, setDirtyVersion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [compareWith, setCompareWith] = useState(null);
  const [report, setReport] = useState(null);
  const [durationMs, setDurationMs] = useState(0);

  const load = useCallback(async () => {
    try {
      const meta = await contractWriterApi.sections();
      setSections(meta.sections); setStatuses(meta.statuses);
      const doc = await contractWriterApi.get(projectId);
      if (doc) { setContract(doc); setTitle(doc.title); setStatus(doc.status); setContent(doc.content); setDirtyVersion(doc.version); }
    } catch (e) { /* ignore */ } finally { setLoading(false); }
  }, [projectId]);
  useEffect(() => { load(); }, [load]);

  const generate = async () => {
    if (generating) return;
    setGenerating(true); setCompareWith(null); setEditing(false); setReport(null);
    const start = Date.now();
    try {
      const { title: t, content: c, report: r } = await contractWriterApi.generate(projectId);
      setContent(c); setTitle((prev) => prev || t); setStatus("Generated"); setDirtyVersion(null);
      setDurationMs(Date.now() - start); setReport(r || null);
    } catch (e) { toast.error(e.message); } finally { setGenerating(false); }
  };

  const sendToClient = async () => {
    setStatus("Sent"); setReport(null);
    try {
      const doc = await contractWriterApi.save(projectId, { title: title || t("writers.contract.defaultTitle", { project: projectName }), status: "Sent", content });
      setContract(doc); setDirtyVersion(doc.version);
      toast.success(t("writers.contract.markedSent")); onSaved?.();
    } catch (e) { toast.error(e.message); setStatus("Generated"); }
  };

  const save = async () => {
    if (saving || !content) return;
    setSaving(true);
    try {
      const doc = await contractWriterApi.save(projectId, { title: title || t("writers.contract.defaultTitle", { project: projectName }), status, content });
      setContract(doc); setDirtyVersion(doc.version); setEditing(false);
      toast.success(t("writers.savedVersion", { type: t("writers.contract.name"), version: doc.version }));
      onSaved?.();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  const restore = async (v) => {
    try {
      const doc = await contractWriterApi.restore(projectId, v);
      setContract(doc); setTitle(doc.title); setStatus(doc.status); setContent(doc.content); setDirtyVersion(doc.version); setCompareWith(null);
      toast.success(t("writers.restoredVersion", { oldVersion: v, version: doc.version })); onSaved?.();
    } catch (e) { toast.error(e.message); }
  };

  const exportFile = (fmt) => { window.open(contractWriterApi.exportUrl(projectId, fmt), "_blank"); toast.success(t("writers.exporting", { format: fmt.toUpperCase() })); setTimeout(() => onSaved?.(), 1500); };
  const viewVersion = (v) => { setContent(v.content); setTitle(v.title); setStatus(v.status); setDirtyVersion(v.version); setEditing(false); setCompareWith(null); };
  const setField = (key, val) => setContent((c) => ({ ...c, [key]: val }));
  useAssistantDocument({ type: "contract", name: title || t("writers.contract.defaultTitle", { project: projectName }), sections, content, setField, active: !!content });

  if (loading) return <div className="flex items-center justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>;

  if (report) {
    return (
      <AIActionReport report={report} durationMs={durationMs} actions={{
        onReview: () => { setReport(null); setEditing(false); },
        onEdit: () => { setReport(null); setEditing(true); },
        onDownloadPdf: () => exportFile("pdf"),
        onExportWord: () => exportFile("docx"),
        onSend: sendToClient,
      }} />
    );
  }

  if (!content) {
    if (generating) {
      return (
        <div data-testid="contract-generating">
          <AIWorkflow running={generating} title={t("writers.contract.workflow.title")} steps={t("writers.contract.workflow.steps", { returnObjects: true })} />
        </div>
      );
    }
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-zinc-950/40 py-20 text-center" data-testid="contract-empty">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600 glow-brand animate-pulse-glow"><ScrollText className="h-8 w-8 text-white" /></div>
        <h3 className="mt-5 text-lg font-semibold text-zinc-100">{t("writers.contract.emptyTitle")}</h3>
        <p className="mt-1 max-w-md text-sm text-zinc-500">{t("writers.contract.emptyDescription")}</p>
        <button onClick={generate} disabled={generating} data-testid="generate-contract-btn" className="mt-6 flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-60 glow-brand">
          {generating ? <><Loader2 className="h-4 w-4 animate-spin" /> {t("writers.contract.generating")}</> : <><Sparkles className="h-4 w-4" /> {t("writers.contract.generate")}</>}
        </button>
      </div>
    );
  }

  const history = contract?.history || [];

  return (
    <div className="space-y-5" data-testid="tab-contract">
      {/* Header */}
      <div className="rounded-xl border border-white/10 bg-zinc-950 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="min-w-0 flex-1">
            <input value={title} onChange={(e) => setTitle(e.target.value)} data-testid="contract-title-input" placeholder={t("writers.contract.titlePlaceholder")}
              className="w-full bg-transparent text-lg font-bold tracking-tight text-zinc-50 outline-none placeholder:text-zinc-600" />
            <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-500">
              <span>{t("writers.version")} <b className="text-zinc-300" data-testid="contract-version">{dirtyVersion === null ? t("writers.draft") : dirtyVersion}</b></span>
              <span>{t("writers.lastGenerated")} <b className="text-zinc-300">{fmtTime(contract?.updated_at)}</b></span>
            </div>
          </div>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger data-testid="contract-status-trigger" className="w-40 border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
            <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
              {statuses.map((s) => <SelectItem key={s} value={s} data-testid={`contract-status-${s}`}>{t(`statuses.${s}`, { defaultValue: s })}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>

      <BrandedDocPreview docType="contract" />

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <span className={`mr-auto inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${statusStyle[status]}`}>{t(`statuses.${status}`, { defaultValue: status })}</span>
        <button onClick={() => setEditing((e) => !e)} data-testid="edit-contract-btn" className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${editing ? "border-brand-500 bg-brand-600/15 text-brand-300" : "border-white/10 bg-zinc-900 text-zinc-300 hover:text-white"}`}>
          {editing ? <><X className="h-4 w-4" /> {t("writers.done")}</> : <><Pencil className="h-4 w-4" /> {t("common.edit")}</>}
        </button>
        <button onClick={generate} disabled={generating} data-testid="regenerate-contract-btn" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-300 hover:text-white disabled:opacity-60">
          {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} {t("writers.regenerate")}
        </button>
        <button onClick={() => setShowHistory((s) => !s)} data-testid="contract-version-history-btn" className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${showHistory ? "border-brand-500 bg-brand-600/15 text-brand-300" : "border-white/10 bg-zinc-900 text-zinc-300 hover:text-white"}`}>
          <History className="h-4 w-4" /> {t("writers.versions")} {history.length > 0 && <span className="rounded bg-zinc-800 px-1.5 text-xs">{history.length}</span>}
        </button>
        <button onClick={() => exportFile("pdf")} data-testid="export-contract-pdf-btn" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-300 hover:text-white"><Download className="h-4 w-4" /> PDF</button>
        <button onClick={() => exportFile("docx")} data-testid="export-contract-docx-btn" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-300 hover:text-white"><FileText className="h-4 w-4" /> DOCX</button>
        <button onClick={save} disabled={saving} data-testid="save-contract-btn" className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-60 glow-brand">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} {t("common.save")}
        </button>
      </div>

      {/* History panel */}
      {showHistory && (
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-4" data-testid="contract-version-list">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-100"><History className="h-4 w-4 text-brand-400" /> {t("writers.versionHistory")}</h3>
          {history.length === 0 ? <p className="text-xs text-zinc-500" data-testid="contract-no-versions">{t("writers.noVersions")}</p> : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {[...history].reverse().map((v) => (
                <div key={v.version} className={`rounded-lg border p-3 ${dirtyVersion === v.version && !compareWith ? "border-brand-500/50 bg-brand-600/10" : "border-white/10 bg-zinc-900"}`} data-testid={`contract-version-${v.version}`}>
                  <div className="flex items-center justify-between">
                    <button onClick={() => viewVersion(v)} data-testid={`view-contract-version-${v.version}`} className="text-sm font-medium text-zinc-200 hover:text-brand-300">v{v.version}</button>
                    <div className="flex items-center gap-1">
                      <button onClick={() => setCompareWith(v)} data-testid={`compare-contract-version-${v.version}`} title={t("writers.compareCurrent")} className="rounded p-1 text-zinc-500 hover:text-brand-400"><GitCompare className="h-3.5 w-3.5" /></button>
                      <button onClick={() => restore(v.version)} data-testid={`restore-contract-version-${v.version}`} title={t("writers.restore")} className="rounded p-1 text-zinc-500 hover:text-emerald-400"><RotateCcw className="h-3.5 w-3.5" /></button>
                    </div>
                  </div>
                  <p className="mt-0.5 truncate text-xs text-zinc-500">{v.status} · {fmtTime(v.created_at)}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Content */}
      {compareWith ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2" data-testid="contract-compare">
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-lg bg-zinc-900 px-3 py-2">
              <span className="text-sm font-semibold text-zinc-300">v{compareWith.version} · {fmtTime(compareWith.created_at)}</span>
              <button onClick={() => setCompareWith(null)} data-testid="exit-compare-contract-btn" className="text-xs text-zinc-500 hover:text-white">{t("writers.exitCompare")}</button>
            </div>
            {sections.map((s) => <SectionView key={s.key} section={s} value={compareWith.content[s.key]} testidPrefix="contract-compare-a" />)}
          </div>
          <div className="space-y-4">
            <div className="rounded-lg bg-brand-600/20 px-3 py-2 text-sm font-semibold text-brand-200">{dirtyVersion === null ? t("writers.currentDraft") : `v${dirtyVersion}`}</div>
            {sections.map((s) => <SectionView key={s.key} section={s} value={content[s.key]} testidPrefix="contract-compare-b" />)}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {sections.map((s) => editing
            ? <SectionEdit key={s.key} section={s} value={content[s.key]} onChange={(v) => setField(s.key, v)} />
            : <SectionView key={s.key} section={s} value={content[s.key]} />)}
        </div>
      )}
    </div>
  );
}
