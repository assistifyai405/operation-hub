import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Loader2, KeyRound, Plug, CreditCard, ShieldCheck, Monitor, LogOut, Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { authApi, settingsApi } from "@/lib/api";
import { BILLING_ENABLED } from "@/lib/config";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  SectionCard, TextField, TextArea, SelectField, ColorField, ToggleRow, ImageUpload, SaveButton, inputCls,
} from "@/components/settings/fields";

const TIMEZONES = ["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Europe/Amsterdam", "Europe/Berlin", "Asia/Kolkata", "Asia/Singapore", "Australia/Sydney"];
const LANGUAGES = [{ value: "en", label: "English" }, { value: "es", label: "Español" }, { value: "fr", label: "Français" }, { value: "de", label: "Deutsch" }, { value: "pt", label: "Português" }, { value: "hi", label: "हिन्दी" }, { value: "nl", label: "Nederlands" }];
const CURRENCIES = ["USD", "EUR", "GBP", "INR", "AUD", "CAD", "SGD"];
const TONES = ["Professional", "Formal", "Friendly", "Persuasive", "Concise"];
const fmtDate = (d) => d ? new Date(d).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

// ---------------- General (user profile) ----------------
export function GeneralSection() {
  const { user, setUser } = useAuth();
  const [f, setF] = useState({ firstName: user.firstName || "", lastName: user.lastName || "", avatar: user.avatar || "", language: user.language || "en", timezone: user.timezone || "UTC" });
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const initials = `${(f.firstName || user.email)[0] || ""}${(f.lastName || "")[0] || ""}`.toUpperCase();
  const save = async () => {
    setSaving(true);
    try { const u = await authApi.updateProfile(f); setUser(u); toast.success("Profile saved"); }
    catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };
  return (
    <SectionCard title="General" description="Your personal profile and preferences." testid="settings-general">
      <div className="flex items-center gap-4">
        <Avatar className="h-16 w-16 border border-white/10"><AvatarImage src={f.avatar} /><AvatarFallback className="bg-violet-600/20 text-violet-300">{initials}</AvatarFallback></Avatar>
        <div className="flex-1"><TextField label="Avatar URL" value={f.avatar} onChange={set("avatar")} placeholder="https://…" testid="general-avatar" /></div>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TextField label="First name" value={f.firstName} onChange={set("firstName")} testid="general-firstname" />
        <TextField label="Last name" value={f.lastName} onChange={set("lastName")} testid="general-lastname" />
        <TextField label="Email" value={user.email} onChange={() => {}} disabled testid="general-email" />
        <SelectField label="Language" value={f.language} onChange={set("language")} options={LANGUAGES} testid="general-language" />
        <SelectField label="Timezone" value={f.timezone} onChange={set("timezone")} options={TIMEZONES} testid="general-timezone" />
      </div>
      <SaveButton onClick={save} saving={saving} testid="general-save" />
    </SectionCard>
  );
}

// ---------------- Organization ----------------
export function OrganizationSection({ data, reload }) {
  const [f, setF] = useState({ ...data.organization });
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const save = async () => {
    setSaving(true);
    try { await settingsApi.updateOrganization({ ...f, defaultVat: Number(f.defaultVat) || 0 }); toast.success("Organization saved"); reload(); }
    catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };
  return (
    <SectionCard title="Organization" description="Company details used across proposals, contracts and invoices." testid="settings-organization">
      <ImageUpload label="Organization logo" value={f.logo} onChange={set("logo")} testid="org-logo-upload" hint="PNG, JPG or SVG up to 5MB." />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TextField label="Organization name" value={f.name} onChange={set("name")} testid="org-name" />
        <TextField label="Website" value={f.website} onChange={set("website")} placeholder="https://…" testid="org-website" />
        <TextField label="Business email" value={f.businessEmail} onChange={set("businessEmail")} testid="org-email" />
        <TextField label="Phone" value={f.phone} onChange={set("phone")} testid="org-phone" />
        <TextField label="VAT number" value={f.vatNumber} onChange={set("vatNumber")} testid="org-vat" />
        <TextField label="KVK number" value={f.kvkNumber} onChange={set("kvkNumber")} testid="org-kvk" />
        <SelectField label="Default currency" value={f.defaultCurrency} onChange={set("defaultCurrency")} options={CURRENCIES} testid="org-currency" />
        <TextField label="Default VAT (%)" type="number" value={f.defaultVat} onChange={set("defaultVat")} testid="org-defaultvat" />
      </div>
      <TextArea label="Address" value={f.address} onChange={set("address")} testid="org-address" />
      <SaveButton onClick={save} saving={saving} testid="org-save" />
    </SectionCard>
  );
}

