import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Receipt, Loader2, RefreshCw, Save, Download, History, GitCompare,
  Pencil, X, RotateCcw, FileText, Sparkles, Plus, Trash2,
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { invoiceWriterApi } from "@/lib/api";
import BrandedDocPreview from "@/components/BrandedDocPreview";
import { AIWorkflow } from "@/components/ai/AIWorkflow";
import { AIActionReport } from "@/components/ai/AIActionReport";
import { useAssistantDocument } from "@/context/AssistantContext";

const fmtTime = (d) => d ? new Date(d).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "—";
const money = (v) => `$${Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const statusStyle = {
  Draft: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  Generated: "bg-brand-500/10 text-brand-400 border-brand-500/20",
  Sent: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  Paid: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Overdue: "bg-red-500/10 text-red-400 border-red-500/20",
  Cancelled: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  Archived: "bg-zinc-500/10 text-zinc-500 border-zinc-500/20",
};
const BODY_FIELDS = [
  { key: "billing_address", label: "Billing Address", area: true },
  { key: "description", label: "Description", area: true },
  { key: "payment_terms", label: "Payment Terms" },
  { key: "bank_details", label: "Bank Details", area: true },
  { key: "notes", label: "Notes", area: true },
];

function computeTotals(lineItems, vatRate) {
  const items = (lineItems || []).map((li) => ({ ...li, amount: (Number(li.quantity) || 0) * (Number(li.unit_price) || 0) }));
  const subtotal = items.reduce((s, li) => s + li.amount, 0);
  const vat = subtotal * (Number(vatRate) || 0) / 100;
  return { items, subtotal, vat, total: subtotal + vat };
}

function InvoiceView({ inv, testidPrefix = "invoice-view" }) {
  const c = inv.content || {};
  const totals = computeTotals(inv.line_items, c.vat_rate);
  return (
    <div className="space-y-4" data-testid={testidPrefix}>
      <div className="grid grid-cols-2 gap-4 rounded-xl border border-white/10 bg-zinc-950 p-5 text-sm">
        <div><p className="text-xs uppercase tracking-wide text-zinc-500">Bill To</p><p className="mt-1 font-medium text-zinc-100">{c.company || c.client_name || "—"}</p><p className="whitespace-pre-wrap text-zinc-400">{c.billing_address}</p></div>
        <div className="text-right"><p className="text-xs uppercase tracking-wide text-zinc-500">Details</p><p className="mt-1 text-zinc-300">Issue: {c.issue_date || "—"}</p><p className="text-zinc-300">Due: {c.due_date || "—"}</p></div>
      </div>
      <div className="overflow-hidden rounded-xl border border-white/10 bg-zinc-950">
        <table className="w-full text-sm">
          <thead className="bg-brand-600/15 text-zinc-300"><tr><th className="px-4 py-2 text-left font-medium">Description</th><th className="px-4 py-2 text-right font-medium">Qty</th><th className="px-4 py-2 text-right font-medium">Unit Price</th><th className="px-4 py-2 text-right font-medium">Amount</th></tr></thead>
          <tbody>
            {totals.items.map((li, i) => (
              <tr key={i} className="border-t border-white/5"><td className="px-4 py-2 text-zinc-200">{li.description}</td><td className="px-4 py-2 text-right text-zinc-300">{li.quantity}</td><td className="px-4 py-2 text-right text-zinc-300">{money(li.unit_price)}</td><td className="px-4 py-2 text-right text-zinc-100">{money(li.amount)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="ml-auto w-full max-w-xs space-y-1 text-sm">
        <div className="flex justify-between text-zinc-400"><span>Subtotal</span><span>{money(totals.subtotal)}</span></div>
        <div className="flex justify-between text-zinc-400"><span>VAT ({c.vat_rate || 0}%)</span><span>{money(totals.vat)}</span></div>
        <div className="flex justify-between border-t border-brand-500/40 pt-1 text-base font-semibold text-zinc-50"><span>Total</span><span data-testid={`${testidPrefix}-total`}>{money(totals.total)}</span></div>
      </div>
      {["payment_terms", "bank_details", "notes"].filter((k) => c[k]).map((k) => (
        <div key={k} className="rounded-xl border border-white/10 bg-zinc-950 p-4"><p className="text-xs uppercase tracking-wide text-brand-400">{k.replace(/_/g, " ")}</p><p className="mt-1 whitespace-pre-wrap text-sm text-zinc-300">{c[k]}</p></div>
      ))}
    </div>
  );
}

export default function InvoiceWriter({ projectId, projectName, onSaved }) {
  const [statuses, setStatuses] = useState([]);
  const [invoice, setInvoice] = useState(null);
  const [number, setNumber] = useState("");
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("Draft");
  const [content, setContent] = useState(null);
  const [lineItems, setLineItems] = useState([]);
  const [dirtyVersion, setDirtyVersion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [compareWith, setCompareWith] = useState(null);
  const [report, setReport] = useState(null);
  const [durationMs, setDurationMs] = useState(0);

  const totals = useMemo(() => computeTotals(lineItems, content?.vat_rate), [lineItems, content]);

  const load = useCallback(async () => {
    try {
      const cfg = await invoiceWriterApi.config();
      setStatuses(cfg.statuses);
      const doc = await invoiceWriterApi.get(projectId);
      if (doc) { setInvoice(doc); setNumber(doc.invoice_number); setTitle(doc.title); setStatus(doc.status); setContent(doc.content); setLineItems(doc.line_items); setDirtyVersion(doc.version); }
    } catch (e) { /* ignore */ } finally { setLoading(false); }
  }, [projectId]);
  useEffect(() => { load(); }, [load]);

  const generate = async () => {
    if (generating) return;
    setGenerating(true); setCompareWith(null); setEditing(false); setReport(null);
    const start = Date.now();
    try {
      const d = await invoiceWriterApi.generate(projectId);
      setNumber(d.invoice_number); setTitle((prev) => prev || d.title); setContent(d.content); setLineItems(d.line_items); setStatus("Generated"); setDirtyVersion(null);
      setDurationMs(Date.now() - start); setReport(d.report || null);
    } catch (e) { toast.error(e.message); } finally { setGenerating(false); }
  };

  const sendToClient = async () => {
    setStatus("Sent"); setReport(null);
    try {
      const doc = await invoiceWriterApi.save(projectId, { invoice_number: number, title: title || `${projectName} — Invoice`, status: "Sent", content, line_items: lineItems });
      setInvoice(doc); setDirtyVersion(doc.version);
      toast.success("Invoice marked as Sent"); onSaved?.();
    } catch (e) { toast.error(e.message); setStatus("Generated"); }
  };

  const save = async () => {
    if (saving || !content) return;
    setSaving(true);
    try {
      const doc = await invoiceWriterApi.save(projectId, { invoice_number: number, title: title || `${projectName} — Invoice`, status, content, line_items: lineItems });
      setInvoice(doc); setNumber(doc.invoice_number); setLineItems(doc.line_items); setDirtyVersion(doc.version); setEditing(false);
      toast.success(`Invoice saved as v${doc.version}`); onSaved?.();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  const restore = async (v) => {
    try {
      const doc = await invoiceWriterApi.restore(projectId, v);
      setInvoice(doc); setNumber(doc.invoice_number); setTitle(doc.title); setStatus(doc.status); setContent(doc.content); setLineItems(doc.line_items); setDirtyVersion(doc.version); setCompareWith(null);
      toast.success(`Restored v${v} as new v${doc.version}`); onSaved?.();
    } catch (e) { toast.error(e.message); }
  };

  const exportFile = (fmt) => { window.open(invoiceWriterApi.exportUrl(projectId, fmt), "_blank"); toast.success(`Exporting ${fmt.toUpperCase()}…`); setTimeout(() => onSaved?.(), 1500); };
  const viewVersion = (v) => { setNumber(v.invoice_number); setTitle(v.title); setStatus(v.status); setContent(v.content); setLineItems(v.line_items); setDirtyVersion(v.version); setEditing(false); setCompareWith(null); };
  const setField = (k, val) => setContent((c) => ({ ...c, [k]: val }));
  useAssistantDocument({ type: "invoice", name: title || `${projectName} — Invoice`, sections: BODY_FIELDS, content, setField, active: !!content });
  const setItem = (i, k, val) => setLineItems((rows) => rows.map((r, idx) => idx === i ? { ...r, [k]: k === "description" ? val : Number(val) } : r));
  const addItem = () => setLineItems((r) => [...r, { description: "", quantity: 1, unit_price: 0 }]);
  const removeItem = (i) => setLineItems((r) => r.filter((_, idx) => idx !== i));

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
        <div data-testid="invoice-generating">
          <AIWorkflow running={generating} title="Preparing your invoice" steps={[
            "Reading client & billing details",
            "Pulling scope from proposal & contract",
            "Building line items",
            "Calculating VAT & totals",
            "Finalizing your invoice",
          ]} />
        </div>
      );
    }
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-zinc-950/40 py-20 text-center" data-testid="invoice-empty">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600 glow-brand animate-pulse-glow"><Receipt className="h-8 w-8 text-white" /></div>
        <h3 className="mt-5 text-lg font-semibold text-zinc-100">AI Invoice Generator</h3>
        <p className="mt-1 max-w-md text-sm text-zinc-500">Generate a professional invoice from your client, project, proposal, contract and payment terms — with auto-calculated line items and VAT.</p>
        <button onClick={generate} disabled={generating} data-testid="generate-invoice-btn" className="mt-6 flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-60 glow-brand">
          {generating ? <><Loader2 className="h-4 w-4 animate-spin" /> Preparing invoice…</> : <><Sparkles className="h-4 w-4" /> Generate Invoice</>}
        </button>
      </div>
    );
  }

  const history = invoice?.history || [];

  return (
    <div className="space-y-5" data-testid="tab-invoice">
      {/* Header */}
      <div className="rounded-xl border border-white/10 bg-zinc-950 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="rounded-md bg-brand-600/15 px-2 py-0.5 text-xs font-semibold text-brand-300" data-testid="invoice-number">{number}</span>
              <span className="text-xs text-zinc-500">Version <b className="text-zinc-300" data-testid="invoice-version">{dirtyVersion === null ? "draft" : dirtyVersion}</b></span>
            </div>
            <input value={title} onChange={(e) => setTitle(e.target.value)} data-testid="invoice-title-input" placeholder="Invoice name"
              className="mt-1 w-full bg-transparent text-lg font-bold tracking-tight text-zinc-50 outline-none placeholder:text-zinc-600" />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex flex-col"><label className="text-[10px] uppercase text-zinc-500">Issue</label>
              <input type="date" value={content.issue_date || ""} onChange={(e) => setField("issue_date", e.target.value)} data-testid="invoice-issue-date" className="rounded-lg border border-white/10 bg-zinc-900 px-2 py-1 text-sm text-zinc-200 outline-none focus:border-brand-500" /></div>
            <div className="flex flex-col"><label className="text-[10px] uppercase text-zinc-500">Due</label>
              <input type="date" value={content.due_date || ""} onChange={(e) => setField("due_date", e.target.value)} data-testid="invoice-due-date" className="rounded-lg border border-white/10 bg-zinc-900 px-2 py-1 text-sm text-zinc-200 outline-none focus:border-brand-500" /></div>
            <div className="flex flex-col"><label className="text-[10px] uppercase text-zinc-500">Status</label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger data-testid="invoice-status-trigger" className="w-32 border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
                <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">{statuses.map((s) => <SelectItem key={s} value={s} data-testid={`invoice-status-${s}`}>{s}</SelectItem>)}</SelectContent>
              </Select></div>
          </div>
        </div>
      </div>

      <BrandedDocPreview docType="invoice" />

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <span className={`mr-auto inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${statusStyle[status]}`}>{status}</span>
        <button onClick={() => setEditing((e) => !e)} data-testid="edit-invoice-btn" className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${editing ? "border-brand-500 bg-brand-600/15 text-brand-300" : "border-white/10 bg-zinc-900 text-zinc-300 hover:text-white"}`}>{editing ? <><X className="h-4 w-4" /> Done</> : <><Pencil className="h-4 w-4" /> Edit</>}</button>
        <button onClick={generate} disabled={generating} data-testid="regenerate-invoice-btn" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-300 hover:text-white disabled:opacity-60">{generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Regenerate</button>
        <button onClick={() => setShowHistory((s) => !s)} data-testid="invoice-version-history-btn" className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${showHistory ? "border-brand-500 bg-brand-600/15 text-brand-300" : "border-white/10 bg-zinc-900 text-zinc-300 hover:text-white"}`}><History className="h-4 w-4" /> Versions {history.length > 0 && <span className="rounded bg-zinc-800 px-1.5 text-xs">{history.length}</span>}</button>
        <button onClick={() => exportFile("pdf")} data-testid="export-invoice-pdf-btn" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-300 hover:text-white"><Download className="h-4 w-4" /> PDF</button>
        <button onClick={() => exportFile("docx")} data-testid="export-invoice-docx-btn" className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-300 hover:text-white"><FileText className="h-4 w-4" /> DOCX</button>
        <button onClick={save} disabled={saving} data-testid="save-invoice-btn" className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-60 glow-brand">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save</button>
      </div>

      {/* History */}
      {showHistory && (
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-4" data-testid="invoice-version-list">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-100"><History className="h-4 w-4 text-brand-400" /> Version History</h3>
          {history.length === 0 ? <p className="text-xs text-zinc-500" data-testid="invoice-no-versions">No versions yet. Save to create v1.</p> : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {[...history].reverse().map((v) => (
                <div key={v.version} className={`rounded-lg border p-3 ${dirtyVersion === v.version && !compareWith ? "border-brand-500/50 bg-brand-600/10" : "border-white/10 bg-zinc-900"}`} data-testid={`invoice-version-${v.version}`}>
                  <div className="flex items-center justify-between">
                    <button onClick={() => viewVersion(v)} data-testid={`view-invoice-version-${v.version}`} className="text-sm font-medium text-zinc-200 hover:text-brand-300">v{v.version} · {money(v.total)}</button>
                    <div className="flex items-center gap-1">
                      <button onClick={() => setCompareWith(v)} data-testid={`compare-invoice-version-${v.version}`} title="Compare" className="rounded p-1 text-zinc-500 hover:text-brand-400"><GitCompare className="h-3.5 w-3.5" /></button>
                      <button onClick={() => restore(v.version)} data-testid={`restore-invoice-version-${v.version}`} title="Restore" className="rounded p-1 text-zinc-500 hover:text-emerald-400"><RotateCcw className="h-3.5 w-3.5" /></button>
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
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2" data-testid="invoice-compare">
          <div><div className="mb-3 flex items-center justify-between rounded-lg bg-zinc-900 px-3 py-2"><span className="text-sm font-semibold text-zinc-300">v{compareWith.version} · {money(compareWith.total)}</span><button onClick={() => setCompareWith(null)} data-testid="exit-compare-invoice-btn" className="text-xs text-zinc-500 hover:text-white">Exit</button></div><InvoiceView inv={compareWith} testidPrefix="invoice-compare-a" /></div>
          <div><div className="mb-3 rounded-lg bg-brand-600/20 px-3 py-2 text-sm font-semibold text-brand-200">{dirtyVersion === null ? "Current draft" : `v${dirtyVersion}`}</div><InvoiceView inv={{ content, line_items: lineItems }} testidPrefix="invoice-compare-b" /></div>
        </div>
      ) : editing ? (
        <div className="space-y-4">
          {/* Editable line items */}
          <div className="overflow-hidden rounded-xl border border-white/10 bg-zinc-950" data-testid="invoice-line-items">
            <table className="w-full text-sm">
              <thead className="bg-zinc-900 text-zinc-400"><tr><th className="px-3 py-2 text-left font-medium">Description</th><th className="px-3 py-2 text-right font-medium">Qty</th><th className="px-3 py-2 text-right font-medium">Unit Price</th><th className="px-3 py-2 text-right font-medium">Amount</th><th /></tr></thead>
              <tbody>
                {lineItems.map((li, i) => (
                  <tr key={i} className="border-t border-white/5" data-testid={`invoice-item-${i}`}>
                    <td className="px-3 py-1.5"><input value={li.description} onChange={(e) => setItem(i, "description", e.target.value)} data-testid={`invoice-item-desc-${i}`} className="w-full rounded border border-white/10 bg-zinc-900 px-2 py-1 text-sm text-zinc-200 outline-none focus:border-brand-500" /></td>
                    <td className="px-3 py-1.5"><input type="number" value={li.quantity} onChange={(e) => setItem(i, "quantity", e.target.value)} data-testid={`invoice-item-qty-${i}`} className="w-16 rounded border border-white/10 bg-zinc-900 px-2 py-1 text-right text-sm text-zinc-200 outline-none focus:border-brand-500" /></td>
                    <td className="px-3 py-1.5"><input type="number" value={li.unit_price} onChange={(e) => setItem(i, "unit_price", e.target.value)} data-testid={`invoice-item-price-${i}`} className="w-24 rounded border border-white/10 bg-zinc-900 px-2 py-1 text-right text-sm text-zinc-200 outline-none focus:border-brand-500" /></td>
                    <td className="px-3 py-1.5 text-right text-zinc-100" data-testid={`invoice-item-amount-${i}`}>{money((Number(li.quantity) || 0) * (Number(li.unit_price) || 0))}</td>
                    <td className="px-2"><button onClick={() => removeItem(i)} data-testid={`invoice-item-remove-${i}`} className="text-zinc-500 hover:text-red-400"><Trash2 className="h-4 w-4" /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button onClick={addItem} data-testid="invoice-add-item-btn" className="flex w-full items-center justify-center gap-1.5 border-t border-white/5 py-2 text-sm font-medium text-brand-400 hover:bg-zinc-900"><Plus className="h-4 w-4" /> Add line item</button>
          </div>
          {/* Totals + VAT */}
          <div className="ml-auto w-full max-w-xs space-y-2 rounded-xl border border-white/10 bg-zinc-950 p-4 text-sm">
            <div className="flex items-center justify-between text-zinc-400"><span>Subtotal</span><span data-testid="invoice-subtotal">{money(totals.subtotal)}</span></div>
            <div className="flex items-center justify-between text-zinc-400"><span>VAT %</span><input type="number" value={content.vat_rate || 0} onChange={(e) => setField("vat_rate", Number(e.target.value))} data-testid="invoice-vat-input" className="w-20 rounded border border-white/10 bg-zinc-900 px-2 py-1 text-right text-zinc-200 outline-none focus:border-brand-500" /></div>
            <div className="flex justify-between text-zinc-400"><span>VAT amount</span><span data-testid="invoice-vat-amount">{money(totals.vat)}</span></div>
            <div className="flex justify-between border-t border-brand-500/40 pt-2 text-base font-semibold text-zinc-50"><span>Total</span><span data-testid="invoice-total">{money(totals.total)}</span></div>
          </div>
          {/* Editable text fields */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {BODY_FIELDS.map((f) => (
              <div key={f.key} className="rounded-xl border border-white/10 bg-zinc-950 p-4">
                <label className="mb-1.5 block text-xs uppercase tracking-wide text-brand-400">{f.label}</label>
                {f.area
                  ? <textarea value={content[f.key] || ""} onChange={(e) => setField(f.key, e.target.value)} data-testid={`invoice-field-${f.key}`} rows={3} className="w-full resize-none rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" />
                  : <input value={content[f.key] || ""} onChange={(e) => setField(f.key, e.target.value)} data-testid={`invoice-field-${f.key}`} className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" />}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <InvoiceView inv={{ content, line_items: lineItems }} />
      )}
    </div>
  );
}
