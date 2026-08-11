import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Loader2, Mail, Plus, Send, Check, X, RotateCcw, Sparkles, Pencil, Ban, Search,
} from "lucide-react";
import { toast } from "sonner";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { emailsApi } from "@/lib/api";
import { emailsNl, fmtNlDate } from "@/lib/nlCopy";
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
  { id: "drafts", label: emailsNl.tabs.drafts },
  { id: "awaiting_approval", label: emailsNl.tabs.awaiting_approval },
  { id: "scheduled", label: emailsNl.tabs.scheduled },
  { id: "sent", label: emailsNl.tabs.sent },
  { id: "failed", label: emailsNl.tabs.failed },
];

const statusStyle = {
  draft: "bg-zinc-500/15 text-zinc-300",
  pending_approval: "bg-amber-500/15 text-amber-300",
  approved: "bg-emerald-500/15 text-emerald-300",
  scheduled: "bg-sky-500/15 text-sky-300",
  sending: "bg-violet-500/15 text-violet-300",
  sent: "bg-emerald-500/15 text-emerald-300",
  failed: "bg-rose-500/15 text-rose-300",
  needs_review: "bg-amber-500/15 text-amber-200",
  delivery_unknown: "bg-amber-500/15 text-amber-200",
  cancelled: "bg-zinc-500/15 text-zinc-500",
  rejected: "bg-rose-500/15 text-rose-300",
};

const emptyForm = () => ({
  to: "", cc: "", subject: "", textBody: "",
});

const formatCopyValue = (copyMap, value, fallback = "—") => {
  if (!value) return fallback;
  return copyMap[value] || String(value).replace(/_/g, " ");
};

const formatTemplate = (template, values) => Object.entries(values).reduce(
  (text, [key, value]) => text.replace(`{${key}}`, value),
  template,
);

const formatTransportLabel = (label) => {
  if (!label) return null;
  if (/gmail/i.test(label)) return emailsNl.sendGmail;
  if (/outlook|microsoft/i.test(label)) return emailsNl.sendOutlook;
  return label;
};

