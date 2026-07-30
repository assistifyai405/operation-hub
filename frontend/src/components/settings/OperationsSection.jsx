import { useCallback, useEffect, useState } from "react";
import { Loader2, Activity, RefreshCw, Wrench } from "lucide-react";
import { toast } from "sonner";
import { opsApi } from "@/lib/api";
import { SectionCard, SaveButton } from "@/components/settings/fields";

export function OperationsSection() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await opsApi.status());
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const run = async (label, fn) => {
    setBusy(true);
    try {
      await fn();
      toast.success(label);
      await load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (loading && !data) {
    return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-zinc-500" /></div>;
  }

  const mailboxes = data?.mailboxes || [];

  return (
    <SectionCard title="Operations" description="Backend readiness, workers, and recovery actions for owners and admins." testid="settings-operations">
      <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4" data-testid="ops-status-grid">
        <Stat label="Release" value={data?.release || "—"} />
        <Stat label="MongoDB" value={data?.mongodb?.ok ? "ok" : "down"} bad={!data?.mongodb?.ok} />
        <Stat label="Redis" value={data?.redis?.ok ? "ok" : (data?.redis?.configured ? "down" : "unset")} />
        <Stat label="Failed jobs" value={String(data?.failedJobs ?? 0)} bad={(data?.failedJobs || 0) > 0} />
        <Stat label="Stuck emails" value={String(data?.stuckEmails ?? 0)} bad={(data?.stuckEmails || 0) > 0} />
        <Stat label="Unhealthy integrations" value={String(data?.unhealthyIntegrations ?? 0)} bad={(data?.unhealthyIntegrations || 0) > 0} />
        <Stat label="Worker" value={data?.workerEnabled || data?.worker?.enabled ? "enabled" : "inline"} />
        <Stat label="Scheduler" value={data?.schedulerEnabled || data?.scheduler?.enabled ? "enabled" : "off"} />
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-zinc-400">Mailboxes</p>
        {mailboxes.length === 0 ? (
          <p className="text-xs text-zinc-500">No mailboxes connected.</p>
        ) : (
          <ul className="space-y-2">
            {mailboxes.map((m) => (
              <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-300">
                <span>{m.provider} · {m.emailAddress || m.id} · {m.syncStatus || "—"} · last {m.lastSuccessfulSyncAt || "never"}</span>
                <button
                  type="button"
                  disabled={busy}
                  data-testid={`ops-sync-${m.id}`}
                  onClick={() => run("Sync enqueued", () => opsApi.syncMailbox(m.id))}
                  className="inline-flex items-center gap-1 rounded border border-white/10 px-2 py-1 hover:bg-zinc-900"
                >
                  <RefreshCw className="h-3 w-3" /> Sync
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
          onClick={() => run("Reconciliation complete", () => opsApi.reconcile())}
          className="inline-flex items-center gap-1 rounded-lg border border-amber-500/30 px-3 py-2 text-sm text-amber-200"
        >
          <Wrench className="h-3.5 w-3.5" /> Reconcile stuck emails
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={load}
          className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-300"
        >
          <Activity className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>
      <p className="text-[11px] text-zinc-500">
        Resolve individual needs_review emails from Email Center or via API. Never retry a message that already has a provider message id without confirming delivery in Gmail/Outlook.
      </p>
    </SectionCard>
  );
}

function Stat({ label, value, bad }) {
  return (
    <div className="rounded-lg border border-white/10 bg-zinc-900/40 p-3">
      <p className="text-[10px] uppercase tracking-wide text-zinc-500">{label}</p>
      <p className={`mt-1 font-medium ${bad ? "text-rose-300" : "text-zinc-100"}`}>{value}</p>
    </div>
  );
}