// ---------------- Branding ----------------
export function BrandingSection({ data }) {
  const [f, setF] = useState({ ...data.branding });
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const save = async () => {
    setSaving(true);
    try { await settingsApi.updateBranding(f); toast.success("Branding saved"); }
    catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };
  return (
    <SectionCard title="Branding" description="Colors, logos and document footers for a consistent brand." testid="settings-branding">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ColorField label="Primary color" value={f.primaryColor} onChange={set("primaryColor")} testid="brand-primary" />
        <ColorField label="Secondary color" value={f.secondaryColor} onChange={set("secondaryColor")} testid="brand-secondary" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ImageUpload label="Brand logo" value={f.logo} onChange={set("logo")} testid="brand-logo-upload" />
        <ImageUpload label="Default PDF logo" value={f.pdfLogo} onChange={set("pdfLogo")} testid="brand-pdflogo-upload" />
      </div>
      <TextArea label="Proposal footer" value={f.proposalFooter} onChange={set("proposalFooter")} testid="brand-proposal-footer" />
      <TextArea label="Contract footer" value={f.contractFooter} onChange={set("contractFooter")} testid="brand-contract-footer" />
      <TextArea label="Invoice footer" value={f.invoiceFooter} onChange={set("invoiceFooter")} testid="brand-invoice-footer" />
      <SaveButton onClick={save} saving={saving} testid="brand-save" />
    </SectionCard>
  );
}

// ---------------- AI Settings ----------------
export function AISection({ data }) {
  const [f, setF] = useState({ ...data.ai });
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const save = async () => {
    setSaving(true);
    try { await settingsApi.updateAI({ ...f, temperature: Number(f.temperature) }); toast.success("AI settings saved"); }
    catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };
  return (
    <SectionCard title="AI Settings" description="Defaults for AI-generated proposals, contracts and invoices." testid="settings-ai">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <SelectField label="Default AI provider" value={f.provider} onChange={set("provider")} options={[{ value: "openai", label: "OpenAI (GPT)" }, { value: "anthropic", label: "Anthropic (Claude)" }, { value: "gemini", label: "Google (Gemini)" }]} testid="ai-provider" hint="Provider routing is future-ready." />
        <SelectField label="Proposal tone" value={f.proposalTone} onChange={set("proposalTone")} options={TONES} testid="ai-proposal-tone" />
        <SelectField label="Contract tone" value={f.contractTone} onChange={set("contractTone")} options={TONES} testid="ai-contract-tone" />
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Temperature ({Number(f.temperature).toFixed(1)})</label>
          <input type="range" min="0" max="1" step="0.1" value={f.temperature} onChange={(e) => set("temperature")(e.target.value)} data-testid="ai-temperature" className="w-full accent-violet-600" />
        </div>
      </div>
      <TextArea label="Default invoice notes" value={f.invoiceNotes} onChange={set("invoiceNotes")} placeholder="e.g. Payment due within 14 days." testid="ai-invoice-notes" />
      <SaveButton onClick={save} saving={saving} testid="ai-save" />
    </SectionCard>
  );
}

// ---------------- Documents ----------------
export function DocumentsSection({ data }) {
  const [f, setF] = useState({ ...data.documents });
  const [saving, setSaving] = useState(false);
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));
  const save = async () => {
    setSaving(true);
    try { await settingsApi.updateDocuments({ ...f, numberingStart: Number(f.numberingStart) || 1 }); toast.success("Document settings saved"); }
    catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };
  return (
    <SectionCard title="Documents" description="Numbering, prefixes and PDF defaults." testid="settings-documents">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <TextField label="Proposal prefix" value={f.proposalPrefix} onChange={set("proposalPrefix")} testid="doc-proposal-prefix" />
        <TextField label="Contract prefix" value={f.contractPrefix} onChange={set("contractPrefix")} testid="doc-contract-prefix" />
        <TextField label="Invoice prefix" value={f.invoicePrefix} onChange={set("invoicePrefix")} testid="doc-invoice-prefix" hint="Used for new invoice numbers." />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <TextField label="Numbering starts at" type="number" value={f.numberingStart} onChange={set("numberingStart")} testid="doc-numbering-start" />
        <SelectField label="PDF page size" value={f.pdfPageSize} onChange={set("pdfPageSize")} options={["A4", "Letter", "Legal"]} testid="doc-pdf-size" />
        <ColorField label="PDF accent color" value={f.pdfAccentColor} onChange={set("pdfAccentColor")} testid="doc-pdf-accent" />
      </div>
      <SaveButton onClick={save} saving={saving} testid="doc-save" />
    </SectionCard>
  );
}

