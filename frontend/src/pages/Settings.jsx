import { useState } from "react";
import { User, Bell, CreditCard, Shield, Palette } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { toast } from "sonner";
import { currentUser } from "@/data/mock";

const tabs = [
  { id: "profile", label: "Profile", icon: User },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "security", label: "Security", icon: Shield },
  { id: "appearance", label: "Appearance", icon: Palette },
];

const Field = ({ label, defaultValue, type = "text" }) => (
  <div>
    <label className="mb-1.5 block text-xs font-medium text-zinc-400">{label}</label>
    <input type={type} defaultValue={defaultValue} className="w-full rounded-lg border border-white/10 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-100 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
  </div>
);

const Row = ({ label, desc, defaultChecked }) => (
  <div className="flex items-center justify-between border-b border-white/5 py-4 last:border-0">
    <div>
      <p className="text-sm font-medium text-zinc-100">{label}</p>
      <p className="text-xs text-zinc-500">{desc}</p>
    </div>
    <Switch defaultChecked={defaultChecked} className="data-[state=checked]:bg-violet-600" />
  </div>
);

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
        {tab === "profile" && (
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16 border border-white/10"><AvatarImage src={currentUser.avatar} /><AvatarFallback>JR</AvatarFallback></Avatar>
              <button className="rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-sm text-zinc-200 transition-all hover:border-violet-500/40">Change photo</button>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Full name" defaultValue={currentUser.name} />
              <Field label="Email" defaultValue={currentUser.email} type="email" />
              <Field label="Role" defaultValue={currentUser.role} />
              <Field label="Company" defaultValue="Assistify Inc." />
            </div>
            <button onClick={() => toast.success("Profile saved")} data-testid="save-profile-btn" className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">Save changes</button>
          </div>
        )}
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
              <p className="text-sm font-semibold text-violet-300">{currentUser.plan} Plan</p>
              <p className="mt-1 text-2xl font-bold text-zinc-50">$99<span className="text-sm font-normal text-zinc-500">/mo</span></p>
              <p className="mt-1 text-xs text-zinc-400">Renews on Sep 1, 2026</p>
            </div>
            <button className="rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-200 transition-all hover:border-violet-500/40">Manage subscription</button>
          </div>
        )}
        {tab === "security" && (
          <div>
            <Row label="Two-factor authentication" desc="Add an extra layer of security" defaultChecked />
            <Row label="Login alerts" desc="Notify on new device sign-ins" defaultChecked />
            <div className="pt-4">
              <button className="rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-200 transition-all hover:border-violet-500/40">Change password</button>
            </div>
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
