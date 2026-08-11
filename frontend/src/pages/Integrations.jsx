import PageIntro from "@/components/PageIntro";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Loader2, Plug, Link2, Unplug, RefreshCw, HeartPulse, Shield, CheckCircle2, XCircle, AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { useLocale } from "@/context/LocaleContext";
import { integrationsApi } from "@/lib/api";
import { formatDateTime } from "@/i18n/format";
import HelpTip from "@/components/HelpTip";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const statusBadge = (status) => {
  if (status === "connected") return "bg-emerald-500/15 text-emerald-300";
  if (status === "error") return "bg-rose-500/15 text-rose-300";
  if (status === "expired") return "bg-amber-500/15 text-amber-300";
  return "bg-zinc-500/15 text-zinc-400";
};

const healthIcon = (h) => {
  if (h === "healthy") return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />;
  if (h === "error") return <XCircle className="h-3.5 w-3.5 text-rose-400" />;
  if (h === "degraded") return <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />;
  return <HeartPulse className="h-3.5 w-3.5 text-zinc-500" />;
};

export default function Integrations() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const { user } = useAuth();
  const canManage = user?.role === "owner" || user?.role === "admin";
  const [data, setData] = useState({ items: [], catalog: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(null);
  const [connectTarget, setConnectTarget] = useState(null);
  const [webhookForm, setWebhookForm] = useState({ webhookUrl: "", channel: "", displayName: "" });
  const [confirm, setConfirm] = useState(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const res = await integrationsApi.list();
      setData(res);
    } catch (e) {
      setError(e.message || t("integrations.loadError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    load();
    const params = new URLSearchParams(window.location.search);
    if (params.get("connected")) {
      toast.success(t("integrations.toasts.connectedProvider", { provider: params.get("connected") }));
      window.history.replaceState({}, "", "/integrations");
    } else if (params.get("error")) {
      toast.error(t("integrations.toasts.connectionFailed", { error: params.get("error") }));
      window.history.replaceState({}, "", "/integrations");
    }
  }, [load, t]);

  const byProvider = Object.fromEntries((data.items || []).map((i) => [i.provider, i]));

  const startConnect = async (providerMeta) => {
    if (!canManage) {
      toast.error(t("integrations.toasts.adminOnly"));
      return;
    }
    const needsWebhook = ["discord", "zapier", "webhook"].includes(providerMeta.id)
      || (providerMeta.id === "slack" && !providerMeta.oauthReady);

    if (needsWebhook || (providerMeta.authType === "webhook")) {
      setWebhookForm({ webhookUrl: "", channel: "", displayName: providerMeta.name });
      setConnectTarget(providerMeta);
      return;
    }

    // OAuth
    setBusy(providerMeta.id);
    try {
      const res = await integrationsApi.connect({ provider: providerMeta.id, useOauth: true });
      if (res.authUrl) {
        window.location.href = res.authUrl;
        return;
      }
      toast.success(t("integrations.toasts.connected"));
      await load();
    } catch (e) {
      // Slack without OAuth — fall back to webhook dialog
      if (providerMeta.id === "slack") {
        setWebhookForm({ webhookUrl: "", channel: "", displayName: "Slack" });
        setConnectTarget(providerMeta);
      } else {
        toast.error(e.message);
      }
    } finally {
      setBusy(null);
    }
  };

  const submitWebhook = async () => {
    if (!connectTarget) return;
    if (!webhookForm.webhookUrl.trim()) {
      toast.error(t("integrations.toasts.webhookRequired"));
      return;
    }
    setBusy(connectTarget.id);
    try {
      await integrationsApi.connect({
        provider: connectTarget.id,
        webhookUrl: webhookForm.webhookUrl.trim(),
        channel: webhookForm.channel || undefined,
        displayName: webhookForm.displayName || undefined,
        useOauth: false,
      });
      toast.success(t("integrations.toasts.connectedProvider", { provider: connectTarget.name }));
      setConnectTarget(null);
      await load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(null);
    }
  };

  const run = async (action, provider) => {
    setBusy(provider);
    try {
      if (action === "disconnect") {
        await integrationsApi.disconnect({ provider });
        toast.success(t("integrations.toasts.disconnected"));
      } else if (action === "refresh") {
        await integrationsApi.refresh({ provider });
        toast.success(t("integrations.toasts.tokensRefreshed"));
      } else if (action === "health") {
        const res = await integrationsApi.health({ provider });
        toast.success(res.message || (res.ok ? t("integrations.health.healthy") : t("integrations.health.unhealthy")));
      } else if (action === "reconnect") {
        const meta = (data.catalog || []).find((c) => c.id === provider);
        if (meta) await startConnect(meta);
        return;
      }
      await load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(null);
      setConfirm(null);
    }
  };

  return (
    <div className="space-y-5" data-testid="integrations-page">
      <PageIntro title={t("pages.integrations.title")} description={t("pages.integrations.description")} />

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">{t("integrations.title")}</h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-zinc-400">
            {t("integrations.description")}
            <HelpTip testid="integrations-help" text={t("integrations.help")} />
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : error ? (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-6 text-sm text-rose-200" data-testid="integrations-error">{error}</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="integrations-grid">
          {(data.catalog || []).map((meta) => {
            const row = byProvider[meta.id] || { status: "disconnected" };
            const connected = row.status === "connected" || row.status === "error";
            return (
              <div
                key={meta.id}
                data-testid={`integration-card-${meta.id}`}
                className="flex flex-col rounded-xl border border-white/10 bg-zinc-950 p-5"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600/15 text-brand-400">
                      <Plug className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-zinc-100">{meta.name}</p>
                      <p className="text-xs text-zinc-500">{meta.description}</p>
                    </div>
                  </div>
                  <span className={`rounded-md px-2 py-0.5 text-[11px] capitalize ${statusBadge(row.status)}`}>
                    {t(`integrations.status.${row.status || "disconnected"}`)}
                  </span>
                </div>

                <div className="mt-4 space-y-1.5 text-xs text-zinc-400">
                  <p className="flex items-center gap-1.5">
                    <Shield className="h-3.5 w-3.5 text-zinc-500" />
                    {t("integrations.permissions")}: {(row.permissions || []).length ? (row.permissions || []).join(", ") : (meta.permissions || []).slice(0, 3).join(", ") || "—"}
                  </p>
                  <p>{t("integrations.lastSync")}: {formatDateTime(row.lastSyncAt, locale)}</p>
                  <p className="flex items-center gap-1.5">
                    {healthIcon(row.healthStatus)}
                    {t("integrations.health.label")}: {row.healthMessage || (row.healthStatus ? t(`integrations.health.${row.healthStatus}`, { defaultValue: row.healthStatus }) : "—")}
                  </p>
                  {row.accountEmail && <p>{t("integrations.account")}: {row.accountEmail}</p>}
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {!connected ? (
                    <button
                      type="button"
                      disabled={!canManage || busy === meta.id}
                      onClick={() => startConnect(meta)}
                      data-testid={`integration-connect-${meta.id}`}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-500 disabled:opacity-50"
                    >
                      {busy === meta.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Link2 className="h-3.5 w-3.5" />}
                      {t("integrations.actions.connect")}
                    </button>
                  ) : (
                    <>
                      <button
                        type="button"
                        disabled={busy === meta.id}
                        onClick={() => run("health", meta.id)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-900"
                        data-testid={`integration-health-${meta.id}`}
                      >
                        <HeartPulse className="h-3.5 w-3.5" /> {t("integrations.actions.health")}
                      </button>
                      {["google", "microsoft", "slack"].includes(meta.id) && canManage && (
                        <button
                          type="button"
                          disabled={busy === meta.id}
                          onClick={() => run("refresh", meta.id)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-900"
                          data-testid={`integration-refresh-${meta.id}`}
                        >
                          <RefreshCw className="h-3.5 w-3.5" /> {t("common.refresh")}
                        </button>
                      )}
                      {canManage && (
                        <button
                          type="button"
                          disabled={busy === meta.id}
                          onClick={() => setConfirm({ action: "reconnect", provider: meta.id })}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-900"
                          data-testid={`integration-reconnect-${meta.id}`}
                        >
                          {t("integrations.actions.reconnect")}
                        </button>
                      )}
                      {canManage && (
                        <button
                          type="button"
                          disabled={busy === meta.id}
                          onClick={() => setConfirm({ action: "disconnect", provider: meta.id })}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 px-3 py-1.5 text-xs text-rose-300 hover:bg-rose-500/10"
                          data-testid={`integration-disconnect-${meta.id}`}
                        >
                          <Unplug className="h-3.5 w-3.5" /> {t("integrations.actions.disconnect")}
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Dialog open={!!connectTarget} onOpenChange={(o) => !o && setConnectTarget(null)}>
        <DialogContent className="max-w-md border-white/10 bg-zinc-950 text-zinc-100" data-testid="integration-webhook-dialog">
          <DialogHeader>
            <DialogTitle>{t("integrations.dialog.title", { provider: connectTarget?.name })}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            <p className="text-xs text-zinc-400">{t("integrations.dialog.description")}</p>
            <label className="block text-xs text-zinc-400">{t("integrations.dialog.webhookUrl")}
              <input
                aria-label={t("integrations.dialog.webhookUrl")}
                data-testid="integration-webhook-url"
                className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm"
                value={webhookForm.webhookUrl}
                onChange={(e) => setWebhookForm((s) => ({ ...s, webhookUrl: e.target.value }))}
                placeholder="https://…"
              />
            </label>
            {connectTarget?.id === "slack" && (
              <label className="block text-xs text-zinc-400">{t("integrations.dialog.defaultChannel")}
                <input
                  aria-label={t("integrations.dialog.channel")}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm"
                  value={webhookForm.channel}
                  onChange={(e) => setWebhookForm((s) => ({ ...s, channel: e.target.value }))}
                  placeholder="#general"
                />
              </label>
            )}
          </div>
          <DialogFooter>
            <button
              type="button"
              disabled={busy === connectTarget?.id}
              onClick={submitWebhook}
              data-testid="integration-webhook-save"
              className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-500"
            >
              {busy === connectTarget?.id ? <Loader2 className="h-4 w-4 animate-spin" /> : t("integrations.actions.connect")}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!confirm} onOpenChange={(o) => !o && setConfirm(null)}>
        <AlertDialogContent className="border-white/10 bg-zinc-950 text-zinc-100">
          <AlertDialogHeader>
            <AlertDialogTitle>{t("integrations.confirm.title", { action: t(`integrations.actions.${confirm?.action}`, { defaultValue: confirm?.action }) })}</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">
              {confirm?.action === "disconnect"
                ? t("integrations.confirm.disconnect")
                : t("integrations.confirm.reconnect")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-white/10 bg-transparent">{t("common.back")}</AlertDialogCancel>
            <AlertDialogAction
              className="bg-brand-600 hover:bg-brand-500"
              onClick={() => confirm && run(confirm.action, confirm.provider)}
            >
              {t("integrations.confirm.action")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
