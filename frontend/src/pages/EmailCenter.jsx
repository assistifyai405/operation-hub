import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Loader2, Mail, Plus, Send, Check, X, RotateCcw, Sparkles, Pencil, Ban, Search,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { emailsApi } from "@/lib/api";
import EmptyState from "@/components/EmptyState";
import HelpTip from "@/components/HelpTip";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const TABS = [
  { id: "drafts", label: "Drafts" },
  { id: "awaiting_approval", label: "Awaiting approval" },
  { id: "scheduled", label: "Scheduled" },
  { id: "sent", label: "Sent" },
  { id: "failed", label: "Failed" },
];

const statusStyle = {
  draft: "bg-zinc-500/15 text-zinc-300",
  pending_approval: "bg-amber-500/15 text-amber-300",
  approved: "bg-emerald-500/15 text-emerald-300",
  scheduled: "bg-sky-500/15 text-sky-300",
  sending: "bg-violet-500/15 text-violet-300",
  sent: "bg-emerald-500/15 text-emerald-300",
  failed: "bg-rose-500/15 text-rose-300",
  cancelled: "bg-zinc-500/15 text-zinc-500",
  rejected: "bg-rose-500/15 text-rose-300",
};

const fmtDate = (d) => {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return "—";
  }
};

const emptyForm = () => ({
  to: "", cc: "", subject: "", textBody: "",
});

