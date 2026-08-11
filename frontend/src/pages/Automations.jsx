import PageIntro from "@/components/PageIntro";
import { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  Zap, Loader2, Plus, Play, Pause, ChevronDown, CheckCircle2, Inbox, History as HistoryIcon,
  SlidersHorizontal, ShieldCheck, PauseCircle,
} from "lucide-react";
import { automationApi } from "@/lib/api";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { AutomationCard } from "@/components/automation/AutomationCard";
import { ApprovalCard } from "@/components/automation/ApprovalCard";
import { AutomationBuilder } from "@/components/automation/AutomationBuilder";
import { AutomationSettingsPanel } from "@/components/automation/AutomationSettingsPanel";
import { PAUSE_OPTIONS } from "@/components/automation/automationShared";
import { useLocale } from "@/context/LocaleContext";
import { formatRelativeTime } from "@/i18n/format";

const APPROVAL_TABS = [
  "pending", "suggested", "executed", "rejected",
];

export default function Automations() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const [summary, setSummary] = useState(null);
  const [tab, setTab] = useState("automations");
  const [automations, setAutomations] = useState([]);
  const [approvals, setApprovals] = useState({ items: [], counts: {}, total_time_saved: 0 });
  const [approvalStatus, setApprovalStatus] = useState("pending");
  const [logs, setLogs] = useState([]);
  const [settings, setSettings] = useState(null);
  const [options, setOptions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editing, setEditing] = useState(null);

  const loadSummary = useCallback(() => automationApi.summary().then(setSummary).catch(() => {}), []);
  const loadAutomations = useCallback(() => automationApi.automations().then(setAutomations).catch(() => {}), []);
  const loadApprovals = useCallback((st) => automationApi.approvals(st).then(setApprovals).catch(() => {}), []);
  const loadLogs = useCallback(() => automationApi.logs().then((d) => setLogs(d.items)).catch(() => {}), []);
  const loadSettings = useCallback(() => automationApi.getSettings().then(setSettings).catch(() => {}), []);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadSummary(), loadAutomations(), loadApprovals("pending"), loadSettings(),
      automationApi.builderOptions().then(setOptions).catch(() => {})]).finally(() => setLoading(false));
  }, [loadSummary, loadAutomations, loadApprovals, loadSettings]);

  useEffect(() => { if (tab === "history") loadLogs(); }, [tab, loadLogs]);

  const refreshAll = () => { loadSummary(); loadAutomations(); loadApprovals(approvalStatus); };

  const runNow = async () => {
    setBusy(true);
    try {
      const r = await automationApi.run();
      toast.success(t("automations.toasts.scanComplete", r));
      refreshAll();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  const toggleMaster = async (v) => {
    try {
      const s = await automationApi.updateSettings({ enabled: v });
      setSettings(s); loadSummary();
      toast.success(v ? t("automations.toasts.enabled") : t("automations.toasts.allPaused"));
    } catch (e) { toast.error(e.message); }
  };

  const pauseAll = async (duration) => {
    try {
      const s = await automationApi.pause(duration);
      setSettings(s); loadSummary();
      toast.success(t("automations.toasts.paused"));
    } catch (e) { toast.error(e.message); }
  };
  const resumeAll = async () => {
    try {
      const s = await automationApi.resume();
      setSettings(s); loadSummary();
      toast.success(t("automations.toasts.resumed"));
    } catch (e) { toast.error(e.message); }
  };

  // automation handlers
  const onToggle = async (a, v) => {
    try { await automationApi.toggleAutomation(a.id, v); loadAutomations(); loadSummary(); }
    catch (e) { toast.error(e.message); }
  };
  const onMode = async (a, mode) => {
    try { await automationApi.setMode(a.id, mode); loadAutomations(); toast.success(t("automations.toasts.modeSet", { mode })); }
    catch (e) { toast.error(e.message); }
  };
  const onDelete = async (a) => {
    if (!window.confirm(t("automations.confirm.delete", { name: a.name }))) return;
    try { await automationApi.deleteAutomation(a.id); loadAutomations(); loadSummary(); toast.success(t("automations.toasts.deleted")); }
    catch (e) { toast.error(e.message); }
  };
  const onEditRule = (a) => { setEditing(a); setBuilderOpen(true); };
  const saveBuilder = async (body) => {
    try {
      if (editing) { await automationApi.updateAutomation(editing.id, body); toast.success(t("automations.toasts.updated")); }
      else { await automationApi.createAutomation(body); toast.success(t("automations.toasts.created")); }
      setBuilderOpen(false); setEditing(null); loadAutomations(); loadSummary();
    } catch (e) { toast.error(e.message); }
  };

  // approval handlers
  const onApprove = async (item) => {
    setBusy(true);
    try { const r = await automationApi.approve(item.id); toast.success(r.status === "executed" ? t("automations.toasts.approvedDone") : t("automations.toasts.approvedPartial")); loadApprovals(approvalStatus); loadSummary(); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const onReject = async (item) => {
    setBusy(true);
    try { await automationApi.reject(item.id); toast.success(t("automations.toasts.dismissed")); loadApprovals(approvalStatus); loadSummary(); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const onPrepare = async (item) => {
    setBusy(true);
    try { await automationApi.prepareSuggestion(item.id); toast.success(t("automations.toasts.prepared")); loadApprovals(approvalStatus); loadSummary(); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const onEditApproval = async (item, actions) => {
    try { await automationApi.editApproval(item.id, actions); toast.success(t("automations.toasts.draftUpdated")); loadApprovals(approvalStatus); }
    catch (e) { toast.error(e.message); }
  };
  const onDisableFromApproval = async (item) => {
    if (!window.confirm(t("automations.confirm.disable", { name: item.automation_name }))) return;
    try { await automationApi.toggleAutomation(item.automation_id, false); toast.success(t("automations.toasts.disabled")); loadApprovals(approvalStatus); loadAutomations(); loadSummary(); }
    catch (e) { toast.error(e.message); }
  };

  const switchApprovalStatus = (st) => { setApprovalStatus(st); loadApprovals(st); };

  const saveSettings = async (patch) => {
    const next = { ...settings, ...patch };
    setSettings(next);
    try { const s = await automationApi.updateSettings(patch); setSettings(s); loadSummary(); }
    catch (e) { toast.error(e.message); loadSettings(); }
  };

  const paused = summary?.paused;

  return (
    <div className="space-y-6" data-testid="automations-page">
      <PageIntro title={t("pages.automations.title")} description={t("pages.automations.description")} />

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2.5 text-3xl font-bold tracking-tight text-zinc-50">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 glow-brand"><Zap className="h-5 w-5 text-white" /></span>
            {t("automations.title")}
          </h1>
          <p className="mt-1.5 max-w-2xl text-sm text-zinc-400">
            {t("automations.intro")}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={runNow} disabled={busy} data-testid="run-now-btn" className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-sm font-medium text-zinc-300 transition-all hover:border-brand-500/40 hover:text-zinc-100 disabled:opacity-50">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} {t("automations.actions.runNow")}
          </button>
          {paused ? (
            <button onClick={resumeAll} data-testid="resume-all-btn" className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white transition-all hover:bg-emerald-500">
              <Play className="h-4 w-4" /> {t("automations.actions.resume")}
            </button>
          ) : (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button data-testid="pause-all-btn" className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-sm font-medium text-zinc-300 transition-all hover:text-zinc-100">
                  <Pause className="h-4 w-4" /> {t("automations.actions.pauseAll")} <ChevronDown className="h-3.5 w-3.5" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="border-white/10 bg-zinc-950 text-zinc-200">
                {PAUSE_OPTIONS.map((o) => (
                  <DropdownMenuItem key={o.v} onClick={() => pauseAll(o.v)} data-testid={`pause-${o.v}`} className="focus:bg-zinc-900">{t(`automations.pauseOptions.${o.v}`)}</DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          <button onClick={() => { setEditing(null); setBuilderOpen(true); }} data-testid="new-automation-btn" className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-500">
            <Plus className="h-4 w-4" /> {t("automations.actions.new")}
          </button>
        </div>
      </div>

      {/* Status strip */}
      {summary && (
        <div className="flex flex-wrap items-center gap-3" data-testid="automation-status-strip">
          <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${paused ? "border-amber-500/30 bg-amber-500/15 text-amber-300" : summary.enabled ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-300" : "border-zinc-600/40 bg-zinc-800/40 text-zinc-400"}`}>
            {paused ? <PauseCircle className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
            {paused ? t("automations.status.pausedUntil", { time: formatRelativeTime(summary.paused_until, locale, t) }) : summary.enabled ? t("automations.status.active") : t("automations.status.off")}
          </span>
          <span className="rounded-full border border-white/10 bg-zinc-900 px-3 py-1 text-xs text-zinc-400">{t("automations.status.enabledCount", { active: summary.active_automations, total: summary.total_automations })}</span>
          <span className="rounded-full border border-brand-500/20 bg-brand-500/[0.08] px-3 py-1 text-xs text-brand-200" data-testid="summary-pending">{t("automations.status.awaiting", { count: summary.pending })}</span>
          <span className="rounded-full border border-white/10 bg-zinc-900 px-3 py-1 text-xs text-zinc-400">{t("automations.status.completedSaved", { count: summary.executed_count, minutes: summary.time_saved_total })}</span>
        </div>
      )}

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="bg-zinc-900/60" data-testid="automation-tabs">
          <TabsTrigger value="automations" data-testid="tab-automations"><Zap className="mr-1.5 h-4 w-4" /> {t("automations.tabs.automations")}</TabsTrigger>
          <TabsTrigger value="approvals" data-testid="tab-approvals"><Inbox className="mr-1.5 h-4 w-4" /> {t("automations.tabs.approvals")}{summary?.pending ? ` (${summary.pending})` : ""}</TabsTrigger>
          <TabsTrigger value="history" data-testid="tab-history"><HistoryIcon className="mr-1.5 h-4 w-4" /> {t("automations.tabs.history")}</TabsTrigger>
          <TabsTrigger value="settings" data-testid="tab-settings"><SlidersHorizontal className="mr-1.5 h-4 w-4" /> {t("automations.tabs.settings")}</TabsTrigger>
        </TabsList>

        {loading ? (
          <div className="flex items-center justify-center py-20 text-zinc-600"><Loader2 className="h-7 w-7 animate-spin" /></div>
        ) : (
          <>
            <TabsContent value="automations" className="mt-5 space-y-3">
              {automations.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-white/10 bg-zinc-950 px-4 py-16 text-center" data-testid="automations-empty">
                  <Zap className="mx-auto h-9 w-9 text-zinc-600" aria-hidden="true" />
                  <p className="mt-3 text-sm font-semibold text-zinc-200">{t("automations.empty.title")}</p>
                  <p className="mx-auto mt-1 max-w-md text-xs text-zinc-500">
                    {t("automations.empty.description")}
                  </p>
                  <button
                    type="button"
                    onClick={() => { setEditing(null); setBuilderOpen(true); }}
                    data-testid="automations-empty-action"
                    className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500"
                  >
                    <Plus className="h-4 w-4" aria-hidden="true" /> {t("automations.empty.action")}
                  </button>
                </div>
              ) : (
                automations.map((a) => (
                  <AutomationCard key={a.id} a={a} onToggle={onToggle} onMode={onMode} onEdit={onEditRule} onDelete={onDelete} />
                ))
              )}
            </TabsContent>

            <TabsContent value="approvals" className="mt-5 space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                {APPROVAL_TABS.map((status) => (
                  <button key={status} onClick={() => switchApprovalStatus(status)} data-testid={`approval-tab-${status}`}
                    className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all ${approvalStatus === status ? "border-brand-500 bg-brand-600/15 text-brand-200" : "border-white/10 bg-zinc-900 text-zinc-400 hover:text-zinc-200"}`}>
                    {t(`automations.approvalStatus.${status}`)} <span className="rounded-full bg-white/10 px-1.5 text-[10px]">{approvals.counts?.[status] || 0}</span>
                  </button>
                ))}
              </div>
              {approvals.items.length === 0 ? (
                <div className="rounded-2xl border border-white/10 bg-zinc-950 py-16 text-center" data-testid="approvals-empty">
                  <CheckCircle2 className="mx-auto h-9 w-9 text-emerald-500" />
                  <p className="mt-3 text-sm font-semibold text-zinc-200">{t("automations.approvalsEmpty.title")}</p>
                  <p className="mx-auto mt-1 max-w-sm text-xs text-zinc-500">{t("automations.approvalsEmpty.description")}</p>
                </div>
              ) : (
                approvals.items.map((item) => (
                  <ApprovalCard key={item.id} item={item} busy={busy}
                    onApprove={onApprove} onReject={onReject} onPrepare={onPrepare} onEdit={onEditApproval} onDisable={onDisableFromApproval} />
                ))
              )}
            </TabsContent>

            <TabsContent value="history" className="mt-5">
              {logs.length === 0 ? (
                <div className="rounded-2xl border border-white/10 bg-zinc-950 py-16 text-center text-sm text-zinc-500" data-testid="history-empty">{t("automations.historyEmpty")}</div>
              ) : (
                <div className="rounded-2xl border border-white/10 bg-zinc-950" data-testid="automation-history">
                  {logs.map((l) => (
                    <div key={l.id} className="flex items-start gap-3 border-b border-white/5 px-4 py-3 last:border-0" data-testid="history-item">
                      <span className={`mt-0.5 rounded-md px-2 py-0.5 text-[10px] font-semibold ${eventChip(l.event)}`}>{l.event_label}</span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-zinc-200">{l.message}</p>
                        <p className="text-[11px] text-zinc-600">{l.automation_name} · {formatRelativeTime(l.created_at, locale, t)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="settings" className="mt-5">
              <AutomationSettingsPanel settings={settings} onChange={saveSettings} />
            </TabsContent>
          </>
        )}
      </Tabs>

      <AutomationBuilder open={builderOpen} onOpenChange={(v) => { setBuilderOpen(v); if (!v) setEditing(null); }} options={options} initial={editing} onSave={saveBuilder} />
    </div>
  );
}

function eventChip(event) {
  if (["executed", "approved", "enabled"].includes(event)) return "bg-emerald-500/15 text-emerald-300";
  if (["rejected", "failed", "disabled"].includes(event)) return "bg-red-500/15 text-red-300";
  if (["action_prepared", "trigger_detected", "conditions_evaluated"].includes(event)) return "bg-brand-500/15 text-brand-300";
  if (event === "paused") return "bg-amber-500/15 text-amber-300";
  return "bg-zinc-700/40 text-zinc-300";
}
