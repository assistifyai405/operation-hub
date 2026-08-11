import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import { emailsApi, settingsApi } from "@/lib/api";
import { localizeApiError } from "@/i18n/errors";
import { SectionCard, TextField, TextArea, ToggleRow, SaveButton } from "@/components/settings/fields";

export function EmailSettingsSection({ data, reload }) {
  const { t } = useTranslation();
  const email = data?.email || {};
  const [f, setF] = useState({ ...email });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));

  useEffect(() => {
    setF({ ...(data?.email || {}) });
  }, [data]);

  useEffect(() => {
    emailsApi.status().then(setStatus).catch(() => setStatus(null));
  }, [data]);

  const save = async () => {
    setSaving(true);
    try {
      await settingsApi.updateEmail({
        ...f,
        dailySendingLimit: Number(f.dailySendingLimit) || 50,
      });
      toast.success(t("settings.email.saved"));
      reload();
    } catch (e) {
      toast.error(localizeApiError(t, e));
    } finally {
      setSaving(false);
    }
  };

  if (!data) {
    return <div className="flex justify-center py-16 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>;
  }

  return (
    <SectionCard
      title={t("settings.email.title")}
      description={t("settings.email.description")}
      testid="settings-email"
    >
      {status && (
        <div className="rounded-lg border border-white/10 bg-zinc-900/50 px-3 py-2 text-xs text-zinc-400" data-testid="settings-email-status">
          {t("settings.email.globalSending")}: {t(`settings.operations.statuses.${status.globalSendingEnabled ? "on" : "off"}`)}
          {" · "}{t("settings.email.provider")}: {status.provider}{status.providerConfigured ? "" : ` (${t("settings.email.notConfigured")})`}
          {" · "}{t("settings.email.today")}: {status.sentToday}/{status.dailyLimit}
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TextField label={t("settings.email.senderName")} value={f.senderName || ""} onChange={set("senderName")} testid="email-sender-name" />
        <TextField label={t("settings.email.senderEmail")} value={f.senderEmail || ""} onChange={set("senderEmail")} testid="email-sender-email" />
        <TextField label={t("settings.email.replyToEmail")} value={f.replyToEmail || ""} onChange={set("replyToEmail")} testid="email-reply-to" />
        <TextField label={t("settings.email.dailySendingLimit")} type="number" value={f.dailySendingLimit ?? 50} onChange={set("dailySendingLimit")} testid="email-daily-limit" />
      </div>
      <TextArea label={t("settings.email.companySignature")} value={f.companySignature || ""} onChange={set("companySignature")} testid="email-signature" />
      <ToggleRow label={t("settings.email.enableSending")} description={t("settings.email.enableSendingDescription")} checked={!!f.sendingEnabled} onChange={set("sendingEnabled")} testid="email-sending-enabled" />
      <ToggleRow label={t("settings.email.requireApproval")} description={t("settings.email.requireApprovalDescription")} checked={f.approvalRequired !== false} onChange={set("approvalRequired")} testid="email-approval-required" />
      <ToggleRow label={t("settings.email.allowAutoSend")} description={t("settings.email.allowAutoSendDescription")} checked={!!f.autoSendFromAutomation} onChange={set("autoSendFromAutomation")} testid="email-auto-send" />
      <SaveButton onClick={save} saving={saving} testid="email-settings-save" />
    </SectionCard>
  );
}
