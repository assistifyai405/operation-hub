import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Loader2, Mail, RefreshCw, Link2, Unlink, Sparkles, User, Search, Inbox as InboxIcon,
} from "lucide-react";
import { toast } from "sonner";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { inboxApi, integrationsApi } from "@/lib/api";
import { inboxNl, fmtNlDate } from "@/lib/nlCopy";
import EmptyState from "@/components/EmptyState";
import HelpTip from "@/components/HelpTip";

const VIEWS = [
  { id: "all", label: inboxNl.viewAll },
  { id: "unread", label: inboxNl.viewUnread },
  { id: "assigned", label: inboxNl.viewAssigned },
  { id: "linked", label: inboxNl.viewLinked },
  { id: "unlinked", label: inboxNl.viewUnlinked },
];

const PROVIDER_LABELS = { google: "Gmail", microsoft: "Outlook" };
const SYNC_STATUS_NL = {
  idle: "Inactief",
  syncing: "Synchroniseert",
  success: "Gesynchroniseerd",
  error: "Fout",
};

const providerLabel = (provider) => PROVIDER_LABELS[provider] || provider;

const providerIsConnected = (status, provider) => {
  const readiness = status?.oauthReadiness?.[provider] || status?.providers?.[provider]?.readiness;
  const providerStatus = status?.providers?.[provider]?.status;
  return readiness === "connected" || providerStatus === "connected";
};

