import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Loader2, KeyRound, Plug, ShieldCheck, Monitor, LogOut, Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/context/AuthContext";
import { authApi, settingsApi } from "@/lib/api";
import { BILLING_ENABLED } from "@/lib/config";
import { localizeApiError } from "@/i18n/errors";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  SectionCard, TextField, TextArea, SelectField, ColorField, ToggleRow, ImageUpload, SaveButton, inputCls,
} from "@/components/settings/fields";

const TIMEZONES = ["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Europe/Amsterdam", "Europe/Berlin", "Asia/Kolkata", "Asia/Singapore", "Australia/Sydney"];
const CURRENCIES = ["USD", "EUR", "GBP", "INR", "AUD", "CAD", "SGD"];
const TONES = ["Professional", "Formal", "Friendly", "Persuasive", "Concise"];
const fmtDate = (d, locale) => d ? new Date(d).toLocaleString(locale, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

// ---------------- General (user profile) ----------------
export function GeneralSection() {
  const { t } = useTranslation();
  const { user, setUser } = useAuth();
  const [f, setF] = useState({ firstName: user.firstName || "", lastName: user.lastName || "", avatar: user.avatar || "", language: user.language || "en", timezone: user.timezone || "UTC" });
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const initials = `${(f.firstName || user.email)[0] || ""}${(f.lastName || "")[0] || ""}`.toUpperCase();
  const save = async () => {
    setSaving(true);
    try { const u = await authApi.updateProfile(f); setUser(u); toast.success(t("settings.general.saved")); }
    catch (e) { toast.error(localizeApiError(t, e)); } finally { setSaving(false); }
  };
  return (
    <SectionCard title={t("settings.general.title")} description={t("settings.general.description")} testid="settings-general">
      <div className="flex items-center gap-4">
        <Avatar className="h-16 w-16 border border-white/10"><AvatarImage src={f.avatar} /><AvatarFallback className="bg-brand-600/20 text-brand-300">{initials}</AvatarFallback></Avatar>
        <div className="flex-1"><TextField label={t("settings.general.avatarUrl")} value={f.avatar} onChange={set("avatar")} placeholder="https://…" testid="general-avatar" /></div>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TextField label={t("settings.general.firstName")} value={f.firstName} onChange={set("firstName")} testid="general-firstname" />
        <TextField label={t("settings.general.lastName")} value={f.lastName} onChange={set("lastName")} testid="general-lastname" />
        <TextField label={t("settings.general.email")} value={user.email} onChange={() => {}} disabled testid="general-email" />
        <SelectField label={t("settings.general.timezone")} value={f.timezone} onChange={set("timezone")} options={TIMEZONES} testid="general-timezone" />
        <p className="text-xs text-zinc-500" data-testid="general-language-hint">
          {t("settings.general.languageHint")}
        </p>
      </div>
      <SaveButton onClick={save} saving={saving} testid="general-save" />
    </SectionCard>
  );
}

// ---------------- Organization ----------------
export function OrganizationSection({ data, reload }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ ...data.organization });
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const save = async () => {
    setSaving(true);
    try { await settingsApi.updateOrganization({ ...f, defaultVat: Number(f.defaultVat) || 0 }); toast.success(t("settings.organization.saved")); reload(); }
    catch (e) { toast.error(localizeApiError(t, e)); } finally { setSaving(false); }
  };
  return (
    <SectionCard title={t("settings.organization.title")} description={t("settings.organization.description")} testid="settings-organization">
      <ImageUpload label={t("settings.organization.logo")} value={f.logo} onChange={set("logo")} testid="org-logo-upload" hint={t("settings.organization.logoHint")} />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TextField label={t("settings.organization.name")} value={f.name} onChange={set("name")} testid="org-name" />
        <TextField label={t("settings.organization.website")} value={f.website} onChange={set("website")} placeholder="https://…" testid="org-website" />
        <TextField label={t("settings.organization.businessEmail")} value={f.businessEmail} onChange={set("businessEmail")} testid="org-email" />
        <TextField label={t("settings.organization.phone")} value={f.phone} onChange={set("phone")} testid="org-phone" />
        <TextField label={t("settings.organization.vatNumber")} value={f.vatNumber} onChange={set("vatNumber")} testid="org-vat" />
        <TextField label={t("settings.organization.kvkNumber")} value={f.kvkNumber} onChange={set("kvkNumber")} testid="org-kvk" />
        <SelectField label={t("settings.organization.defaultCurrency")} value={f.defaultCurrency} onChange={set("defaultCurrency")} options={CURRENCIES} testid="org-currency" />
        <TextField label={t("settings.organization.defaultVat")} type="number" value={f.defaultVat} onChange={set("defaultVat")} testid="org-defaultvat" />
      </div>
      <TextArea label={t("settings.organization.address")} value={f.address} onChange={set("address")} testid="org-address" />
      <SaveButton onClick={save} saving={saving} testid="org-save" />
    </SectionCard>
  );
}

