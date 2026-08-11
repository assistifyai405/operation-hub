import { useTranslation } from "react-i18next";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { MODE_META } from "./automationShared";

const Row = ({ title, desc, children, testid }) => (
  <div className="flex items-start justify-between gap-4 border-b border-white/5 py-4 last:border-0" data-testid={testid}>
    <div className="min-w-0">
      <p className="text-sm font-medium text-zinc-200">{title}</p>
      {desc && <p className="mt-0.5 text-xs text-zinc-500">{desc}</p>}
    </div>
    <div className="shrink-0">{children}</div>
  </div>
);

const TIMEZONES = ["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Europe/Amsterdam", "Asia/Kolkata", "Asia/Singapore", "Australia/Sydney"];

export function AutomationSettingsPanel({ settings, onChange }) {
  const { t } = useTranslation();
  if (!settings) return null;
  const set = (patch) => onChange(patch);
  const notif = settings.notifications || {};
  const qh = settings.quiet_hours || {};
  const prefs = settings.approval_prefs || {};

  return (
    <div className="space-y-6" data-testid="automation-settings-panel">
      <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
        <h3 className="mb-1 text-sm font-semibold text-zinc-100">{t("automations.settingsPanel.general.title")}</h3>
        <Row title={t("automations.settingsPanel.general.enable")} desc={t("automations.settingsPanel.general.enableDescription")} testid="settings-master-toggle">
          <Switch checked={!!settings.enabled} onCheckedChange={(v) => set({ enabled: v })} data-testid="settings-enabled-switch" />
        </Row>
        <Row title={t("automations.settingsPanel.general.defaultMode")} desc={t("automations.settingsPanel.general.defaultModeDescription")} testid="settings-default-mode">
          <Select value={settings.default_mode} onValueChange={(v) => set({ default_mode: v })}>
            <SelectTrigger className="h-9 w-[200px] border-white/10 bg-zinc-900 text-sm" data-testid="settings-mode-select"><SelectValue /></SelectTrigger>
            <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">
              {Object.entries(MODE_META).map(([v, m]) => <SelectItem key={v} value={v}>{t(m.labelKey)}</SelectItem>)}
            </SelectContent>
          </Select>
        </Row>
        <Row title={t("automations.settingsPanel.general.safeAutomatic")} desc={t("automations.settingsPanel.general.safeAutomaticDescription")} testid="settings-safe-auto">
          <Switch checked={!!settings.safe_internal_auto} onCheckedChange={(v) => set({ safe_internal_auto: v })} data-testid="settings-safe-auto-switch" />
        </Row>
        <Row title={t("automations.settingsPanel.general.timezone")} desc={t("automations.settingsPanel.general.timezoneDescription")} testid="settings-timezone">
          <Select value={settings.timezone} onValueChange={(v) => set({ timezone: v })}>
            <SelectTrigger className="h-9 w-[200px] border-white/10 bg-zinc-900 text-sm"><SelectValue /></SelectTrigger>
            <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">
              {TIMEZONES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
            </SelectContent>
          </Select>
        </Row>
      </section>

      <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
        <h3 className="mb-1 text-sm font-semibold text-zinc-100">{t("automations.settingsPanel.approvals.title")}</h3>
        <p className="mb-2 text-xs text-zinc-500">{t("automations.settingsPanel.approvals.description")}</p>
        <Row title={t("automations.settingsPanel.approvals.clientFacing")} desc={t("automations.settingsPanel.approvals.clientFacingDescription")}>
          <Switch checked={prefs.require_external !== false} onCheckedChange={(v) => set({ approval_prefs: { ...prefs, require_external: v } })} data-testid="settings-require-external" />
        </Row>
        <Row title={t("automations.settingsPanel.approvals.aiDocuments")} desc={t("automations.settingsPanel.approvals.aiDocumentsDescription")}>
          <Switch checked={prefs.require_generative !== false} onCheckedChange={(v) => set({ approval_prefs: { ...prefs, require_generative: v } })} data-testid="settings-require-generative" />
        </Row>
        <Row title={t("automations.settingsPanel.approvals.destructive")} desc={t("automations.settingsPanel.approvals.destructiveDescription")}>
          <Switch checked={prefs.require_destructive !== false} onCheckedChange={(v) => set({ approval_prefs: { ...prefs, require_destructive: v } })} data-testid="settings-require-destructive" />
        </Row>
      </section>

      <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
        <h3 className="mb-1 text-sm font-semibold text-zinc-100">{t("automations.settingsPanel.notifications.title")}</h3>
        <Row title={t("automations.settingsPanel.notifications.approvals")} desc={t("automations.settingsPanel.notifications.approvalsDescription")}>
          <Switch checked={!!notif.approvals} onCheckedChange={(v) => set({ notifications: { ...notif, approvals: v } })} data-testid="settings-notif-approvals" />
        </Row>
        <Row title={t("automations.settingsPanel.notifications.executions")} desc={t("automations.settingsPanel.notifications.executionsDescription")}>
          <Switch checked={!!notif.executions} onCheckedChange={(v) => set({ notifications: { ...notif, executions: v } })} data-testid="settings-notif-executions" />
        </Row>
        <Row title={t("automations.settingsPanel.notifications.email")} desc={t("automations.settingsPanel.notifications.emailDescription")}>
          <Switch checked={!!notif.email} onCheckedChange={(v) => set({ notifications: { ...notif, email: v } })} data-testid="settings-notif-email" />
        </Row>
      </section>

      <section className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
        <h3 className="mb-1 text-sm font-semibold text-zinc-100">{t("automations.settingsPanel.quietHours.title")}</h3>
        <Row title={t("automations.settingsPanel.quietHours.pause")} desc={t("automations.settingsPanel.quietHours.pauseDescription")}>
          <Switch checked={!!qh.enabled} onCheckedChange={(v) => set({ quiet_hours: { ...qh, enabled: v } })} data-testid="settings-quiet-toggle" />
        </Row>
        {qh.enabled && (
          <Row title={t("automations.settingsPanel.quietHours.window")} desc={t("automations.settingsPanel.quietHours.windowDescription")}>
            <div className="flex items-center gap-2">
              <Input type="time" value={qh.start || "22:00"} onChange={(e) => set({ quiet_hours: { ...qh, start: e.target.value } })} className="h-9 w-28 border-white/10 bg-zinc-900 text-sm" data-testid="settings-quiet-start" />
              <span className="text-xs text-zinc-500">{t("automations.settingsPanel.quietHours.to")}</span>
              <Input type="time" value={qh.end || "07:00"} onChange={(e) => set({ quiet_hours: { ...qh, end: e.target.value } })} className="h-9 w-28 border-white/10 bg-zinc-900 text-sm" data-testid="settings-quiet-end" />
            </div>
          </Row>
        )}
      </section>
    </div>
  );
}
