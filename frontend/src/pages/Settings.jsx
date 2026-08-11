import { useEffect, useState } from "react";
import {
  User, Building2, Palette, Sparkles, FileText, Bell, Shield, KeyRound, CreditCard, Plug, Loader2, Users, Mail, Activity, MessageSquare, Languages,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { settingsApi } from "@/lib/api";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import {
  GeneralSection, OrganizationSection, BrandingSection, AISection, DocumentsSection,
  NotificationsSection, SecuritySection, ApiKeysSection, IntegrationsSection, BillingSection,
} from "@/components/settings/sections";
import { TeamSection } from "@/components/settings/TeamSection";
import { EmailSettingsSection } from "@/components/settings/EmailSettingsSection";
import { OperationsSection } from "@/components/settings/OperationsSection";
import { BetaFeedbackSection } from "@/components/settings/BetaFeedbackSection";
import { LanguageSection } from "@/components/settings/LanguageSection";
import PageIntro from "@/components/PageIntro";

const TAB_DEFS = [
  { id: "general", key: "general", icon: User },
  { id: "language", key: "language", icon: Languages },
  { id: "organization", key: "organization", icon: Building2 },
  { id: "team", key: "team", icon: Users },
  { id: "email", key: "email", icon: Mail },
  { id: "branding", key: "branding", icon: Palette },
  { id: "ai", key: "ai", icon: Sparkles },
  { id: "documents", key: "documents", icon: FileText },
  { id: "notifications", key: "notifications", icon: Bell },
  { id: "security", key: "security", icon: Shield },
  { id: "apikeys", key: "apikeys", icon: KeyRound },
  { id: "billing", key: "billing", icon: CreditCard },
  { id: "integrations", key: "integrations", icon: Plug },
  { id: "operations", key: "operations", icon: Activity, adminOnly: true },
  { id: "feedback", key: "feedback", icon: MessageSquare, adminOnly: true },
];

export default function Settings() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isAdmin = user?.role === "owner" || user?.role === "admin";
  const [tab, setTab] = useState("general");
  const [data, setData] = useState(null);

  const load = () => settingsApi.get().then(setData).catch((e) => toast.error(e.message));
  useEffect(() => { load(); }, []);

  const tabs = TAB_DEFS.filter((x) => !x.adminOnly || isAdmin);
  const needsData = ["organization", "branding", "ai", "documents", "notifications", "email"].includes(tab);

  return (
    <div data-testid="settings-page">
      <PageIntro title={t("pages.settings.title")} description={t("pages.settings.description")} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[220px_1fr]">
        <nav className="flex gap-1 overflow-x-auto lg:flex-col">
          {tabs.map((item) => (
            <button key={item.id} onClick={() => setTab(item.id)} data-testid={`settings-tab-${item.id}`}
              className={`flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${tab === item.id ? "bg-brand-600/15 text-brand-300" : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"}`}>
              <item.icon className="h-4 w-4" />{t(`settings.tabs.${item.key}`)}
            </button>
          ))}
        </nav>

        <div>
          {needsData && !data ? (
            <div className="flex items-center justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
          ) : (
            <>
              {tab === "general" && <GeneralSection />}
              {tab === "language" && <LanguageSection />}
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
              {tab === "operations" && isAdmin && <OperationsSection />}
              {tab === "feedback" && isAdmin && <BetaFeedbackSection />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