export default function EmailCenter() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
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
    } catch {
      setError(emailsNl.loadFailed);
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

  useEffect(() => {
    const draftId = searchParams.get("draft");
    if (draftId) {
      openDetail(draftId);
      setSearchParams({}, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const createDraft = async ({ generateAi = false } = {}) => {
    if (!form.to.trim()) { toast.error(emailsNl.recipientRequired); return; }
    if (!form.subject.trim() && !generateAi) { toast.error(emailsNl.subjectRequired); return; }
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
      toast.success(generateAi ? emailsNl.toasts.aiDraftCreated : emailsNl.toasts.draftCreated);
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
      toast.success(emailsNl.toasts.draftSaved);
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusyId(null);
    }
  };

  const blocked = Boolean(statusInfo && !statusInfo.canSend);
  const actionSuccess = {
    submit: emailsNl.toasts.submitted,
    approve: emailsNl.toasts.approved,
    reject: emailsNl.toasts.rejected,
    send: emailsNl.toasts.sendCompleted,
    cancel: emailsNl.toasts.cancelled,
    retry: emailsNl.toasts.retryCompleted,
    improve: emailsNl.toasts.aiRewriteApplied,
  };
  const actionLabels = {
    submit: emailsNl.submit,
    approve: emailsNl.approve,
    reject: emailsNl.reject,
    send: emailsNl.send,
    cancel: emailsNl.cancel,
    retry: emailsNl.retry,
    improve: emailsNl.improve,
  };

  const requestConfirm = (action, id) => {
    if ((action === "send" || action === "retry") && blocked) {
      toast.error(emailsNl.sendBlockedToast);
      return;
    }
    setConfirm({ action, id });
  };

  const runAction = async (action, id) => {
    if ((action === "send" || action === "retry") && blocked) {
      toast.error(emailsNl.sendBlockedToast);
      setConfirm(null);
      return;
    }
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
      toast.success(actionSuccess[action] || emailsNl.toasts.done);
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

  const detailEditable = useMemo(
    () => detail && ["draft", "pending_approval", "approved", "rejected", "failed", "needs_review", "delivery_unknown"].includes(detail.status),
    [detail],
  );

  const transport = detail?.transport;
  const transportLabel = formatTransportLabel(transport?.label);
  const providerReplyLabel = detail?.replyProvider === "google" ? emailsNl.sendGmail
    : detail?.replyProvider === "microsoft" ? emailsNl.sendOutlook
      : (transportLabel || emailsNl.providerReply);
  const sendLabel = detail?.replyProvider === "google" ? emailsNl.sendGmail
    : detail?.replyProvider === "microsoft" ? emailsNl.sendOutlook
      : (transportLabel || emailsNl.send);
  const transportBlocked = Boolean(transport?.reconnectRequired || (transport?.isThreadedReply && transport?.connected === false));

  return (
    <div className="space-y-5" data-testid="email-center-page">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-sm text-zinc-400">
            {emailsNl.intro}
            <HelpTip testid="emails-help" text={emailsNl.help} />
          </p>
          {statusInfo && (
            <p className="mt-1 text-xs text-zinc-500" data-testid="email-sending-status">
              {emailsNl.provider}: {statusInfo.provider}
              {" · "}
              {statusInfo.canSend ? emailsNl.sendingReady : emailsNl.sendingDisabled}
              {" · "}
              {emailsNl.today}: {statusInfo.sentToday}/{statusInfo.dailyLimit}
            </p>
          )}
        </div>
        <button
          type="button"
          data-testid="email-compose-btn"
          onClick={() => { setForm(emptyForm()); setComposeOpen(true); }}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500"
        >
          <Plus className="h-4 w-4" /> {emailsNl.compose}
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
            aria-label={emailsNl.searchAria}
            data-testid="email-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={emailsNl.search}
            className="w-full rounded-lg border border-white/10 bg-zinc-950 py-2 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 sm:w-64"
          />
        </div>
      </div>

      {blocked && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-200" data-testid="email-blocked-banner">
          {emailsNl.blockedBanner}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : error ? (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-6 text-sm text-rose-200" data-testid="email-error">{error}</div>
      ) : !(data.items || []).length ? (
        <EmptyState
          icon={Mail}
          title={emailsNl.emptyTitle}
          description={emailsNl.emptyBody}
          actionLabel={emailsNl.compose}
          onAction={() => setComposeOpen(true)}
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-white/10" data-testid="email-list">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-zinc-500">
              <tr>
                <th className="px-4 py-3 font-medium">{emailsNl.headers.recipient}</th>
                <th className="px-4 py-3 font-medium">{emailsNl.headers.subject}</th>
                <th className="px-4 py-3 font-medium">{emailsNl.headers.source}</th>
                <th className="px-4 py-3 font-medium">{emailsNl.headers.status}</th>
                <th className="px-4 py-3 font-medium">{emailsNl.headers.creator}</th>
                <th className="px-4 py-3 font-medium">{emailsNl.headers.date}</th>
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
                  <td className="px-4 py-3 text-zinc-400">{formatCopyValue(emailsNl.sources, row.source, emailsNl.sources.manual)}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-md px-2 py-0.5 text-xs ${statusStyle[row.status] || statusStyle.draft}`}>
                      {formatCopyValue(emailsNl.statuses, row.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-400">{row.createdByName || row.createdByEmail || "—"}</td>
                  <td className="px-4 py-3 text-zinc-500">{fmtNlDate(row.updatedAt || row.createdAt)}</td>
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
            <DialogTitle>{emailsNl.compose}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <label className="block text-xs text-zinc-400">{emailsNl.to}
              <input aria-label={emailsNl.to} data-testid="compose-to" className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={form.to} onChange={(e) => setForm((s) => ({ ...s, to: e.target.value }))} placeholder="client@example.com" />
            </label>
            <label className="block text-xs text-zinc-400">{emailsNl.cc}
              <input aria-label={emailsNl.cc} data-testid="compose-cc" className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={form.cc} onChange={(e) => setForm((s) => ({ ...s, cc: e.target.value }))} />
            </label>
            <label className="block text-xs text-zinc-400">{emailsNl.subject}
              <input aria-label={emailsNl.subject} data-testid="compose-subject" className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={form.subject} onChange={(e) => setForm((s) => ({ ...s, subject: e.target.value }))} />
            </label>
            <label className="block text-xs text-zinc-400">{emailsNl.body}
              <textarea aria-label={emailsNl.body} data-testid="compose-body" rows={8} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={form.textBody} onChange={(e) => setForm((s) => ({ ...s, textBody: e.target.value }))} />
            </label>
          </div>
          <DialogFooter className="gap-2 sm:gap-2">
            <button type="button" disabled={saving} onClick={() => createDraft({ generateAi: true })} className="inline-flex items-center gap-1.5 rounded-lg border border-violet-500/30 px-3 py-2 text-sm text-violet-300 hover:bg-violet-600/10" data-testid="compose-ai">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} {emailsNl.aiDraft}
            </button>
            <button type="button" disabled={saving} onClick={() => createDraft()} className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500" data-testid="compose-save">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pencil className="h-4 w-4" />} {emailsNl.saveDraft}
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
                <DialogTitle className="pr-6">{detail.subject || emailsNl.email}</DialogTitle>
              </DialogHeader>
              <div className="space-y-3 text-sm">
                <div className="flex flex-wrap gap-2 text-xs text-zinc-400">
                  <span className={`rounded-md px-2 py-0.5 ${statusStyle[detail.status] || statusStyle.draft}`}>{formatCopyValue(emailsNl.statuses, detail.status)}</span>
                  <span>{emailsNl.source}: {formatCopyValue(emailsNl.sources, detail.source)}</span>
                  {detail.providerMessageId && <span>{emailsNl.providerId}: {detail.providerMessageId}</span>}
                  {detail.deliveryStatus && <span>{emailsNl.delivery}: {formatCopyValue(emailsNl.deliveryStatuses, detail.deliveryStatus)}</span>}
                </div>
                {detailEditable ? (
                  <>
                    <label className="block text-xs text-zinc-400">{emailsNl.to}
                      <input aria-label={emailsNl.to} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={(detail.to || []).join(", ")} onChange={(e) => setDetail((d) => ({ ...d, to: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) }))} />
                    </label>
                    <label className="block text-xs text-zinc-400">{emailsNl.subject}
                      <input aria-label={emailsNl.subject} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={detail.subject || ""} onChange={(e) => setDetail((d) => ({ ...d, subject: e.target.value }))} />
                    </label>
                    <label className="block text-xs text-zinc-400">{emailsNl.body}
                      <textarea aria-label={emailsNl.body} rows={10} className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm" value={detail.textBody || ""} onChange={(e) => setDetail((d) => ({ ...d, textBody: e.target.value }))} />
                    </label>
                  </>
                ) : (
                  <>
                    <p className="text-zinc-400">{emailsNl.to}: {(detail.to || []).join(", ")}</p>
                    <div className="rounded-lg border border-white/10 bg-zinc-900/60 p-3 whitespace-pre-wrap text-zinc-200">{detail.textBody || emailsNl.noTextBody}</div>
                  </>
                )}
                {detail.failureReason && (
                  <p className="text-xs text-rose-300" data-testid="email-failure-reason">
                    {emailsNl.failure}: {detail.failureReason}
                    {detail.failureActionable ? ` — ${detail.failureActionable}` : ""}
                  </p>
                )}
                {detail.consolePreview && (
                  <pre className="overflow-x-auto rounded-lg border border-white/10 bg-zinc-900/60 p-3 text-[11px] text-zinc-400" data-testid="email-console-preview">{JSON.stringify(detail.consolePreview, null, 2)}</pre>
                )}
                {(detail.inboxThreadId || transport?.isThreadedReply) && (
                  <div className="rounded-lg border border-violet-500/20 bg-violet-600/10 p-3 text-xs text-zinc-300" data-testid="email-inbox-link">
                    <p className="font-medium text-violet-300">{emailsNl.linkedInbox}</p>
                    <p className="mt-1">
                      {providerReplyLabel}
                      {" · "}
                      {emailsNl.mailbox}: {transport?.mailboxEmail || detail.mailboxId || "—"}
                      {" · "}
                      <span className={transportBlocked ? "text-amber-300" : "text-emerald-300"}>
                        {transportBlocked ? emailsNl.disconnected : emailsNl.connected}
                      </span>
                    </p>
                    {transport?.providerThreadId && (
                      <p className="mt-1 text-zinc-500">{emailsNl.thread}: {transport.providerThreadId}</p>
                    )}
                    {transportBlocked && (
                      <p className="mt-2 text-amber-200" data-testid="email-reconnect-warning">
                        {emailsNl.reconnectWarning}
                      </p>
                    )}
                    {(detail.clientId || detail.leadId) && (
                      <p className="mt-1">
                        {emailsNl.crm}: {detail.clientId ? `${emailsNl.client} ${detail.clientId}` : ""}
                        {detail.leadId ? ` ${emailsNl.lead} ${detail.leadId}` : ""}
                      </p>
                    )}
                    <a href={`/inbox?thread=${detail.inboxThreadId}`} className="mt-2 inline-block text-violet-400 hover:underline" data-testid="email-view-conversation">{emailsNl.viewConversation}</a>
                  </div>
                )}
                {(detail.sentVia || detail.providerMessageId) && (
                  <details className="text-xs text-zinc-500" data-testid="email-provider-debug">
                    <summary className="cursor-pointer text-zinc-400">{emailsNl.providerDetails}</summary>
                    <ul className="mt-2 space-y-1">
                      <li>{emailsNl.sentVia}: {detail.sentVia || detail.transportProvider || detail.provider || "—"}</li>
                      <li>{emailsNl.providerMessageId}: {detail.providerMessageId || "—"}</li>
                      <li>{emailsNl.internetMessageId}: {detail.internetMessageId || "—"}</li>
                      <li>{emailsNl.thread}: {detail.providerThreadId || detail.providerConversationId || "—"}</li>
                    </ul>
                  </details>
                )}
                {detail.originalAiSuggestion && (
                  <details className="text-xs text-zinc-500">
                    <summary className="cursor-pointer text-zinc-400">{emailsNl.originalAiSuggestion}</summary>
                    <pre className="mt-2 whitespace-pre-wrap">{detail.originalAiSuggestion.textBody || detail.originalAiSuggestion.subject}</pre>
                  </details>
                )}
                {(detail.versions || []).length > 0 && (
                  <details className="text-xs text-zinc-500">
                    <summary className="cursor-pointer text-zinc-400">{emailsNl.history} ({detail.versions.length})</summary>
                    <ul className="mt-2 space-y-1">
                      {detail.versions.slice().reverse().map((v) => (
                        <li key={v.id}>{fmtNlDate(v.at)} · {formatCopyValue(emailsNl.historyKinds, v.kind, v.kind)} · {v.byEmail || v.by}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
              <DialogFooter className="flex flex-wrap gap-2 sm:justify-start">
                {detailEditable && (
                  <button type="button" disabled={busyId === detail.id} onClick={saveDetail} className="rounded-lg border border-white/10 px-3 py-2 text-sm hover:bg-zinc-900" data-testid="detail-save">{emailsNl.save}</button>
                )}
                {detailEditable && (
                  <button type="button" disabled={busyId === detail.id} onClick={() => runAction("improve", detail.id)} className="inline-flex items-center gap-1 rounded-lg border border-violet-500/30 px-3 py-2 text-sm text-violet-300" data-testid="detail-improve"><Sparkles className="h-3.5 w-3.5" /> {emailsNl.improve}</button>
                )}
                {["draft", "rejected", "failed"].includes(detail.status) && (
                  <button type="button" disabled={busyId === detail.id} onClick={() => runAction("submit", detail.id)} className="rounded-lg border border-amber-500/30 px-3 py-2 text-sm text-amber-200" data-testid="detail-submit">{emailsNl.submit}</button>
                )}
                {canApprove && detail.status === "pending_approval" && (
                  <>
                    <button type="button" disabled={busyId === detail.id} onClick={() => runAction("approve", detail.id)} className="inline-flex items-center gap-1 rounded-lg bg-emerald-600/80 px-3 py-2 text-sm text-white" data-testid="detail-approve"><Check className="h-3.5 w-3.5" /> {emailsNl.approve}</button>
                    <button type="button" disabled={busyId === detail.id} onClick={() => setConfirm({ action: "reject", id: detail.id })} className="inline-flex items-center gap-1 rounded-lg border border-rose-500/30 px-3 py-2 text-sm text-rose-300" data-testid="detail-reject"><X className="h-3.5 w-3.5" /> {emailsNl.reject}</button>
                  </>
                )}
                {["approved", "draft", "failed", "needs_review", "delivery_unknown"].includes(detail.status) && (canApprove || !statusInfo?.approvalRequired) && (
                  <button
                    type="button"
                    disabled={busyId === detail.id || transportBlocked || blocked}
                    onClick={() => requestConfirm("send", detail.id)}
                    className="inline-flex items-center gap-1 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                    data-testid="detail-send"
                  >
                    <Send className="h-3.5 w-3.5" /> {sendLabel}
                  </button>
                )}
                {["failed", "needs_review", "delivery_unknown"].includes(detail.status) && (
                  <button type="button" disabled={busyId === detail.id || transportBlocked || blocked} onClick={() => requestConfirm("retry", detail.id)} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-sm" data-testid="detail-retry"><RotateCcw className="h-3.5 w-3.5" /> {emailsNl.retry}</button>
                )}
                {!["sent", "sending", "cancelled"].includes(detail.status) && (
                  <button type="button" disabled={busyId === detail.id} onClick={() => setConfirm({ action: "cancel", id: detail.id })} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-400" data-testid="detail-cancel"><Ban className="h-3.5 w-3.5" /> {emailsNl.cancel}</button>
                )}
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!confirm} onOpenChange={(o) => !o && setConfirm(null)}>
        <AlertDialogContent className="border-white/10 bg-zinc-950 text-zinc-100">
          <AlertDialogHeader>
            <AlertDialogTitle>{emailsNl.confirmTitle}: {actionLabels[confirm?.action] || ""}</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">
              {confirm?.action === "send" && transport?.isThreadedReply
                ? formatTemplate(emailsNl.confirmSendThreaded, {
                  provider: providerReplyLabel || emailsNl.connectedMailbox,
                  mailbox: transport?.mailboxEmail || emailsNl.mailbox,
                })
                : confirm?.action === "send"
                  ? formatTemplate(emailsNl.confirmSend, {
                    provider: statusInfo?.provider || emailsNl.configuredProvider,
                  })
                  : emailsNl.confirmGeneric}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-white/10 bg-transparent">{emailsNl.confirmBack}</AlertDialogCancel>
            <AlertDialogAction
              data-testid="email-confirm-action"
              onClick={() => confirm && runAction(confirm.action, confirm.id)}
              className="bg-violet-600 hover:bg-violet-500"
            >
              {emailsNl.confirmOk}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