// ---------------- Notifications ----------------
export function NotificationsSection({ data }) {
  const [f, setF] = useState({ ...data.notifications });
  const set = async (k, v) => {
    const next = { ...f, [k]: v };
    setF(next);
    try { await settingsApi.updateNotifications({ [k]: v }); } catch (e) { toast.error(e.message); }
  };
  const rows = [
    ["emailNotifications", "Email notifications", "Receive important updates by email"],
    ["productUpdates", "Product updates", "News about new features and improvements"],
    ["securityAlerts", "Security alerts", "Sign-in and security-related notifications"],
    ["billingAlerts", "Billing alerts", "Payment and subscription notices (future)"],
    ["taskReminders", "Task reminders", "Reminders for upcoming tasks"],
    ["weeklyDigest", "Weekly digest", "A summary of your business every Monday"],
    ["aiAlerts", "AI generation alerts", "Notify when AI documents finish generating"],
  ];
  return (
    <SectionCard title="Notifications" description="Choose what you want to hear about." testid="settings-notifications">
      <div>{rows.map(([k, label, desc]) => <ToggleRow key={k} label={label} description={desc} checked={Boolean(f[k])} onChange={(v) => set(k, v)} testid={`notif-${k}`} />)}</div>
    </SectionCard>
  );
}

