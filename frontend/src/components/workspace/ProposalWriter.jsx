import { useEffect, useState } from "react";
import {
  FileSignature, Loader2, RefreshCw, Save, Download, History, GitCompare,
  Pencil, X, RotateCcw, FileText, Sparkles, ChevronDown,
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { proposalWriterApi } from "@/lib/api";
import BrandedDocPreview from "@/components/BrandedDocPreview";

const asList = (v) => Array.isArray(v) ? v : (v ? [v] : []);
const fmtTime = (d) => d ? new Date(d).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "—";
const statusStyle = {
  Draft: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  Generated: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  Sent: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  Accepted: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Rejected: "bg-red-500/10 text-red-400 border-red-500/20",
  Archived: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

function SectionView({ section, value, testidPrefix = "prop-section" }) {
  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950 p-5" data-testid={`${testidPrefix}-${section.key}`}>
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-violet-400">{section.label}</h3>
      {section.type === "text" ? (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-300">{value || "—"}</p>
      ) : (
        <ul className="space-y-1.5">
          {asList(value).length === 0 ? <li className="text-sm text-zinc-600">—</li> :
            asList(value).map((item, i) => <li key={i} className="flex gap-2 text-sm leading-relaxed text-zinc-300"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-violet-500" />{item}</li>)}
        </ul>
      )}
    </div>
  );
}

function SectionEdit({ section, value, onChange }) {
  const text = section.type === "list" ? asList(value).join("\n") : (value || "");
  return (
    <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
      <h3 className="mb-3 flex items-center justify-between text-xs font-semibold uppercase tracking-[0.15em] text-violet-400">
        {section.label}{section.type === "list" && <span className="text-[10px] font-normal normal-case tracking-normal text-zinc-500">one per line</span>}
      </h3>
      <textarea value={text}
        onChange={(e) => onChange(section.type === "list" ? e.target.value.split("\n").filter((l) => l.trim() !== "") : e.target.value)}
        data-testid={`prop-edit-${section.key}`} rows={section.type === "list" ? 4 : 3}
        className="w-full resize-none rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm leading-relaxed text-zinc-200 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
    </div>
  );
}

export default function ProposalWriter({ projectId, projectName, onSaved }) {
  const [sections, setSections] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [proposal, setProposal] = useState(null);       // saved doc
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("Draft");
  const [content, setContent] = useState(null);         // current editable content
  const [dirtyVersion, setDirtyVersion] = useState(null); // null=unsaved draft, num=viewing saved version
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [compareWith, setCompareWith] = useState(null);

  const load = async () => {
    try {
      const meta = await proposalWriterApi.sections();
      setSections(meta.sections); setStatuses(meta.statuses);
      const doc = await proposalWriterApi.get(projectId);
      if (doc) { setProposal(doc); setTitle(doc.title); setStatus(doc.status); setContent(doc.content); setDirtyVersion(doc.version); }
    } catch (e) { /* ignore */ } finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [projectId]);

  const generate = async () => {
    setGenerating(true); setCompareWith(null); setEditing(false);
    try {
      const { title: t, content: c } = await proposalWriterApi.generate(projectId);
      setContent(c); setTitle((prev) => prev || t); setStatus("Generated"); setDirtyVersion(null);
      toast.success("Proposal generated — review, edit and save");
    } catch (e) { toast.error(e.message); } finally { setGenerating(false); }
  };

  const save = async () => {
    if (!content) return;
    setSaving(true);
    try {
      const doc = await proposalWriterApi.save(projectId, { title: title || `${projectName} — Proposal`, status, content });
      setProposal(doc); setDirtyVersion(doc.version); setEditing(false);
      toast.success(`Proposal saved as v${doc.version}`);
      onSaved?.();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  const restore = async (v) => {
    try {
      const doc = await proposalWriterApi.restore(projectId, v);
      setProposal(doc); setTitle(doc.title); setStatus(doc.status); setContent(doc.content); setDirtyVersion(doc.version); setCompareWith(null);
      toast.success(`Restored v${v} as new version v${doc.version}`); onSaved?.();
    } catch (e) { toast.error(e.message); }
  };

  const exportFile = (fmt) => { window.open(proposalWriterApi.exportUrl(projectId, fmt), "_blank"); toast.success(`Exporting ${fmt.toUpperCase()}…`); setTimeout(() => onSaved?.(), 1500); };
  const viewVersion = (v) => { setContent(v.content); setTitle(v.title); setStatus(v.status); setDirtyVersion(v.version); setEditing(false); setCompareWith(null); };
  const setField = (key, val) => setContent((c) => ({ ...c, [key]: val }));

  if (loading) return <div className="flex items-center justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>;

  // Empty (never generated / saved)
  if (!content) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-zinc-950/40 py-20 text-center" data-testid="proposal-empty">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-600 glow-violet animate-pulse-glow"><FileSignature className="h-8 w-8 text-white" /></div>
        <h3 className="mt-5 text-lg font-semibold text-zinc-100">AI Proposal Writer</h3>
        <p className="mt-1 max-w-md text-sm text-zinc-500">Generate a polished, client-ready proposal from your project context — client, plan, notes, tasks, documents and timeline. No copy/paste.</p>
        <button onClick={generate} disabled={generating} data-testid="generate-proposal-btn" className="mt-6 flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-60 glow-violet">
          {generating ? <><Loader2 className="h-4 w-4 animate-spin" /> Writing proposal…</> : <><Sparkles className="h-4 w-4" /> Generate Proposal</>}
        </button>
      </div>
    );
  }

  const history = proposal?.history || [];

  return (
    <div className="space-y-5" data-testid="tab-proposal">
      {/* Header */}
      <div className="rounded-xl border border-white/10 bg-zinc-950 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="min-w-0 flex-1">
            <input value={title} onChange={(e) => setTitle(e.target.value)} data-testid="proposal-title-input" placeholder="Proposal name"
              className="w-full bg-transparent text-lg font-bold tracking-tight text-zinc-50 outline-none placeholder:text-zinc-600" />
            <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-500">
              <span>Version <b className="text-zinc-300" data-testid="proposal-version">{dirtyVersion === null ? "draft" : dirtyVersion}</b></span>
              <span>Last generated <b className="text-zinc-300">{fmtTime(proposal?.updated_at)}</b></span>
            </div>
          </div>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger data-testid="proposal-status-trigger" className="w-40 border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
            <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
              {statuses.map((s) => <SelectItem key={s} value={s} data-testid={`proposal-status-${s}`}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>

      <BrandedDocPreview docType="proposal" />

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <span className={`mr-auto inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${statusStyle[status]}`}>{status}</span>
        <button onClick={() => setEditing((e) => !e)} data-testid="edit-proposal-btn" className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${editing ? "border-violet-500 bg-violet-600/15 text-violet-300" : "border-white/10 bg-zinc-900 text-zinc-300 hover:text-white"}`}>
          {editing ? <><X className="h-4 w-4" /> Done</> : <><Pencil className="h-4 w-4" /> Edit</>}
        </button>
        <button onClick={generate} disabled={generating} data-testid="regenerate-proposal-btn" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-300 hover:text-white disabled:opacity-60">
          {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Regenerate
        </button>
        <button onClick={() => setShowHistory((s) => !s)} data-testid="version-history-btn" className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${showHistory ? "border-violet-500 bg-violet-600/15 text-violet-300" : "border-white/10 bg-zinc-900 text-zinc-300 hover:text-white"}`}>
          <History className="h-4 w-4" /> Versions {history.length > 0 && <span className="rounded bg-zinc-800 px-1.5 text-xs">{history.length}</span>}
        </button>
        <button onClick={() => exportFile("pdf")} data-testid="export-proposal-pdf-btn" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-300 hover:text-white"><Download className="h-4 w-4" /> PDF</button>
        <button onClick={() => exportFile("docx")} data-testid="export-proposal-docx-btn" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-300 hover:text-white"><FileText className="h-4 w-4" /> DOCX</button>
        <button onClick={save} disabled={saving} data-testid="save-proposal-btn" className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-60 glow-violet">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save
        </button>
      </div>

      {/* History panel */}
      {showHistory && (
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-4" data-testid="proposal-version-list">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-100"><History className="h-4 w-4 text-violet-400" /> Version History</h3>
          {history.length === 0 ? <p className="text-xs text-zinc-500" data-testid="proposal-no-versions">No versions yet. Save to create v1.</p> : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {[...history].reverse().map((v) => (
                <div key={v.version} className={`rounded-lg border p-3 ${dirtyVersion === v.version && !compareWith ? "border-violet-500/50 bg-violet-600/10" : "border-white/10 bg-zinc-900"}`} data-testid={`proposal-version-${v.version}`}>
                  <div className="flex items-center justify-between">
                    <button onClick={() => viewVersion(v)} data-testid={`view-proposal-version-${v.version}`} className="text-sm font-medium text-zinc-200 hover:text-violet-300">v{v.version}</button>
                    <div className="flex items-center gap-1">
                      <button onClick={() => setCompareWith(v)} data-testid={`compare-proposal-version-${v.version}`} title="Compare with current" className="rounded p-1 text-zinc-500 hover:text-violet-400"><GitCompare className="h-3.5 w-3.5" /></button>
                      <button onClick={() => restore(v.version)} data-testid={`restore-proposal-version-${v.version}`} title="Restore" className="rounded p-1 text-zinc-500 hover:text-emerald-400"><RotateCcw className="h-3.5 w-3.5" /></button>
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
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2" data-testid="proposal-compare">
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-lg bg-zinc-900 px-3 py-2">
              <span className="text-sm font-semibold text-zinc-300">v{compareWith.version} · {fmtTime(compareWith.created_at)}</span>
              <button onClick={() => setCompareWith(null)} data-testid="exit-compare-proposal-btn" className="text-xs text-zinc-500 hover:text-white">Exit compare</button>
            </div>
            {sections.map((s) => <SectionView key={s.key} section={s} value={compareWith.content[s.key]} testidPrefix="prop-compare-a" />)}
          </div>
          <div className="space-y-4">
            <div className="rounded-lg bg-violet-600/20 px-3 py-2 text-sm font-semibold text-violet-200">{dirtyVersion === null ? "Current draft" : `v${dirtyVersion}`}</div>
            {sections.map((s) => <SectionView key={s.key} section={s} value={content[s.key]} testidPrefix="prop-compare-b" />)}
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
