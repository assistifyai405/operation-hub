import { useState } from "react";
import { User, Bell, CreditCard, Shield, Palette, Loader2 } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { authApi } from "@/lib/api";

const tabs = [
  { id: "profile", label: "Profile", icon: User },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "security", label: "Security", icon: Shield },
  { id: "appearance", label: "Appearance", icon: Palette },
];

const TIMEZONES = ["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Europe/Berlin", "Asia/Kolkata", "Asia/Singapore", "Australia/Sydney"];
const LANGUAGES = [["en", "English"], ["es", "Español"], ["fr", "Français"], ["de", "Deutsch"], ["pt", "Português"], ["hi", "हिन्दी"]];

const inputCls = "w-full rounded-lg border border-white/10 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-100 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40";

const Row = ({ label, desc, defaultChecked }) => (
  <div className="flex items-center justify-between border-b border-white/5 py-4 last:border-0">
    <div>
      <p className="text-sm font-medium text-zinc-100">{label}</p>
      <p className="text-xs text-zinc-500">{desc}</p>
    </div>
    <Switch defaultChecked={defaultChecked} className="data-[state=checked]:bg-violet-600" />
  </div>
);

function ProfileTab() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({
    firstName: user.firstName || "", lastName: user.lastName || "", avatar: user.avatar || "",
    timezone: user.timezone || "UTC", language: user.language || "en", company: "",
  });
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const initials = `${(form.firstName || user.email)[0] || ""}${(form.lastName || "")[0] || ""}`.toUpperCase();

  const save = async () => {
    setSaving(true);
    try {
      const updated = await authApi.updateProfile(form);
      setUser(updated);
      toast.success("Profile saved");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="profile-tab">
      <div className="flex items-center gap-4">
        <Avatar className="h-16 w-16 border border-white/10">
          <AvatarImage src={form.avatar} />
          <AvatarFallback className="bg-violet-600/20 text-violet-300">{initials}</AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Avatar URL</label>
          <input value={form.avatar} onChange={set("avatar")} data-testid="profile-avatar" className={inputCls} placeholder="https://…" />
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">First name</label>
          <input value={form.firstName} onChange={set("firstName")} data-testid="profile-firstname" className={inputCls} />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Last name</label>
          <input value={form.lastName} onChange={set("lastName")} data-testid="profile-lastname" className={inputCls} />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Email</label>
          <input value={user.email} disabled className={`${inputCls} opacity-60`} />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Company</label>
          <input value={form.company} onChange={set("company")} data-testid="profile-company" className={inputCls} placeholder="Leave blank to keep current" />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Timezone</label>
          <select value={form.timezone} onChange={set("timezone")} data-testid="profile-timezone" className={inputCls}>
            {TIMEZONES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Language</label>
          <select value={form.language} onChange={set("language")} data-testid="profile-language" className={inputCls}>
            {LANGUAGES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      </div>
      <button onClick={save} disabled={saving} data-testid="save-profile-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-60 glow-violet">
        {saving && <Loader2 className="h-4 w-4 animate-spin" />} Save changes
      </button>
    </div>
  );
}

function SecurityTab() {
  const [pw, setPw] = useState({ currentPassword: "", newPassword: "", confirm: "" });
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setPw((p) => ({ ...p, [k]: e.target.value }));

  const change = async () => {
    if (pw.newPassword.length < 8) return toast.error("New password must be at least 8 characters");
    if (pw.newPassword !== pw.confirm) return toast.error("Passwords do not match");
    setSaving(true);
    try {
      await authApi.changePassword({ currentPassword: pw.currentPassword, newPassword: pw.newPassword });
      setPw({ currentPassword: "", newPassword: "", confirm: "" });
      toast.success("Password changed");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="security-tab">
      <div className="max-w-md space-y-4">
        <p className="text-sm font-semibold text-zinc-100">Change password</p>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Current password</label>
          <input type="password" value={pw.currentPassword} onChange={set("currentPassword")} data-testid="current-password" className={inputCls} />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">New password</label>
          <input type="password" value={pw.newPassword} onChange={set("newPassword")} data-testid="new-password" className={inputCls} />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Confirm new password</label>
          <input type="password" value={pw.confirm} onChange={set("confirm")} data-testid="confirm-password" className={inputCls} />
        </div>
        <button onClick={change} disabled={saving} data-testid="change-password-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-60">
          {saving && <Loader2 className="h-4 w-4 animate-spin" />} Update password
        </button>
      </div>
      <div className="border-t border-white/5 pt-4">
        <Row label="Login alerts" desc="Notify on new device sign-ins" defaultChecked />
      </div>
    </div>
  );
}

export default function Settings() {
  const [tab, setTab] = useState("profile");

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[220px_1fr]" data-testid="settings-page">
      <nav className="flex gap-1 overflow-x-auto lg:flex-col">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            data-testid={`settings-tab-${t.id}`}
            className={`flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${tab === t.id ? "bg-violet-600/15 text-violet-300" : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"}`}
          >
            <t.icon className="h-4 w-4" />{t.label}
          </button>
        ))}
      </nav>

      <div className="rounded-xl border border-white/10 bg-zinc-950 p-6">
        {tab === "profile" && <ProfileTab />}
        {tab === "security" && <SecurityTab />}
        {tab === "notifications" && (
          <div>
            <Row label="Email notifications" desc="Receive updates in your inbox" defaultChecked />
            <Row label="Task reminders" desc="Get reminded about upcoming tasks" defaultChecked />
            <Row label="AI agent alerts" desc="Notify when agents complete runs" />
            <Row label="Weekly digest" desc="Summary of your business every Monday" defaultChecked />
          </div>
        )}
        {tab === "billing" && (
          <div className="space-y-4">
            <div className="rounded-xl border border-violet-500/20 bg-violet-600/10 p-5">
              <p className="text-sm font-semibold text-violet-300">Pro Plan</p>
              <p className="mt-1 text-2xl font-bold text-zinc-50">$99<span className="text-sm font-normal text-zinc-500">/mo</span></p>
              <p className="mt-1 text-xs text-zinc-400">Renews on Sep 1, 2026</p>
            </div>
            <button className="rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-200 transition-all hover:border-violet-500/40">Manage subscription</button>
          </div>
        )}
        {tab === "appearance" && (
          <div>
            <Row label="Dark mode" desc="Currently enabled" defaultChecked />
            <Row label="Reduce motion" desc="Minimize animations" />
            <Row label="Compact layout" desc="Denser spacing across the app" />
          </div>
        )}
      </div>
    </div>
  );
}
