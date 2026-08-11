import { useCallback, useEffect, useState } from "react";
import { Loader2, Activity, RefreshCw, Wrench } from "lucide-react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import { opsApi } from "@/lib/api";
import { localizeApiError } from "@/i18n/errors";
import { SectionCard } from "@/components/settings/fields";

export function OperationsSection() {
  const { t, i18n } = useTranslation();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await opsApi.status());
    } catch (e) {
      toast.error(localizeApiError(t, e));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => { load(); }, [load]);

  const run = async (successKey, fn) => {
    setBusy(true);
    try {
      await fn();
      toast.success(t(successKey));
      await load();
    } catch (e) {
      toast.error(localizeApiError(t, e));
    } finally {
      setBusy(false);
    }
  };

  if (loading && !data) {
    return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-zinc-500" /></div>;
  }

  const mailboxes = data?.mailboxes || [];
  const ai = data?.aiUsage || {};
  const workerStatus = data?.worker?.status || (data?.workerEnabled ? "enabled" : "inline");
  const schedulerStatus = data?.scheduler?.status || (data?.schedulerEnabled ? "enabled" : "off");
  const statusLabel = (value) => {
    if (value == null || value === "") return "—";
    const key = String(value).toLowerCase().replace(/[^a-z0-9]+/g, "_");
    return t(`settings.operations.statuses.${key}`, { defaultValue: String(value) });
  };
  const formatDate = (value) => {
    if (!value) return t("settings.operations.never");
    try {
      const date = new Date(value);
      return Number.isNaN(date.getTime())
        ? String(value)
        : date.toLocaleString(i18n.resolvedLanguage || i18n.language);
    } catch {
      return String(value);
    }
  };

  return (
    <SectionCard title={t("settings.operations.title")} description={t("settings.operations.description")} testid="settings-operations">
      <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4" data-testid="ops-status-grid">
        <Stat label={t("settings.operations.release")} value={data?.release || "—"} />
        <Stat label={t("settings.operations.appHealth")} value={statusLabel(data?.status || (data?.mongodb?.ok ? "ok" : "down"))} bad={data?.status === "degraded" || !data?.mongodb?.ok} />
        <Stat label="MongoDB" value={statusLabel(data?.mongodb?.ok ? "ok" : "down")} bad={!data?.mongodb?.ok} />
        <Stat label="Redis" value={statusLabel(data?.redis?.ok ? "ok" : (data?.redis?.configured ? "down" : "unset"))} bad={data?.redis?.configured && !data?.redis?.ok} />
        <Stat label={t("settings.operations.workspaces")} value={String(data?.organizationCount ?? "—")} />
        <Stat label={t("settings.operations.workspaceUsers")} value={String(data?.workspaceUserCount ?? "—")} />
        <Stat label={t("beta.aiRequestsToday")} value={String(ai.used ?? 0)} testid="ops-ai-used" />
        <Stat label={t("beta.aiDailyLimit")} value={ai.unlimited ? statusLabel("unlimited") : String(ai.limit ?? data?.aiDailyLimit ?? "—")} testid="ops-ai-limit" />
        <Stat label={t("beta.betaFeedback")} value={String(data?.betaFeedbackCount ?? 0)} testid="ops-feedback-count" />
        <Stat label={t("beta.failedJobs")} value={String(data?.failedJobs ?? 0)} bad={(data?.failedJobs || 0) > 0} />
        <Stat label={t("beta.worker")} value={statusLabel(workerStatus)} />
        <Stat label={t("beta.scheduler")} value={statusLabel(schedulerStatus)} />
        <Stat label={t("settings.operations.queueDepth")} value={String(data?.jobs?.queueDepth ?? "—")} />
        <Stat label={t("settings.operations.failedQueueDepth")} value={String(data?.jobs?.failedDepth ?? "—")} bad={(data?.jobs?.failedDepth || 0) > 0} />
        <Stat label={t("settings.operations.stuckEmails")} value={String(data?.stuckEmails ?? 0)} bad={(data?.stuckEmails || 0) > 0} />
        <Stat label={t("settings.operations.unhealthyIntegrations")} value={String(data?.unhealthyIntegrations ?? 0)} bad={(data?.unhealthyIntegrations || 0) > 0} />
        <Stat label={t("settings.operations.betaMode")} value={statusLabel(data?.betaMode ? "on" : "off")} />
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-zinc-400">{t("settings.operations.mailboxes")}</p>
        {mailboxes.length === 0 ? (
          <p className="text-xs text-zinc-500">{t("settings.operations.noMailboxes")}</p>
        ) : (
          <ul className="space-y-2">
            {mailboxes.map((m) => (
              <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-300">
                <span>{m.provider} · {m.emailAddress || m.id} · {statusLabel(m.syncStatus)} · {t("settings.operations.lastSync", { date: formatDate(m.lastSuccessfulSyncAt) })}</span>
                <button
                  type="button"
                  disabled={busy}
                  data-testid={`ops-sync-${m.id}`}
                  onClick={() => run("settings.operations.syncQueued", () => opsApi.syncMailbox(m.id))}
                  className="inline-flex items-center gap-1 rounded border border-white/10 px-2 py-1 hover:bg-zinc-900"
                >
                  <RefreshCw className="h-3 w-3" /> {t("settings.operations.sync")}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          data-testid="ops-reconcile"
          onClick={() => run("settings.operations.reconciliationComplete", () => opsApi.reconcile())}
          className="inline-flex items-center gap-1 rounded-lg border border-amber-500/30 px-3 py-2 text-sm text-amber-200"
        >
          <Wrench className="h-3.5 w-3.5" /> {t("settings.operations.reconcileStuckEmails")}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={load}
          className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-300"
        >
          <Activity className="h-3.5 w-3.5" /> {t("common.refresh")}
        </button>
      </div>
      <p className="text-[11px] text-zinc-500">
        {t("settings.operations.recoveryNote")}
      </p>
    </SectionCard>
  );
}

function Stat({ label, value, bad, testid }) {
  return (
    <div className="rounded-lg border border-white/10 bg-zinc-900/40 p-3" data-testid={testid}>
      <p className="text-[10px] uppercase tracking-wide text-zinc-500">{label}</p>
      <p className={`mt-1 font-medium ${bad ? "text-rose-300" : "text-zinc-100"}`}>{value}</p>
    </div>
  );
}