// ---------------- Security ----------------
export function SecuritySection() {
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
    if (pw.newPassword.length < 8) return toast.error("New password must be at least 8 characters");
    if (pw.newPassword !== pw.confirm) return toast.error("Passwords do not match");
    setSaving(true);
    try { await authApi.changePassword({ currentPassword: pw.currentPassword, newPassword: pw.newPassword }); setPw({ currentPassword: "", newPassword: "", confirm: "" }); toast.success("Password changed"); }
    catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };
  const logoutAll = async () => {
    try { await settingsApi.logoutAll(); toast.success("Signed out of all devices"); await logout(); navigate("/login"); }
    catch (e) { toast.error(e.message); }
  };

  return (
    <div className="space-y-6">
      <SectionCard title="Change password" description="Use a strong, unique password." testid="settings-security">
        <div className="grid grid-cols-1 gap-4 sm:max-w-md">
          <div><label className="mb-1.5 block text-xs font-medium text-zinc-400">Current password</label><input type="password" value={pw.currentPassword} onChange={setP("currentPassword")} data-testid="current-password" className={inputCls} /></div>
          <div><label className="mb-1.5 block text-xs font-medium text-zinc-400">New password</label><input type="password" value={pw.newPassword} onChange={setP("newPassword")} data-testid="new-password" className={inputCls} /></div>
          <div><label className="mb-1.5 block text-xs font-medium text-zinc-400">Confirm new password</label><input type="password" value={pw.confirm} onChange={setP("confirm")} data-testid="confirm-password" className={inputCls} /></div>
        </div>
        <SaveButton onClick={change} saving={saving} testid="change-password-btn" label="Update password" />
      </SectionCard>

      <SectionCard title="Active sessions" description="Devices currently signed in." testid="settings-sessions" footer={
        <button onClick={logoutAll} data-testid="logout-all-btn" className="mt-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-300 transition-all hover:bg-red-500/20">
          <LogOut className="h-4 w-4" /> Log out of all devices
        </button>
      }>
        <div className="space-y-2" data-testid="active-sessions-list">
          {sessions.length === 0 ? <p className="text-sm text-zinc-500">No active sessions.</p> : sessions.map((s) => (
            <div key={s.id} className="flex items-center gap-3 rounded-lg border border-white/5 bg-zinc-900/50 p-3">
              <Monitor className="h-4 w-4 text-violet-400" />
              <div className="min-w-0 flex-1"><p className="truncate text-sm text-zinc-200">{s.userAgent || "Unknown device"}</p><p className="text-xs text-zinc-500">{s.ip} · last active {fmtDate(s.lastUsedAt)}</p></div>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Recent logins" description="Your latest sign-in activity." testid="settings-recent-logins">
        <div className="space-y-2">
          {logins.length === 0 ? <p className="text-sm text-zinc-500">No login history.</p> : logins.map((s) => (
            <div key={s.id} className="flex items-center gap-3 border-b border-white/5 py-2 text-sm last:border-0">
              <ShieldCheck className={`h-4 w-4 ${s.revoked ? "text-zinc-600" : "text-emerald-400"}`} />
              <span className="text-zinc-300">{s.ip}</span>
              <span className="ml-auto text-xs text-zinc-500">{fmtDate(s.createdAt)}</span>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

// ---------------- API Keys (placeholder) ----------------
export function ApiKeysSection() {
  return (
    <SectionCard title="API Keys" description="Programmatic access to your Assistify workspace." testid="settings-apikeys">
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-zinc-900/40 py-14 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-600/15 text-violet-400"><KeyRound className="h-6 w-6" /></div>
        <p className="mt-4 text-sm font-semibold text-zinc-200">API access is coming soon</p>
        <p className="mt-1 max-w-sm text-sm text-zinc-500">Generate scoped API keys to integrate Assistify with your own tools and workflows.</p>
        <button disabled className="mt-5 cursor-not-allowed rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-500" data-testid="apikeys-create-btn">Create API key</button>
      </div>
    </SectionCard>
  );
}

// ---------------- Integrations (links to hub) ----------------
export function IntegrationsSection() {
  const navigate = useNavigate();
  return (
    <SectionCard title="Integrations" description="Connect Google, Microsoft, Slack, Discord, Zapier, and webhooks." testid="settings-integrations">
      <p className="text-sm text-zinc-400">Manage connections, permissions, health checks, and OAuth from the Integrations hub.</p>
      <button
        type="button"
        data-testid="settings-open-integrations"
        onClick={() => navigate("/integrations")}
        className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500"
      >
        <Plug className="h-4 w-4" /> Open Integrations
      </button>
    </SectionCard>
  );
}

// ---------------- Billing (placeholder) ----------------
export function BillingSection() {
  const [b, setB] = useState(null);
  useEffect(() => { settingsApi.billing().then(setB).catch(() => {}); }, []);
  if (!b) return <div className="flex items-center justify-center py-16 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>;
  const usage = b.usage || {};
  const limits = b.limits || {};
  const usageRows = [
    ["Projects", usage.projects ?? 0, limits.projects],
    ["Documents", usage.documents ?? 0, limits.documents],
    ["Proposals", usage.proposals ?? 0, null], ["Contracts", usage.contracts ?? 0, null], ["Invoices", usage.invoices ?? 0, null],
  ];
  return (
    <SectionCard title="Billing" description="Plans and usage." testid="settings-billing">
      {BILLING_ENABLED && (b.status === "active" || b.subscriptionStatus === "active") ? (
        <div className="rounded-xl border border-violet-500/25 bg-gradient-to-br from-violet-600/15 to-transparent p-5">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-violet-400" /><p className="text-sm font-semibold text-violet-300">{b.plan} Plan</p><span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-400">Active</span></div>
              <p className="mt-2 text-3xl font-bold text-zinc-50">${b.price}<span className="text-sm font-normal text-zinc-500">/{b.interval}</span></p>
              <p className="mt-1 text-xs text-zinc-400">Renews on {b.renews_on} · {b.seats.used}/{b.seats.included} seats used</p>
            </div>
            <button data-testid="upgrade-btn" onClick={() => toast.info("Manage your plan.")} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">Manage plan</button>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-white/10 bg-zinc-900/60 p-6 text-center" data-testid="billing-coming-soon">
          <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-800 text-zinc-400"><Sparkles className="h-5 w-5" /></div>
          <p className="mt-3 text-sm font-semibold text-zinc-100">Billing setup pending</p>
          <p className="mx-auto mt-1 max-w-sm text-xs text-zinc-500">Stripe is not configured. No active subscription or payment method is implied — usage below is informational only.</p>
        </div>
      )}
      <div>
        <p className="mb-3 text-sm font-semibold text-zinc-100">Usage this period</p>
        <div className="space-y-3" data-testid="billing-usage">
          {usageRows.map(([label, used, limit]) => (
            <div key={label}>
              <div className="mb-1 flex items-center justify-between text-xs"><span className="text-zinc-400">{label}</span><span className="text-zinc-300">{used}{limit && BILLING_ENABLED ? ` / ${limit}` : ""}</span></div>
              {limit && BILLING_ENABLED && <div className="h-2 overflow-hidden rounded-full bg-zinc-800"><div className="h-full rounded-full bg-violet-500" style={{ width: `${Math.min(100, (used / limit) * 100)}%` }} /></div>}
            </div>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