// ---------------- Branding ----------------
export function BrandingSection({ data }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ ...data.branding });
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const save = async () => {
    setSaving(true);
    try { await settingsApi.updateBranding(f); toast.success(t("settings.branding.saved")); }
    catch (e) { toast.error(localizeApiError(t, e)); } finally { setSaving(false); }
  };
  return (
    <SectionCard title={t("settings.branding.title")} description={t("settings.branding.description")} testid="settings-branding">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ColorField label={t("settings.branding.primaryColor")} value={f.primaryColor} onChange={set("primaryColor")} testid="brand-primary" />
        <ColorField label={t("settings.branding.secondaryColor")} value={f.secondaryColor} onChange={set("secondaryColor")} testid="brand-secondary" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ImageUpload label={t("settings.branding.brandLogo")} value={f.logo} onChange={set("logo")} testid="brand-logo-upload" />
        <ImageUpload label={t("settings.branding.pdfLogo")} value={f.pdfLogo} onChange={set("pdfLogo")} testid="brand-pdflogo-upload" />
      </div>
      <TextArea label={t("settings.branding.proposalFooter")} value={f.proposalFooter} onChange={set("proposalFooter")} testid="brand-proposal-footer" />
      <TextArea label={t("settings.branding.contractFooter")} value={f.contractFooter} onChange={set("contractFooter")} testid="brand-contract-footer" />
      <TextArea label={t("settings.branding.invoiceFooter")} value={f.invoiceFooter} onChange={set("invoiceFooter")} testid="brand-invoice-footer" />
      <SaveButton onClick={save} saving={saving} testid="brand-save" />
    </SectionCard>
  );
}

// ---------------- AI Settings ----------------
export function AISection({ data }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ ...data.ai });
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const save = async () => {
    setSaving(true);
    try { await settingsApi.updateAI({ ...f, temperature: Number(f.temperature) }); toast.success(t("settings.ai.saved")); }
    catch (e) { toast.error(localizeApiError(t, e)); } finally { setSaving(false); }
  };
  const toneOptions = TONES.map((tone) => ({
    value: tone,
    label: t(`settings.ai.tones.${tone.toLowerCase()}`),
  }));
  return (
    <SectionCard title={t("settings.ai.title")} description={t("settings.ai.description")} testid="settings-ai">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <SelectField label={t("settings.ai.defaultProvider")} value={f.provider} onChange={set("provider")} options={[{ value: "openai", label: "OpenAI (GPT)" }, { value: "anthropic", label: "Anthropic (Claude)" }, { value: "gemini", label: "Google (Gemini)" }]} testid="ai-provider" hint={t("settings.ai.providerHint")} />
        <SelectField label={t("settings.ai.proposalTone")} value={f.proposalTone} onChange={set("proposalTone")} options={toneOptions} testid="ai-proposal-tone" />
        <SelectField label={t("settings.ai.contractTone")} value={f.contractTone} onChange={set("contractTone")} options={toneOptions} testid="ai-contract-tone" />
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("settings.ai.temperature")} ({Number(f.temperature).toFixed(1)})</label>
          <input type="range" min="0" max="1" step="0.1" value={f.temperature} onChange={(e) => set("temperature")(e.target.value)} data-testid="ai-temperature" className="w-full accent-brand-600" />
        </div>
      </div>
      <TextArea label={t("settings.ai.invoiceNotes")} value={f.invoiceNotes} onChange={set("invoiceNotes")} placeholder={t("settings.ai.invoiceNotesPlaceholder")} testid="ai-invoice-notes" />
      <SaveButton onClick={save} saving={saving} testid="ai-save" />
    </SectionCard>
  );
}

