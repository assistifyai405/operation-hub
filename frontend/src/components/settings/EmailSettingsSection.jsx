import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { emailsApi, settingsApi } from "@/lib/api";
import { SectionCard, TextField, TextArea, ToggleRow, SaveButton } from "@/components/settings/fields";

export function EmailSettingsSection({ data, reload }) {
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
      toast.success("Email settings saved");
      reload();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (!data) {
    return <div className="flex justify-center py-16 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>;
  }

  return (
    <SectionCard
      title="Email"
      description="Organization outbound sender defaults and approval rules. Provider API keys are configured only on the server."
      testid="settings-email"
    >
      {status && (
        <div className="rounded-lg border border-white/10 bg-zinc-900/50 px-3 py-2 text-xs text-zinc-400" data-testid="settings-email-status">
          Global sending: {status.globalSendingEnabled ? "on" : "off"}
          {" · "}Provider: {status.provider}{status.providerConfigured ? "" : " (not configured)"}
          {" · "}Today: {status.sentToday}/{status.dailyLimit}
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TextField label="Sender name" value={f.senderName || ""} onChange={set("senderName")} testid="email-sender-name" />
        <TextField label="Sender email" value={f.senderEmail || ""} onChange={set("senderEmail")} testid="email-sender-email" />
        <TextField label="Reply-to email" value={f.replyToEmail || ""} onChange={set("replyToEmail")} testid="email-reply-to" />
        <TextField label="Daily sending limit" type="number" value={f.dailySendingLimit ?? 50} onChange={set("dailySendingLimit")} testid="email-daily-limit" />
      </div>
      <TextArea label="Company signature" value={f.companySignature || ""} onChange={set("companySignature")} testid="email-signature" />
      <ToggleRow label="Enable organization sending" description="Must also have EMAIL_SENDING_ENABLED=true on the server." checked={!!f.sendingEnabled} onChange={set("sendingEnabled")} testid="email-sending-enabled" />
      <ToggleRow label="Require approval before send" description="Members submit drafts; owners/admins approve." checked={f.approvalRequired !== false} onChange={set("approvalRequired")} testid="email-approval-required" />
      <ToggleRow label="Allow automation auto-send" description="Only when approval is off and the automation is explicitly auto-mode. Still respects global sending gates." checked={!!f.autoSendFromAutomation} onChange={set("autoSendFromAutomation")} testid="email-auto-send" />
      <SaveButton onClick={save} saving={saving} testid="email-settings-save" />
    </SectionCard>
  );
}
