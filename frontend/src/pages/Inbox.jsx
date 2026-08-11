import PageIntro from "@/components/PageIntro";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocale } from "@/context/LocaleContext";
import { formatDateTime } from "@/i18n/format";
import {
  Loader2, Mail, RefreshCw, Link2, Unlink, Sparkles, User, Search, Inbox as InboxIcon,
} from "lucide-react";
import { toast } from "sonner";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { inboxApi } from "@/lib/api";
import EmptyState from "@/components/EmptyState";
import HelpTip from "@/components/HelpTip";

const VIEWS = [
  { id: "all", labelKey: "inbox.views.all" },
  { id: "unread", labelKey: "inbox.views.unread" },
  { id: "assigned", labelKey: "inbox.views.assigned" },
  { id: "linked", labelKey: "inbox.views.linked" },
  { id: "unlinked", labelKey: "inbox.views.unlinked" },
];

export default function Inbox() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const fmtTime = (d) => formatDateTime(d, locale);
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const canSync = user?.role === "owner" || user?.role === "admin";
  const [mailboxes, setMailboxes] = useState([]);
  const [view, setView] = useState("all");
  const [provider, setProvider] = useState("all");
  const [mailboxId, setMailboxId] = useState("");
  const [q, setQ] = useState("");
  const [threads, setThreads] = useState({ items: [], total: 0, page: 1, pages: 1 });
  const [selected, setSelected] = useState(searchParams.get("thread") || null);
  const [detail, setDetail] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [syncing, setSyncing] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [linkForm, setLinkForm] = useState({ clientId: "", leadId: "" });

  const loadMailboxes = useCallback(async () => {
    try {
      const res = await inboxApi.mailboxes();
      setMailboxes(res.items || []);
    } catch (e) {
      /* ignore */
    }
  }, []);

  const threadParams = useMemo(() => {
    const p = { page: threads.page || 1, page_size: 25 };
    if (provider !== "all") p.provider = provider;
    if (mailboxId) p.mailbox_id = mailboxId;
    if (q) p.q = q;
    if (view === "unread") p.unread = true;
    if (view === "assigned") p.assigned = "me";
    if (view === "linked") p.linked = true;
    if (view === "unlinked") p.linked = false;
    return p;
  }, [provider, mailboxId, q, view, threads.page]);

  const loadThreads = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const res = await inboxApi.threads(threadParams);
      setThreads(res);
    } catch (e) {
      setError(e.message || t("inbox.loadError"));
    } finally {
      setLoading(false);
    }
  }, [threadParams, t]);

  useEffect(() => { loadMailboxes(); }, [loadMailboxes]);
  useEffect(() => {
    const t = setTimeout(loadThreads, q ? 250 : 0);
    return () => clearTimeout(t);
  }, [loadThreads, q]);

  const openThread = async (id) => {
    setSelected(id);
    setDetailLoading(true);
    try {
      const [t, m] = await Promise.all([
        inboxApi.getThread(id),
        inboxApi.messages(id),
      ]);
      setDetail(t);
      setMessages(m.timeline || m.messages || []);
      if ((t.thread?.unreadCount || 0) > 0) {
        await inboxApi.patchThread(id, { isRead: true }).catch(() => {});
        loadThreads();
      }
    } catch (e) {
      toast.error(e.message);
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    const tid = searchParams.get("thread");
    if (tid) openThread(tid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const ensureAndSync = async (prov) => {
    if (!canSync) {
      toast.error(t("inbox.toasts.adminOnly"));
      return;
    }
    setSyncing(prov);
    try {
      const mb = await inboxApi.ensureMailbox(prov);
      const res = await inboxApi.syncMailbox(mb.id);
      toast.success(t("inbox.toasts.synced", { count: res.messagesCreated || 0 }));
      await loadMailboxes();
      await loadThreads();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSyncing(null);
    }
  };

  const syncOne = async (id) => {
    if (!canSync) return;
    setSyncing(id);
    try {
      const res = await inboxApi.syncMailbox(id);
      toast.success(t("inbox.toasts.synced", { count: res.messagesCreated || 0 }));
      await loadMailboxes();
      await loadThreads();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSyncing(null);
    }
  };

  const runSummarize = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      const res = await inboxApi.summarize(selected);
      setDetail((d) => ({ ...d, thread: { ...d.thread, aiSummary: res.aiSummary } }));
      toast.success(t("inbox.toasts.summaryReady"));
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const runDraftReply = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      const res = await inboxApi.draftReply(selected);
      toast.success(t("inbox.toasts.replyDraftCreated"));
      navigate(`/emails?draft=${res.email?.id || ""}`);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const runLink = async () => {
    if (!selected) return;
    if (!linkForm.clientId && !linkForm.leadId) {
      toast.error(t("inbox.toasts.enterId"));
      return;
    }
    setBusy(true);
    try {
      await inboxApi.link(selected, {
        clientId: linkForm.clientId || undefined,
        leadId: linkForm.leadId || undefined,
      });
      toast.success(t("inbox.toasts.linked"));
      await openThread(selected);
      loadThreads();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const runUnlink = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      await inboxApi.unlink(selected);
      toast.success(t("inbox.toasts.unlinked"));
      await openThread(selected);
      loadThreads();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const thread = detail?.thread;
  const mailbox = detail?.mailbox;

  return (
    <div className="space-y-4" data-testid="inbox-page">
      <PageIntro title={t("pages.inbox.title")} description={t("pages.inbox.description")} />

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">{t("inbox.title")}</h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-zinc-400">
            {t("inbox.intro")}
            <HelpTip testid="inbox-help" text={t("inbox.help")} />
          </p>
        </div>
        {canSync && (
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={!!syncing} onClick={() => ensureAndSync("google")} className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-zinc-200 hover:bg-zinc-900" data-testid="inbox-sync-google">
              {syncing === "google" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />} {t("inbox.syncGmail")}
            </button>
            <button type="button" disabled={!!syncing} onClick={() => ensureAndSync("microsoft")} className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-zinc-200 hover:bg-zinc-900" data-testid="inbox-sync-outlook">
              {syncing === "microsoft" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />} {t("inbox.syncOutlook")}
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[220px_1fr_1.1fr]">
        {/* Left filters */}
        <aside className="space-y-4 rounded-xl border border-white/10 bg-zinc-950 p-4" data-testid="inbox-filters">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">{t("inbox.viewsTitle")}</p>
            <div className="space-y-1">
              {VIEWS.map((v) => (
                <button key={v.id} type="button" onClick={() => { setView(v.id); setThreads((t) => ({ ...t, page: 1 })); }}
                  className={`flex w-full rounded-lg px-3 py-2 text-left text-sm ${view === v.id ? "bg-brand-600/15 text-brand-300" : "text-zinc-400 hover:bg-zinc-900"}`}
                  data-testid={`inbox-view-${v.id}`}
                >{v.labelKey ? t(v.labelKey) : v.label}</button>
              ))}
            </div>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">{t("inbox.provider")}</p>
            <select aria-label={t("inbox.providerFilter")} className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200" value={provider} onChange={(e) => setProvider(e.target.value)} data-testid="inbox-provider-filter">
              <option value="all">{t("inbox.providers.all")}</option>
              <option value="google">{t("inbox.providers.google")}</option>
              <option value="microsoft">{t("inbox.providers.microsoft")}</option>
            </select>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">{t("inbox.mailboxes")}</p>
            {!mailboxes.length ? (
              <p className="text-xs text-zinc-500">{t("inbox.noMailboxes")}</p>
            ) : (
              <ul className="space-y-2">
                {mailboxes.map((m) => (
                  <li key={m.id} className="rounded-lg border border-white/5 p-2 text-xs text-zinc-400">
                    <button type="button" className={`w-full text-left ${mailboxId === m.id ? "text-brand-300" : ""}`} onClick={() => setMailboxId(mailboxId === m.id ? "" : m.id)}>
                      <span className="font-medium text-zinc-200">{m.emailAddress}</span>
                      <span className="mt-0.5 block capitalize">{t(`inbox.providers.${m.provider}`, { defaultValue: m.provider })} · {t(`inbox.statuses.${m.syncStatus || "idle"}`, { defaultValue: m.syncStatus || "idle" })}</span>
                      <span className="block text-zinc-500">{t("inbox.lastSync", { time: fmtTime(m.lastSuccessfulSyncAt || m.lastSyncAt) })}</span>
                      {m.lastError && <span className="block text-rose-400">{m.lastError}</span>}
                    </button>
                    {canSync && (
                      <button type="button" className="mt-1 text-brand-400 hover:underline" onClick={() => syncOne(m.id)} disabled={!!syncing}>
                        {t("inbox.syncNow")}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>

        {/* Thread list */}
        <section className="rounded-xl border border-white/10 bg-zinc-950" data-testid="inbox-thread-list">
          <div className="border-b border-white/10 p-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <input aria-label={t("inbox.searchLabel")} data-testid="inbox-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("inbox.searchPlaceholder")} className="w-full rounded-lg border border-white/10 bg-zinc-900 py-2 pl-9 pr-3 text-sm text-zinc-100" />
            </div>
          </div>
          {loading ? (
            <div className="flex justify-center py-16 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
          ) : error ? (
            <div className="p-6 text-sm text-rose-300">{error}</div>
          ) : !(threads.items || []).length ? (
            <EmptyState icon={InboxIcon} title={t("inbox.empty.title")} description={t("inbox.empty.description")} />
          ) : (
            <ul className="divide-y divide-white/5">
              {threads.items.map((threadItem) => (
                <li key={threadItem.id}>
                  <button type="button" data-testid={`inbox-thread-${threadItem.id}`} onClick={() => openThread(threadItem.id)}
                    className={`flex w-full flex-col gap-1 px-4 py-3 text-left hover:bg-zinc-900/70 ${selected === threadItem.id ? "bg-brand-600/10" : ""}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className={`truncate text-sm ${(threadItem.unreadCount || 0) > 0 ? "font-semibold text-zinc-50" : "text-zinc-300"}`}>
                        {(threadItem.participantEmails || [])[0] || t("inbox.unknown")}
                      </span>
                      <span className="shrink-0 text-[11px] text-zinc-500">{fmtTime(threadItem.latestMessageAt)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {(threadItem.unreadCount || 0) > 0 && <span className="h-2 w-2 rounded-full bg-brand-400" />}
                      <span className="truncate text-sm text-zinc-200">{threadItem.subject}</span>
                    </div>
                    <p className="truncate text-xs text-zinc-500">{threadItem.snippet}</p>
                    <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-wide text-zinc-500">
                      <span>{t(`inbox.providers.${threadItem.provider}`, { defaultValue: threadItem.provider })}</span>
                      {threadItem.linkedClientId && <span className="text-emerald-400">{t("inbox.client")}</span>}
                      {threadItem.linkedLeadId && <span className="text-sky-400">{t("inbox.lead")}</span>}
                      {threadItem.assignedUserId && <span>{t("inbox.assigned")}</span>}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {threads.pages > 1 && (
            <div className="flex items-center justify-between border-t border-white/10 px-3 py-2 text-xs text-zinc-500">
              <button type="button" disabled={threads.page <= 1} onClick={() => setThreads((t) => ({ ...t, page: t.page - 1 }))}>{t("common.previous")}</button>
              <span>{threads.page} / {threads.pages}</span>
              <button type="button" disabled={threads.page >= threads.pages} onClick={() => setThreads((t) => ({ ...t, page: t.page + 1 }))}>{t("common.next")}</button>
            </div>
          )}
        </section>

        {/* Detail */}
        <section className="rounded-xl border border-white/10 bg-zinc-950 p-4" data-testid="inbox-detail">
          {!selected ? (
            <div className="flex h-full min-h-[320px] items-center justify-center text-sm text-zinc-500">{t("inbox.selectConversation")}</div>
          ) : detailLoading ? (
            <div className="flex justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
          ) : (
            <div className="space-y-4">
              <div>
                <h2 className="text-base font-semibold text-zinc-100">{thread?.subject}</h2>
                <p className="mt-1 text-xs text-zinc-500">
                  {mailbox?.emailAddress} · {thread?.provider}
                  {mailbox?.lastSuccessfulSyncAt ? ` · ${t("inbox.syncedAt", { time: fmtTime(mailbox.lastSuccessfulSyncAt) })}` : ""}
                </p>
              </div>

              {thread?.aiSummary && (
                <div className="rounded-lg border border-brand-500/20 bg-brand-600/10 p-3 text-xs text-zinc-300" data-testid="inbox-ai-summary">
                  <p className="font-medium text-brand-300">{t("inbox.aiSummary.title")}</p>
                  <p className="mt-1">{thread.aiSummary.summary}</p>
                  <p className="mt-2 text-zinc-400">{t("inbox.aiSummary.metadata", { intent: thread.aiSummary.intent, urgency: thread.aiSummary.urgency, sentiment: thread.aiSummary.sentiment })}</p>
                  <p className="mt-1">{t("inbox.aiSummary.next", { next: thread.aiSummary.suggestedNextStep })}</p>
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                <button type="button" disabled={busy} onClick={runSummarize} className="inline-flex items-center gap-1 rounded-lg border border-brand-500/30 px-2.5 py-1.5 text-xs text-brand-300" data-testid="inbox-summarize">
                  <Sparkles className="h-3.5 w-3.5" /> {t("inbox.actions.summarize")}
                </button>
                <button type="button" disabled={busy} onClick={runDraftReply} className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-2.5 py-1.5 text-xs font-semibold text-white" data-testid="inbox-draft-reply">
                  <Mail className="h-3.5 w-3.5" /> {t("inbox.actions.draftReply")}
                </button>
                <button type="button" disabled={busy} onClick={() => inboxApi.patchThread(selected, { assignedUserId: user.id }).then(() => { toast.success(t("inbox.toasts.assigned")); openThread(selected); loadThreads(); })} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-zinc-300">
                  <User className="h-3.5 w-3.5" /> {t("inbox.actions.assignMe")}
                </button>
              </div>

              <div className="rounded-lg border border-white/10 p-3 text-xs">
                <p className="mb-2 font-medium text-zinc-300">{t("inbox.crmLink")}</p>
                <div className="flex flex-wrap gap-2">
                  <input aria-label={t("inbox.clientId")} placeholder={t("inbox.clientId")} className="rounded border border-white/10 bg-zinc-900 px-2 py-1 text-zinc-200" value={linkForm.clientId} onChange={(e) => setLinkForm((s) => ({ ...s, clientId: e.target.value }))} />
                  <input aria-label={t("inbox.leadId")} placeholder={t("inbox.leadId")} className="rounded border border-white/10 bg-zinc-900 px-2 py-1 text-zinc-200" value={linkForm.leadId} onChange={(e) => setLinkForm((s) => ({ ...s, leadId: e.target.value }))} />
                  <button type="button" onClick={runLink} className="inline-flex items-center gap-1 text-emerald-400" data-testid="inbox-link"><Link2 className="h-3.5 w-3.5" /> {t("inbox.actions.link")}</button>
                  <button type="button" onClick={runUnlink} className="inline-flex items-center gap-1 text-zinc-400" data-testid="inbox-unlink"><Unlink className="h-3.5 w-3.5" /> {t("inbox.actions.unlink")}</button>
                </div>
                <p className="mt-2 text-zinc-500">
                  {thread?.linkedClientId ? t("inbox.linkedClient", { id: thread.linkedClientId }) : t("inbox.noClient")}
                  {" · "}
                  {thread?.linkedLeadId ? t("inbox.linkedLead", { id: thread.linkedLeadId }) : t("inbox.noLead")}
                </p>
              </div>

              <div className="max-h-[50vh] space-y-3 overflow-y-auto" data-testid="inbox-messages">
                {messages.map((m) => (
                  <article key={`${m.kind}-${m.id}`} className="rounded-lg border border-white/10 bg-zinc-900/40 p-3">
                    <div className="mb-2 flex items-center justify-between text-[11px] text-zinc-500">
                      <span>
                        {m.kind === "outbound"
                          ? t(m.sentVia ? "inbox.messages.youSentVia" : "inbox.messages.youSent", { provider: m.sentVia })
                          : (m.from || m.fromRaw || "—")}
                      </span>
                      <span className="flex items-center gap-2">
                        {m.deliveryWarning && <span className="text-amber-300">{t("inbox.messages.deliveryUnconfirmed")}</span>}
                        {m.kind === "outbound" && (
                          <a href={`/emails?draft=${m.id}`} className="text-brand-400 hover:underline">{t("inbox.messages.openEmailCenter")}</a>
                        )}
                        <span>{fmtTime(m.receivedAt || m.sentAt)}</span>
                      </span>
                    </div>
                    {m.kind === "inbound" && m.sanitizedHtmlBody ? (
                      <div className="prose-invert max-w-none text-sm text-zinc-300 [&_a]:text-brand-400" dangerouslySetInnerHTML={{ __html: m.sanitizedHtmlBody }} />
                    ) : (
                      <pre className="whitespace-pre-wrap font-sans text-sm text-zinc-300">{m.textBody || m.snippet || ""}</pre>
                    )}
                    {(m.attachments || []).length > 0 && (
                      <ul className="mt-2 space-y-1 text-xs text-zinc-500">
                        {m.attachments.map((a) => (
                          <li key={a.providerAttachmentId}>{t("inbox.messages.attachment", { filename: a.filename, size: Math.round((a.size || 0) / 1024) })}</li>
                        ))}
                      </ul>
                    )}
                  </article>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