export default function Inbox() {
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
  const [connectionStatus, setConnectionStatus] = useState(null);

  const loadMailboxes = useCallback(async () => {
    try {
      const res = await inboxApi.mailboxes();
      setMailboxes(res.items || []);
    } catch (e) {
      /* ignore */
    }
  }, []);

  const loadConnectionStatus = useCallback(async () => {
    try {
      const res = await integrationsApi.status();
      setConnectionStatus(res);
      return res;
    } catch {
      return null;
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
      setError(e.message || "Inbox laden mislukt");
    } finally {
      setLoading(false);
    }
  }, [threadParams]);

  useEffect(() => { loadMailboxes(); }, [loadMailboxes]);
  useEffect(() => { loadConnectionStatus(); }, [loadConnectionStatus]);
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
      toast.error(inboxNl.adminOnlySync);
      return;
    }
    const status = connectionStatus || await loadConnectionStatus();
    if (status && !providerIsConnected(status, prov)) {
      toast.error(`Koppel ${providerLabel(prov)} eerst onder Integraties en probeer daarna opnieuw.`);
      return;
    }
    setSyncing(prov);
    try {
      const mb = await inboxApi.ensureMailbox(prov);
      const res = await inboxApi.syncMailbox(mb.id);
      toast.success(`${providerLabel(prov)} gesynchroniseerd: ${res.messagesCreated || 0} nieuwe bericht(en).`);
      await loadMailboxes();
      await loadThreads();
    } catch (e) {
      toast.error(e.message || "Synchroniseren mislukt. Controleer Integraties en probeer opnieuw.");
    } finally {
      setSyncing(null);
    }
  };

  const syncOne = async (id) => {
    if (!canSync) return;
    setSyncing(id);
    try {
      const res = await inboxApi.syncMailbox(id);
      toast.success(`${res.messagesCreated || 0} nieuwe bericht(en) gesynchroniseerd.`);
      await loadMailboxes();
      await loadThreads();
    } catch (e) {
      toast.error(e.message || "Synchroniseren mislukt.");
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
      toast.success("Samenvatting klaar");
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
      toast.success("Antwoordconcept gemaakt — E-mailcentrum openen");
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
      toast.error("Voer een klant- of lead-ID in");
      return;
    }
    setBusy(true);
    try {
      await inboxApi.link(selected, {
        clientId: linkForm.clientId || undefined,
        leadId: linkForm.leadId || undefined,
      });
      toast.success("Gekoppeld");
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
      toast.success("Ontkoppeld");
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
  const hasMailboxes = mailboxes.length > 0;
  const syncDisabled = !hasMailboxes || !!syncing;
  const syncDisabledProps = !hasMailboxes
    ? { title: inboxNl.syncDisabledHint, "aria-label": inboxNl.syncDisabledHint }
    : {};

  return (
    <div className="space-y-4" data-testid="inbox-page">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">{inboxNl.title}</h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-zinc-400">
            {inboxNl.subtitle}
            <HelpTip testid="inbox-help" text={inboxNl.help} />
          </p>
        </div>
        {canSync && (
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={syncDisabled} onClick={() => ensureAndSync("google")} className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-zinc-200 hover:bg-zinc-900 disabled:opacity-50" data-testid="inbox-sync-google" {...syncDisabledProps}>
              {syncing === "google" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />} {inboxNl.syncGmail}
            </button>
            <button type="button" disabled={syncDisabled} onClick={() => ensureAndSync("microsoft")} className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-zinc-200 hover:bg-zinc-900 disabled:opacity-50" data-testid="inbox-sync-outlook" {...syncDisabledProps}>
              {syncing === "microsoft" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />} {inboxNl.syncOutlook}
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[220px_1fr_1.1fr]">
        {/* Left filters */}
        <aside className="space-y-4 rounded-xl border border-white/10 bg-zinc-950 p-4" data-testid="inbox-filters">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">{inboxNl.views}</p>
            <div className="space-y-1">
              {VIEWS.map((v) => (
                <button key={v.id} type="button" onClick={() => { setView(v.id); setThreads((t) => ({ ...t, page: 1 })); }}
                  className={`flex w-full rounded-lg px-3 py-2 text-left text-sm ${view === v.id ? "bg-violet-600/15 text-violet-300" : "text-zinc-400 hover:bg-zinc-900"}`}
                  data-testid={`inbox-view-${v.id}`}
                >{v.label}</button>
              ))}
            </div>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">{inboxNl.provider}</p>
            <select aria-label="Providerfilter" className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200" value={provider} onChange={(e) => setProvider(e.target.value)} data-testid="inbox-provider-filter">
              <option value="all">{inboxNl.all}</option>
              <option value="google">Gmail</option>
              <option value="microsoft">Outlook</option>
            </select>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">{inboxNl.mailboxes}</p>
            {!mailboxes.length ? (
              <p className="text-xs text-zinc-500">{inboxNl.noMailbox}</p>
            ) : (
              <ul className="space-y-2">
                {mailboxes.map((m) => (
                  <li key={m.id} className="rounded-lg border border-white/5 p-2 text-xs text-zinc-400">
                    <button type="button" className={`w-full text-left ${mailboxId === m.id ? "text-violet-300" : ""}`} onClick={() => setMailboxId(mailboxId === m.id ? "" : m.id)}>
                      <span className="font-medium text-zinc-200">{m.emailAddress}</span>
                      <span className="mt-0.5 block">{providerLabel(m.provider)} · {SYNC_STATUS_NL[m.syncStatus] || m.syncStatus || SYNC_STATUS_NL.idle}</span>
                      <span className="block text-zinc-500">{inboxNl.lastSync}: {fmtNlDate(m.lastSuccessfulSyncAt || m.lastSyncAt)}</span>
                      {m.lastError && <span className="block text-rose-400">{m.lastError}</span>}
                    </button>
                    {canSync && (
                      <button type="button" className="mt-1 text-violet-400 hover:underline" onClick={() => syncOne(m.id)} disabled={!!syncing}>
                        {inboxNl.syncNow}
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
              <input aria-label="Zoek in inbox" data-testid="inbox-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={inboxNl.search} className="w-full rounded-lg border border-white/10 bg-zinc-900 py-2 pl-9 pr-3 text-sm text-zinc-100" />
            </div>
          </div>
          {!hasMailboxes ? (
            <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
              <InboxIcon className="h-10 w-10 text-violet-400" />
              <h2 className="mt-4 text-sm font-semibold text-zinc-100">{inboxNl.noMailboxTitle}</h2>
              <p className="mt-1 max-w-md text-sm text-zinc-500">{inboxNl.noMailboxBody}</p>
              <button
                type="button"
                onClick={() => navigate("/integrations")}
                data-testid="inbox-go-integrations"
                className="mt-5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500"
              >
                {inboxNl.goIntegrations}
              </button>
            </div>
          ) : loading ? (
            <div className="flex justify-center py-16 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
          ) : error ? (
            <div className="p-6 text-sm text-rose-300">{error}</div>
          ) : !(threads.items || []).length ? (
            <EmptyState icon={InboxIcon} title={inboxNl.emptyTitle} description={inboxNl.emptyBody} />
          ) : (
            <ul className="divide-y divide-white/5">
              {threads.items.map((t) => (
                <li key={t.id}>
                  <button type="button" data-testid={`inbox-thread-${t.id}`} onClick={() => openThread(t.id)}
                    className={`flex w-full flex-col gap-1 px-4 py-3 text-left hover:bg-zinc-900/70 ${selected === t.id ? "bg-violet-600/10" : ""}`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className={`truncate text-sm ${(t.unreadCount || 0) > 0 ? "font-semibold text-zinc-50" : "text-zinc-300"}`}>
                        {(t.participantEmails || [])[0] || "Onbekend"}
                      </span>
                      <span className="shrink-0 text-[11px] text-zinc-500">{fmtNlDate(t.latestMessageAt)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {(t.unreadCount || 0) > 0 && <span className="h-2 w-2 rounded-full bg-violet-400" />}
                      <span className="truncate text-sm text-zinc-200">{t.subject}</span>
                    </div>
                    <p className="truncate text-xs text-zinc-500">{t.snippet}</p>
                    <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-wide text-zinc-500">
                      <span>{providerLabel(t.provider)}</span>
                      {t.linkedClientId && <span className="text-emerald-400">Klant</span>}
                      {t.linkedLeadId && <span className="text-sky-400">Lead</span>}
                      {t.assignedUserId && <span>Toegewezen</span>}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {threads.pages > 1 && (
            <div className="flex items-center justify-between border-t border-white/10 px-3 py-2 text-xs text-zinc-500">
              <button type="button" disabled={threads.page <= 1} onClick={() => setThreads((t) => ({ ...t, page: t.page - 1 }))}>Vorige</button>
              <span>{threads.page} / {threads.pages}</span>
              <button type="button" disabled={threads.page >= threads.pages} onClick={() => setThreads((t) => ({ ...t, page: t.page + 1 }))}>Volgende</button>
            </div>
          )}
        </section>

        {/* Detail */}
        <section className="rounded-xl border border-white/10 bg-zinc-950 p-4" data-testid="inbox-detail">
          {!selected ? (
            <div className="flex h-full min-h-[320px] items-center justify-center text-sm text-zinc-500">{inboxNl.selectConversation}</div>
          ) : detailLoading ? (
            <div className="flex justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
          ) : (
            <div className="space-y-4">
              <div>
                <h2 className="text-base font-semibold text-zinc-100">{thread?.subject}</h2>
                <p className="mt-1 text-xs text-zinc-500">
                  {mailbox?.emailAddress} · {providerLabel(thread?.provider)}
                  {mailbox?.lastSuccessfulSyncAt ? ` · Gesynchroniseerd ${fmtNlDate(mailbox.lastSuccessfulSyncAt)}` : ""}
                </p>
              </div>

              {thread?.aiSummary && (
                <div className="rounded-lg border border-violet-500/20 bg-violet-600/10 p-3 text-xs text-zinc-300" data-testid="inbox-ai-summary">
                  <p className="font-medium text-violet-300">AI-samenvatting</p>
                  <p className="mt-1">{thread.aiSummary.summary}</p>
                  <p className="mt-2 text-zinc-400">Intentie: {thread.aiSummary.intent} · Urgentie: {thread.aiSummary.urgency} · Sentiment: {thread.aiSummary.sentiment}</p>
                  <p className="mt-1">Volgende stap: {thread.aiSummary.suggestedNextStep}</p>
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                <button type="button" disabled={busy} onClick={runSummarize} className="inline-flex items-center gap-1 rounded-lg border border-violet-500/30 px-2.5 py-1.5 text-xs text-violet-300" data-testid="inbox-summarize">
                  <Sparkles className="h-3.5 w-3.5" /> Samenvatten
                </button>
                <button type="button" disabled={busy} onClick={runDraftReply} className="inline-flex items-center gap-1 rounded-lg bg-violet-600 px-2.5 py-1.5 text-xs font-semibold text-white" data-testid="inbox-draft-reply">
                  <Mail className="h-3.5 w-3.5" /> Antwoordconcept
                </button>
                <button type="button" disabled={busy} onClick={() => inboxApi.patchThread(selected, { assignedUserId: user.id }).then(() => { toast.success("Aan jou toegewezen"); openThread(selected); loadThreads(); })} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-zinc-300">
                  <User className="h-3.5 w-3.5" /> Aan mij toewijzen
                </button>
              </div>

              <div className="rounded-lg border border-white/10 p-3 text-xs">
                <p className="mb-2 font-medium text-zinc-300">CRM-koppeling</p>
                <div className="flex flex-wrap gap-2">
                  <input aria-label="Klant-ID" placeholder="Klant-ID" className="rounded border border-white/10 bg-zinc-900 px-2 py-1 text-zinc-200" value={linkForm.clientId} onChange={(e) => setLinkForm((s) => ({ ...s, clientId: e.target.value }))} />
                  <input aria-label="Lead-ID" placeholder="Lead-ID" className="rounded border border-white/10 bg-zinc-900 px-2 py-1 text-zinc-200" value={linkForm.leadId} onChange={(e) => setLinkForm((s) => ({ ...s, leadId: e.target.value }))} />
                  <button type="button" onClick={runLink} className="inline-flex items-center gap-1 text-emerald-400" data-testid="inbox-link"><Link2 className="h-3.5 w-3.5" /> Koppelen</button>
                  <button type="button" onClick={runUnlink} className="inline-flex items-center gap-1 text-zinc-400" data-testid="inbox-unlink"><Unlink className="h-3.5 w-3.5" /> Ontkoppelen</button>
                </div>
                <p className="mt-2 text-zinc-500">
                  {thread?.linkedClientId ? `Klant: ${thread.linkedClientId}` : "Geen klant"}
                  {" · "}
                  {thread?.linkedLeadId ? `Lead: ${thread.linkedLeadId}` : "Geen lead"}
                </p>
              </div>

              <div className="max-h-[50vh] space-y-3 overflow-y-auto" data-testid="inbox-messages">
                {messages.map((m) => (
                  <article key={`${m.kind}-${m.id}`} className="rounded-lg border border-white/10 bg-zinc-900/40 p-3">
                    <div className="mb-2 flex items-center justify-between text-[11px] text-zinc-500">
                      <span>
                        {m.kind === "outbound"
                          ? `Jij (verstuurd${m.sentVia ? ` via ${m.sentVia}` : ""})`
                          : (m.from || m.fromRaw || "—")}
                      </span>
                      <span className="flex items-center gap-2">
                        {m.deliveryWarning && <span className="text-amber-300">Bezorging onbevestigd</span>}
                        {m.kind === "outbound" && (
                          <a href={`/emails?draft=${m.id}`} className="text-violet-400 hover:underline">Openen in E-mailcentrum</a>
                        )}
                        <span>{fmtNlDate(m.receivedAt || m.sentAt)}</span>
                      </span>
                    </div>
                    {m.kind === "inbound" && m.sanitizedHtmlBody ? (
                      <div className="prose-invert max-w-none text-sm text-zinc-300 [&_a]:text-violet-400" dangerouslySetInnerHTML={{ __html: m.sanitizedHtmlBody }} />
                    ) : (
                      <pre className="whitespace-pre-wrap font-sans text-sm text-zinc-300">{m.textBody || m.snippet || ""}</pre>
                    )}
                    {(m.attachments || []).length > 0 && (
                      <ul className="mt-2 space-y-1 text-xs text-zinc-500">
                        {m.attachments.map((a) => (
                          <li key={a.providerAttachmentId}>{a.filename} ({Math.round((a.size || 0) / 1024)} KB) — downloaden via geauthenticeerde inbox-API</li>
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