export default function EmailCenter() {
  const { user } = useAuth();
  const canApprove = user?.role === "owner" || user?.role === "admin";
  const [tab, setTab] = useState("drafts");
  const [q, setQ] = useState("");
  const [data, setData] = useState({ items: [], counts: {} });
  const [statusInfo, setStatusInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [composeOpen, setComposeOpen] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const [detail, setDetail] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const [list, st] = await Promise.all([
        emailsApi.list({ status: tab, q: q || undefined }),
        emailsApi.status().catch(() => null),
      ]);
      setData(list);
      setStatusInfo(st);
    } catch (e) {
      setError(e.message || "Failed to load emails");
    } finally {
      setLoading(false);
    }
  }, [tab, q]);

  useEffect(() => {
    setLoading(true);
    const t = setTimeout(load, q ? 250 : 0);
    return () => clearTimeout(t);
  }, [load, q]);

  const openDetail = async (id) => {
    try {
      const d = await emailsApi.get(id);
      setDetail(d);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const createDraft = async ({ generateAi = false } = {}) => {
    if (!form.to.trim()) { toast.error("Recipient is required"); return; }
    if (!form.subject.trim() && !generateAi) { toast.error("Subject is required"); return; }
    setSaving(true);
    try {
      const body = {
        to: form.to.split(",").map((s) => s.trim()).filter(Boolean),
        cc: form.cc ? form.cc.split(",").map((s) => s.trim()).filter(Boolean) : [],
        subject: form.subject,
        textBody: form.textBody,
        generateAi,
      };
      const doc = await emailsApi.create(body);
      toast.success(generateAi ? "AI draft created" : "Draft created");
      setComposeOpen(false);
      setForm(emptyForm());
      setTab("drafts");
      await load();
      setDetail(doc);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const saveDetail = async () => {
    if (!detail) return;
    setBusyId(detail.id);
    try {
      const updated = await emailsApi.update(detail.id, {
        to: Array.isArray(detail.to) ? detail.to : String(detail.to || "").split(",").map((s) => s.trim()).filter(Boolean),
        cc: detail.cc || [],
        subject: detail.subject,
        textBody: detail.textBody,
      });
      setDetail(updated);
      toast.success("Draft saved");
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusyId(null);
    }
  };

  const runAction = async (action, id) => {
    setBusyId(id);
    try {
      let res;
      if (action === "submit") res = await emailsApi.submit(id);
      else if (action === "approve") res = await emailsApi.approve(id);
      else if (action === "reject") res = await emailsApi.reject(id);
      else if (action === "send") res = await emailsApi.send(id);
      else if (action === "cancel") res = await emailsApi.cancel(id);
      else if (action === "retry") res = await emailsApi.retry(id);
      else if (action === "improve") res = await emailsApi.improve(id, { command: "improve" });
      toast.success({
        submit: "Submitted for approval",
        approve: "Approved",
        reject: "Rejected",
        send: "Send completed",
        cancel: "Cancelled",
        retry: "Retry completed",
        improve: "AI rewrite applied",
      }[action] || "Done");
      if (detail?.id === id) setDetail(res);
      await load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusyId(null);
      setConfirm(null);
    }
  };

  const counts = data.counts || {};
  const blocked = statusInfo && !statusInfo.canSend;

  const detailEditable = useMemo(
    () => detail && ["draft", "pending_approval", "approved", "rejected", "failed"].includes(detail.status),
    [detail],
  );

  return (
    <div className="space-y-5" data-testid="email-center-page">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-sm text-zinc-400">
            Review drafts, approve outbound mail, and send safely.
            <HelpTip testid="emails-help" text="Sending is disabled until EMAIL_SENDING_ENABLED and organization email settings are turned on. Approval may be required before send." />
          </p>
          {statusInfo && (
            <p className="mt-1 text-xs text-zinc-500" data-testid="email-sending-status">
              Provider: {statusInfo.provider}
              {" · "}
              {statusInfo.canSend ? "Sending ready" : (statusInfo.blockedReason || "Sending disabled")}
              {" · "}
              Today: {statusInfo.sentToday}/{statusInfo.dailyLimit}
            </p>
          )}
        </div>
        <button
          type="button"
          data-testid="email-compose-btn"
          onClick={() => { setForm(emptyForm()); setComposeOpen(true); }}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500"
        >
          <Plus className="h-4 w-4" /> Compose draft
        </button>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              data-testid={`email-tab-${t.id}`}
              onClick={() => setTab(t.id)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                tab === t.id ? "bg-violet-600/15 text-violet-300" : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
              }`}
            >
              {t.label}
              {typeof counts[t.id] === "number" && (
                <span className="ml-1.5 text-zinc-500">{counts[t.id]}</span>
              )}
            </button>
          ))}
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <input
            aria-label="Search emails"
            data-testid="email-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search subject or recipient…"
            className="w-full rounded-lg border border-white/10 bg-zinc-950 py-2 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 sm:w-64"
          />
        </div>
      </div>

      {blocked && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-200" data-testid="email-blocked-banner">
          Outbound sending is currently blocked. Configure Settings → Email and enable sending when ready.
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : error ? (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-6 text-sm text-rose-200" data-testid="email-error">{error}</div>
      ) : !(data.items || []).length ? (
        <EmptyState
          icon={Mail}
          title="No emails here"
          description="Compose a draft or let automations prepare follow-ups for review."
          actionLabel="Compose draft"
          onAction={() => setComposeOpen(true)}
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-white/10" data-testid="email-list">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-zinc-500">
              <tr>
                <th className="px-4 py-3 font-medium">Recipient</th>
                <th className="px-4 py-3 font-medium">Subject</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Creator</th>
                <th className="px-4 py-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((row) => (
                <tr
                  key={row.id}
                  data-testid={`email-row-${row.id}`}
                  onClick={() => openDetail(row.id)}
                  className="cursor-pointer border-b border-white/5 hover:bg-zinc-900/60"
                >
                  <td className="px-4 py-3 text-zinc-200">{(row.to || []).join(", ")}</td>
                  <td className="px-4 py-3 text-zinc-100">{row.subject}</td>
                  <td className="px-4 py-3 capitalize text-zinc-400">{row.source || "manual"}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-md px-2 py-0.5 text-xs ${statusStyle[row.status] || statusStyle.draft}`}>
                      {row.status?.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-400">{row.createdByName || row.createdByEmail || "—"}</td>
                  <td className="px-4 py-3 text-zinc-500">{fmtDate(row.updatedAt || row.createdAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Compose */}
      <Dialog open={composeOpen} onOpenChange={setComposeOpen}>
        <DialogContent className="max-w-lg border-white/10 bg-zinc-950 text-zinc-100" data-testid="email-compose-dialog">
          <DialogHeader>
            <DialogTitle>Compose draft</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <label className="block text-xs text-zinc-400">To
              <input aria-label="To" data-testid="compose-to" className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={form.to} onChange={(e) => setForm((s) => ({ ...s, to: e.target.value }))} placeholder="client@example.com" />
            </label>
            <label className="block text-xs text-zinc-400">Cc
              <input aria-label="Cc" data-testid="compose-cc" className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={form.cc} onChange={(e) => setForm((s) => ({ ...s, cc: e.target.value }))} />
            </label>
            <label className="block text-xs text-zinc-400">Subject
              <input aria-label="Subject" data-testid="compose-subject" className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={form.subject} onChange={(e) => setForm((s) => ({ ...s, subject: e.target.value }))} />
            </label>
            <label className="block text-xs text-zinc-400">Body
              <textarea aria-label="Body" data-testid="compose-body" rows={8} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={form.textBody} onChange={(e) => setForm((s) => ({ ...s, textBody: e.target.value }))} />
            </label>
          </div>
          <DialogFooter className="gap-2 sm:gap-2">
            <button type="button" disabled={saving} onClick={() => createDraft({ generateAi: true })} className="inline-flex items-center gap-1.5 rounded-lg border border-violet-500/30 px-3 py-2 text-sm text-violet-300 hover:bg-violet-600/10" data-testid="compose-ai">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} AI draft
            </button>
            <button type="button" disabled={saving} onClick={() => createDraft()} className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500" data-testid="compose-save">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pencil className="h-4 w-4" />} Save draft
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail */}
      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto border-white/10 bg-zinc-950 text-zinc-100" data-testid="email-detail-dialog">
          {detail && (
            <>
              <DialogHeader>
                <DialogTitle className="pr-6">{detail.subject || "Email"}</DialogTitle>
              </DialogHeader>
              <div className="space-y-3 text-sm">
                <div className="flex flex-wrap gap-2 text-xs text-zinc-400">
                  <span className={`rounded-md px-2 py-0.5 ${statusStyle[detail.status] || statusStyle.draft}`}>{detail.status?.replace(/_/g, " ")}</span>
                  <span>Source: {detail.source}</span>
                  {detail.providerMessageId && <span>Provider ID: {detail.providerMessageId}</span>}
                  {detail.deliveryStatus && <span>Delivery: {detail.deliveryStatus}</span>}
                </div>
                {detailEditable ? (
                  <>
                    <label className="block text-xs text-zinc-400">To
                      <input aria-label="Detail to" className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={(detail.to || []).join(", ")} onChange={(e) => setDetail((d) => ({ ...d, to: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) }))} />
                    </label>
                    <label className="block text-xs text-zinc-400">Subject
                      <input aria-label="Detail subject" className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={detail.subject || ""} onChange={(e) => setDetail((d) => ({ ...d, subject: e.target.value }))} />
                    </label>
                    <label className="block text-xs text-zinc-400">Body
                      <textarea aria-label="Detail body" rows={10} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={detail.textBody || ""} onChange={(e) => setDetail((d) => ({ ...d, textBody: e.target.value }))} />
                    </label>
                  </>
                ) : (
                  <>
                    <p className="text-zinc-400">To: {(detail.to || []).join(", ")}</p>
                    <div className="rounded-lg border border-white/10 bg-zinc-900/60 p-3 whitespace-pre-wrap text-zinc-200">{detail.textBody || "(no text body)"}</div>
                  </>
                )}
                {detail.failureReason && (
                  <p className="text-xs text-rose-300">Failure: {detail.failureReason}</p>
                )}
                {detail.consolePreview && (
                  <pre className="overflow-x-auto rounded-lg border border-white/10 bg-zinc-900/60 p-3 text-[11px] text-zinc-400" data-testid="email-console-preview">{JSON.stringify(detail.consolePreview, null, 2)}</pre>
                )}
                {detail.originalAiSuggestion && (
                  <details className="text-xs text-zinc-500">
                    <summary className="cursor-pointer text-zinc-400">Original AI suggestion</summary>
                    <pre className="mt-2 whitespace-pre-wrap">{detail.originalAiSuggestion.textBody || detail.originalAiSuggestion.subject}</pre>
                  </details>
                )}
                {(detail.versions || []).length > 0 && (
                  <details className="text-xs text-zinc-500">
                    <summary className="cursor-pointer text-zinc-400">History ({detail.versions.length})</summary>
                    <ul className="mt-2 space-y-1">
                      {detail.versions.slice().reverse().map((v) => (
                        <li key={v.id}>{fmtDate(v.at)} · {v.kind} · {v.byEmail || v.by}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
              <DialogFooter className="flex flex-wrap gap-2 sm:justify-start">
                {detailEditable && (
                  <button type="button" disabled={busyId === detail.id} onClick={saveDetail} className="rounded-lg border border-white/10 px-3 py-2 text-sm hover:bg-zinc-900" data-testid="detail-save">Save</button>
                )}
                {detailEditable && (
                  <button type="button" disabled={busyId === detail.id} onClick={() => runAction("improve", detail.id)} className="inline-flex items-center gap-1 rounded-lg border border-violet-500/30 px-3 py-2 text-sm text-violet-300" data-testid="detail-improve"><Sparkles className="h-3.5 w-3.5" /> AI improve</button>
                )}
                {["draft", "rejected", "failed"].includes(detail.status) && (
                  <button type="button" disabled={busyId === detail.id} onClick={() => runAction("submit", detail.id)} className="rounded-lg border border-amber-500/30 px-3 py-2 text-sm text-amber-200" data-testid="detail-submit">Submit for approval</button>
                )}
                {canApprove && detail.status === "pending_approval" && (
                  <>
                    <button type="button" disabled={busyId === detail.id} onClick={() => runAction("approve", detail.id)} className="inline-flex items-center gap-1 rounded-lg bg-emerald-600/80 px-3 py-2 text-sm text-white" data-testid="detail-approve"><Check className="h-3.5 w-3.5" /> Approve</button>
                    <button type="button" disabled={busyId === detail.id} onClick={() => setConfirm({ action: "reject", id: detail.id })} className="inline-flex items-center gap-1 rounded-lg border border-rose-500/30 px-3 py-2 text-sm text-rose-300" data-testid="detail-reject"><X className="h-3.5 w-3.5" /> Reject</button>
                  </>
                )}
                {["approved", "draft", "failed"].includes(detail.status) && (canApprove || !statusInfo?.approvalRequired) && (
                  <button type="button" disabled={busyId === detail.id} onClick={() => setConfirm({ action: "send", id: detail.id })} className="inline-flex items-center gap-1 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white" data-testid="detail-send"><Send className="h-3.5 w-3.5" /> Send</button>
                )}
                {detail.status === "failed" && (
                  <button type="button" disabled={busyId === detail.id} onClick={() => setConfirm({ action: "retry", id: detail.id })} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-sm" data-testid="detail-retry"><RotateCcw className="h-3.5 w-3.5" /> Retry</button>
                )}
                {!["sent", "sending", "cancelled"].includes(detail.status) && (
                  <button type="button" disabled={busyId === detail.id} onClick={() => setConfirm({ action: "cancel", id: detail.id })} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-400" data-testid="detail-cancel"><Ban className="h-3.5 w-3.5" /> Cancel</button>
                )}
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!confirm} onOpenChange={(o) => !o && setConfirm(null)}>
        <AlertDialogContent className="border-white/10 bg-zinc-950 text-zinc-100">
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm {confirm?.action}</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">
              This action cannot be undone for send/cancel. Continue?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-white/10 bg-transparent">Back</AlertDialogCancel>
            <AlertDialogAction
              data-testid="email-confirm-action"
              onClick={() => confirm && runAction(confirm.action, confirm.id)}
              className="bg-violet-600 hover:bg-violet-500"
            >
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