// ---------------- Documents ----------------
export function DocumentsSection({ data }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ ...data.documents });
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const save = async () => {
    setSaving(true);
    try { await settingsApi.updateDocuments({ ...f, numberingStart: Number(f.numberingStart) || 1 }); toast.success(t("settings.documents.saved")); }
    catch (e) { toast.error(localizeApiError(t, e)); } finally { setSaving(false); }
  };
  return (
    <SectionCard title={t("settings.documents.title")} description={t("settings.documents.description")} testid="settings-documents">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <TextField label={t("settings.documents.proposalPrefix")} value={f.proposalPrefix} onChange={set("proposalPrefix")} testid="doc-proposal-prefix" />
        <TextField label={t("settings.documents.contractPrefix")} value={f.contractPrefix} onChange={set("contractPrefix")} testid="doc-contract-prefix" />
        <TextField label={t("settings.documents.invoicePrefix")} value={f.invoicePrefix} onChange={set("invoicePrefix")} testid="doc-invoice-prefix" hint={t("settings.documents.invoicePrefixHint")} />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <TextField label={t("settings.documents.numberingStart")} type="number" value={f.numberingStart} onChange={set("numberingStart")} testid="doc-numbering-start" />
        <SelectField label={t("settings.documents.pdfPageSize")} value={f.pdfPageSize} onChange={set("pdfPageSize")} options={["A4", "Letter", "Legal"]} testid="doc-pdf-size" />
        <ColorField label={t("settings.documents.pdfAccentColor")} value={f.pdfAccentColor} onChange={set("pdfAccentColor")} testid="doc-pdf-accent" />
      </div>
      <SaveButton onClick={save} saving={saving} testid="doc-save" />
    </SectionCard>
  );
}

// ---------------- Notifications ----------------
export function NotificationsSection({ data }) {
  const { t } = useTranslation();
  const [f, setF] = useState({ ...data.notifications });
  const set = async (k, v) => {
    const next = { ...f, [k]: v };
    setF(next);
    try { await settingsApi.updateNotifications({ [k]: v }); } catch (e) { toast.error(localizeApiError(t, e)); }
  };
  const rows = [
    "emailNotifications",
    "productUpdates",
    "securityAlerts",
    "billingAlerts",
    "taskReminders",
    "weeklyDigest",
    "aiAlerts",
  ];
  return (
    <SectionCard title={t("settings.notifications.title")} description={t("settings.notifications.description")} testid="settings-notifications">
      <div>{rows.map((k) => <ToggleRow key={k} label={t(`settings.notifications.rows.${k}.label`)} description={t(`settings.notifications.rows.${k}.description`)} checked={Boolean(f[k])} onChange={(v) => set(k, v)} testid={`notif-${k}`} />)}</div>
    </SectionCard>
  );
}

