import { useEffect, useState } from "react";
import {
  User, Building2, Palette, Sparkles, FileText, Bell, Shield, KeyRound, CreditCard, Plug, Loader2, Users, Mail,
} from "lucide-react";
import { settingsApi } from "@/lib/api";
import { toast } from "sonner";
import {
  GeneralSection, OrganizationSection, BrandingSection, AISection, DocumentsSection,
  NotificationsSection, SecuritySection, ApiKeysSection, IntegrationsSection, BillingSection,
} from "@/components/settings/sections";
import { TeamSection } from "@/components/settings/TeamSection";
import { EmailSettingsSection } from "@/components/settings/EmailSettingsSection";

const TABS = [
  { id: "general", label: "General", icon: User },
  { id: "organization", label: "Organization", icon: Building2 },
  { id: "team", label: "Team", icon: Users },
  { id: "email", label: "Email", icon: Mail },
  { id: "branding", label: "Branding", icon: Palette },
  { id: "ai", label: "AI Settings", icon: Sparkles },
  { id: "documents", label: "Documents", icon: FileText },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "security", label: "Security", icon: Shield },
  { id: "apikeys", label: "API Keys", icon: KeyRound },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "integrations", label: "Integrations", icon: Plug },
];

export default function Settings() {
  const [tab, setTab] = useState("general");
  const [data, setData] = useState(null);

  const load = () => settingsApi.get().then(setData).catch((e) => toast.error(e.message));
  useEffect(() => { load(); }, []);

  const needsData = ["organization", "branding", "ai", "documents", "notifications", "email"].includes(tab);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[220px_1fr]" data-testid="settings-page">
      <nav className="flex gap-1 overflow-x-auto lg:flex-col">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} data-testid={`settings-tab-${t.id}`}
            className={`flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${tab === t.id ? "bg-violet-600/15 text-violet-300" : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"}`}>
            <t.icon className="h-4 w-4" />{t.label}
          </button>
        ))}
      </nav>

      <div>
        {needsData && !data ? (
          <div className="flex items-center justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
        ) : (
          <>
            {tab === "general" && <GeneralSection />}
            {tab === "organization" && <OrganizationSection data={data} reload={load} />}
            {tab === "team" && <TeamSection />}
            {tab === "email" && <EmailSettingsSection data={data} reload={load} />}
            {tab === "branding" && <BrandingSection data={data} />}
            {tab === "ai" && <AISection data={data} />}
            {tab === "documents" && <DocumentsSection data={data} />}
            {tab === "notifications" && <NotificationsSection data={data} />}
            {tab === "security" && <SecuritySection />}
            {tab === "apikeys" && <ApiKeysSection />}
            {tab === "billing" && <BillingSection />}
            {tab === "integrations" && <IntegrationsSection />}
          </>
        )}
      </div>
    </div>
  );
}