// ---------------- Security ----------------
export function SecuritySection() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [pw, setPw] = useState({ currentPassword: "", newPassword: "", confirm: "" });
  const [saving, setSaving] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [logins, setLogins] = useState([]);
  const setP = (k) => (e) => setPw((p) => ({ ...p, [k]: e.target.value }));

  const load = () => {
    authApi.sessions().then(setSessions).catch(() => {});
    settingsApi.recentLogins().then(setLogins).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const change = async () => {
    if (pw.newPassword.length < 8) return toast.error(t("settings.security.passwordMin"));
    if (pw.newPassword !== pw.confirm) return toast.error(t("settings.security.passwordMismatch"));
    setSaving(true);
    try { await authApi.changePassword({ currentPassword: pw.currentPassword, newPassword: pw.newPassword }); setPw({ currentPassword: "", newPassword: "", confirm: "" }); toast.success(t("settings.security.passwordChanged")); }
    catch (e) { toast.error(localizeApiError(t, e)); } finally { setSaving(false); }
  };
  const logoutAll = async () => {
    try { await settingsApi.logoutAll(); toast.success(t("settings.security.signedOutAll")); await logout(); navigate("/login"); }
    catch (e) { toast.error(localizeApiError(t, e)); }
  };

  return (
    <div className="space-y-6">
      <SectionCard title={t("settings.security.changePassword")} description={t("settings.security.passwordDescription")} testid="settings-security">
        <div className="grid grid-cols-1 gap-4 sm:max-w-md">
          <div><label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("settings.security.currentPassword")}</label><input type="password" value={pw.currentPassword} onChange={setP("currentPassword")} data-testid="current-password" className={inputCls} /></div>
          <div><label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("settings.security.newPassword")}</label><input type="password" value={pw.newPassword} onChange={setP("newPassword")} data-testid="new-password" className={inputCls} /></div>
          <div><label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("settings.security.confirmPassword")}</label><input type="password" value={pw.confirm} onChange={setP("confirm")} data-testid="confirm-password" className={inputCls} /></div>
        </div>
        <SaveButton onClick={change} saving={saving} testid="change-password-btn" label={t("settings.security.updatePassword")} />
      </SectionCard>

      <SectionCard title={t("settings.security.activeSessions")} description={t("settings.security.activeSessionsDescription")} testid="settings-sessions" footer={
        <button onClick={logoutAll} data-testid="logout-all-btn" className="mt-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-300 transition-all hover:bg-red-500/20">
          <LogOut className="h-4 w-4" /> {t("settings.security.logoutAll")}
        </button>
      }>
        <div className="space-y-2" data-testid="active-sessions-list">
          {sessions.length === 0 ? <p className="text-sm text-zinc-500">{t("settings.security.noActiveSessions")}</p> : sessions.map((s) => (
            <div key={s.id} className="flex items-center gap-3 rounded-lg border border-white/5 bg-zinc-900/50 p-3">
              <Monitor className="h-4 w-4 text-brand-400" />
              <div className="min-w-0 flex-1"><p className="truncate text-sm text-zinc-200">{s.userAgent || t("settings.security.unknownDevice")}</p><p className="text-xs text-zinc-500">{s.ip} · {t("settings.security.lastActive", { date: fmtDate(s.lastUsedAt, i18n.resolvedLanguage || i18n.language) })}</p></div>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title={t("settings.security.recentLogins")} description={t("settings.security.recentLoginsDescription")} testid="settings-recent-logins">
        <div className="space-y-2">
          {logins.length === 0 ? <p className="text-sm text-zinc-500">{t("settings.security.noLoginHistory")}</p> : logins.map((s) => (
            <div key={s.id} className="flex items-center gap-3 border-b border-white/5 py-2 text-sm last:border-0">
              <ShieldCheck className={`h-4 w-4 ${s.revoked ? "text-zinc-600" : "text-emerald-400"}`} />
              <span className="text-zinc-300">{s.ip}</span>
              <span className="ml-auto text-xs text-zinc-500">{fmtDate(s.createdAt, i18n.resolvedLanguage || i18n.language)}</span>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

// ---------------- API Keys (placeholder) ----------------
export function ApiKeysSection() {
  const { t } = useTranslation();
  return (
    <SectionCard title={t("settings.apiKeys.title")} description={t("settings.apiKeys.description")} testid="settings-apikeys">
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-zinc-900/40 py-14 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600/15 text-brand-400"><KeyRound className="h-6 w-6" /></div>
        <p className="mt-4 text-sm font-semibold text-zinc-200">{t("settings.apiKeys.comingSoon")}</p>
        <p className="mt-1 max-w-sm text-sm text-zinc-500">{t("settings.apiKeys.hint")}</p>
        <button disabled className="mt-5 cursor-not-allowed rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-500" data-testid="apikeys-create-btn">{t("settings.apiKeys.create")}</button>
      </div>
    </SectionCard>
  );
}

// ---------------- Integrations (links to hub) ----------------
export function IntegrationsSection() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <SectionCard title={t("settings.integrations.title")} description={t("settings.integrations.description")} testid="settings-integrations">
      <p className="text-sm text-zinc-400">{t("settings.integrations.hint")}</p>
      <button
        type="button"
        data-testid="settings-open-integrations"
        onClick={() => navigate("/integrations")}
        className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-500"
      >
        <Plug className="h-4 w-4" /> {t("settings.integrations.open")}
      </button>
    </SectionCard>
  );
}

// ---------------- Billing (placeholder) ----------------
export function BillingSection() {
  const { t } = useTranslation();
  const [b, setB] = useState(null);
  useEffect(() => { settingsApi.billing().then(setB).catch(() => {}); }, []);
  if (!b) return <div className="flex items-center justify-center py-16 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>;
  const usage = b.usage || {};
  const limits = b.limits || {};
  const usageRows = [
    ["projects", usage.projects ?? 0, limits.projects],
    ["documents", usage.documents ?? 0, limits.documents],
    ["proposals", usage.proposals ?? 0, null], ["contracts", usage.contracts ?? 0, null], ["invoices", usage.invoices ?? 0, null],
  ];
  return (
    <SectionCard title={t("settings.billing.title")} description={t("settings.billing.description")} testid="settings-billing">
      {BILLING_ENABLED && (b.status === "active" || b.subscriptionStatus === "active") ? (
        <div className="rounded-xl border border-brand-500/25 bg-gradient-to-br from-brand-600/15 to-transparent p-5">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-brand-400" /><p className="text-sm font-semibold text-brand-300">{t("settings.billing.plan", { plan: b.plan })}</p><span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-400">{t("settings.billing.active")}</span></div>
              <p className="mt-2 text-3xl font-bold text-zinc-50">${b.price}<span className="text-sm font-normal text-zinc-500">/{t(`settings.billing.intervals.${b.interval}`, { defaultValue: b.interval })}</span></p>
              <p className="mt-1 text-xs text-zinc-400">{t("settings.billing.renewsAndSeats", { date: b.renews_on, used: b.seats.used, included: b.seats.included })}</p>
            </div>
            <button data-testid="upgrade-btn" onClick={() => toast.info(t("settings.billing.managePlanInfo"))} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-500 glow-brand">{t("settings.billing.managePlan")}</button>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-white/10 bg-zinc-900/60 p-6 text-center" data-testid="billing-coming-soon">
          <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-800 text-zinc-400"><Sparkles className="h-5 w-5" /></div>
          <p className="mt-3 text-sm font-semibold text-zinc-100">{t("settings.billing.notAvailable")}</p>
          <p className="mx-auto mt-1 max-w-sm text-xs text-zinc-500">{t("settings.billing.notAvailableHint")}</p>
          {b.aiUsage && (
            <p className="mt-3 text-xs text-zinc-400" data-testid="billing-ai-usage">
              {t("settings.billing.aiUsage", { used: b.aiUsage.used, limit: b.aiUsage.limit != null ? ` / ${b.aiUsage.limit}` : "" })}
            </p>
          )}
        </div>
      )}
      <div>
        <p className="mb-3 text-sm font-semibold text-zinc-100">{t("settings.billing.usageThisPeriod")}</p>
        <div className="space-y-3" data-testid="billing-usage">
          {usageRows.map(([key, used, limit]) => (
            <div key={key}>
              <div className="mb-1 flex items-center justify-between text-xs"><span className="text-zinc-400">{t(`settings.billing.usage.${key}`)}</span><span className="text-zinc-300">{used}{limit && BILLING_ENABLED ? ` / ${limit}` : ""}</span></div>
              {limit && BILLING_ENABLED && <div className="h-2 overflow-hidden rounded-full bg-zinc-800"><div className="h-full rounded-full bg-brand-500" style={{ width: `${Math.min(100, (used / limit) * 100)}%` }} /></div>}
            </div>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
