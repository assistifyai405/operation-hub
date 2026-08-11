import { useState, useEffect, useMemo } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Users, FolderKanban, CheckSquare, MessageSquare,
  Bot, FileText, FolderOpen, BarChart3, Settings as SettingsIcon,
  Search, Bell, Menu, X, Sparkles, LogOut, MailWarning, ScrollText, Receipt, LayoutGrid, Target, TrendingUp, Brain, Zap, Rocket, Mail, Plug, Inbox,
} from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/context/AuthContext";
import { authApi, notificationsApi, aiApi, onboardingApi, publicConfigApi } from "@/lib/api";
import { toast } from "sonner";
import CommandPalette from "@/components/CommandPalette";
import ProductTour from "@/components/ProductTour";
import { AiIcon } from "@/components/ai/aiHelpers";
import { BILLING_ENABLED, BETA_MODE_BUILD } from "@/lib/config";
import { AssistantProvider } from "@/context/AssistantContext";
import FloatingAssistant from "@/components/assistant/FloatingAssistant";
import BetaFeedbackButton from "@/components/BetaFeedbackButton";
import HelpPanel from "@/help/HelpPanel";
import MiniWalkthrough from "@/help/MiniWalkthrough";
import GuidedTour from "@/help/GuidedTour";
import { useTheme } from "@/context/ThemeContext";

const relativeTime = (iso) => {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

const NAV_ITEMS = [
  { to: "/dashboard", key: "dashboard", icon: LayoutDashboard },
  { to: "/opportunities", key: "opportunities", icon: Target },
  { to: "/automations", key: "automations", icon: Zap },
  { to: "/crm", key: "crm", icon: Users },
  { to: "/pipeline", key: "pipeline", icon: TrendingUp },
  { to: "/clients", key: "clients", icon: Users },
  { to: "/projects", key: "projects", icon: FolderKanban },
  { to: "/tasks", key: "tasks", icon: CheckSquare },
  { to: "/ai-chat", key: "copilot", icon: Sparkles },
  { to: "/ai-workspace", key: "aiWorkspace", icon: LayoutGrid },
  { to: "/knowledge-brain", key: "knowledgeBrain", icon: Brain },
  { to: "/ai-agents", key: "aiAgents", icon: Bot },
  { to: "/proposals", key: "proposals", icon: FileText },
  { to: "/contracts", key: "contracts", icon: ScrollText },
  { to: "/invoices", key: "invoices", icon: Receipt },
  { to: "/documents", key: "documents", icon: FolderOpen },
  { to: "/emails", key: "emails", icon: Mail },
  { to: "/inbox", key: "inbox", icon: Inbox },
  { to: "/integrations", key: "integrations", icon: Plug },
  { to: "/analytics", key: "analytics", icon: BarChart3 },
  { to: "/settings", key: "settings", icon: SettingsIcon },
];

const Sidebar = ({ onNavigate, betaMode, t }) => (
  <div className="flex h-full min-h-0 flex-col">
    <div className="flex shrink-0 items-center gap-2.5 px-6 py-6">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 glow-brand">
        <Sparkles className="h-5 w-5 text-white" />
      </div>
      <div className="leading-tight">
        <p className="text-[15px] font-bold tracking-tight text-zinc-50">{t("app.name")}</p>
        {betaMode ? (
          <p className="text-[10px] font-medium tracking-wide text-zinc-500" data-testid="assistify-beta-badge">{t("app.beta")}</p>
        ) : (
          <p className="text-[10px] font-medium uppercase tracking-[0.25em] text-brand-400">OS</p>
        )}
      </div>
    </div>
    <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto px-3 py-2" data-testid="sidebar-nav">
      {NAV_ITEMS.map(({ to, key, icon: Icon }) => {
        const label = t(`nav.${key}`);
        return (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            data-testid={`nav-${key}`}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-brand-600/15 text-brand-300 shadow-[inset_0_0_0_1px_rgba(34,197,94,0.25)]"
                  : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={`h-[18px] w-[18px] shrink-0 transition-colors ${isActive ? "text-brand-400" : "text-zinc-500 group-hover:text-zinc-300"}`} />
                <span className="truncate">{label}</span>
              </>
            )}
          </NavLink>
        );
      })}
    </nav>
    {BILLING_ENABLED ? (
      <div className="m-3 shrink-0 rounded-xl border border-white/10 bg-gradient-to-br from-brand-600/20 to-transparent p-4" data-testid="sidebar-billing">
        <p className="text-sm font-semibold text-zinc-100">Upgrade to Pro</p>
        <p className="mt-1 text-xs text-zinc-400">Unlock unlimited AI agents & automations.</p>
        <button type="button" data-testid="upgrade-btn" className="mt-3 w-full rounded-lg bg-brand-600 py-2 text-xs font-semibold text-white transition-all hover:bg-brand-500">
          Upgrade
        </button>
      </div>
    ) : (
      <div className="m-3 shrink-0 rounded-xl border border-dashed border-white/10 bg-zinc-950/60 p-4" data-testid="sidebar-billing-pending">
        <p className="text-sm font-semibold text-zinc-300">{t("billing.notAvailable")}</p>
        <p className="mt-1 text-xs text-zinc-500">{t("settings.billingBetaHint")}</p>
      </div>
    )}
  </div>
);

export default function Layout() {
  const { t } = useTranslation();
  const { resolved } = useTheme();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [bannerDismissed, setBannerDismissed] = useState(() => sessionStorage.getItem("verify_banner_dismissed") === "1");
  const [betaMode, setBetaMode] = useState(BETA_MODE_BUILD);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, setUser, logout } = useAuth();
  const pageTitle = useMemo(() => {
    const item = [...NAV_ITEMS].reverse().find((n) => location.pathname === n.to || location.pathname.startsWith(n.to + "/"));
    return item ? t(`nav.${item.key}`) : t("nav.dashboard");
  }, [location.pathname, t]);

  useEffect(() => {
    publicConfigApi.get().then((c) => {
      if (typeof c?.betaMode === "boolean") setBetaMode(c.betaMode);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (user && user.onboardingCompleted === false && location.pathname !== "/onboarding") navigate("/onboarding");
  }, [user, location.pathname, navigate]);

  useEffect(() => {
    if (user) aiApi.notifications().then(setNotifications).catch(() => notificationsApi.list().then(setNotifications).catch(() => {}));
  }, [user, location.pathname]);

  const fullName = user ? `${user.firstName || ""} ${user.lastName || ""}`.trim() || user.email : "";
  const initials = user ? `${(user.firstName || user.email || "?")[0] || ""}${(user.lastName || "")[0] || ""}`.toUpperCase() : "";

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const dismissBanner = () => {
    sessionStorage.setItem("verify_banner_dismissed", "1");
    setBannerDismissed(true);
  };

  const resendVerification = async () => {
    try {
      await authApi.resendVerification();
      toast.success(t("verifyEmail.sent"));
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <AssistantProvider>
    <div className="min-h-screen bg-[var(--theme-background)] text-[var(--theme-text-primary)]" data-testid="app-shell" data-resolved-theme={resolved}>
      {/* Desktop sidebar */}
      <aside className="fixed left-0 top-0 z-40 hidden h-screen w-64 border-r border-[var(--theme-border)] bg-[var(--theme-surface)] lg:block">
        <Sidebar betaMode={betaMode} t={t} />
      </aside>

      {/* Mobile sidebar */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 border-r border-[var(--theme-border)] bg-[var(--theme-surface)] animate-fade-up">
            <button className="absolute right-3 top-5 text-[var(--theme-text-secondary)] focus-visible:ring-2 focus-visible:ring-brand-500 rounded-md" onClick={() => setMobileOpen(false)} data-testid="mobile-close" aria-label={t("nav.closeMenu", { defaultValue: "Close navigation menu" })}>
              <X className="h-5 w-5" />
            </button>
            <Sidebar onNavigate={() => setMobileOpen(false)} betaMode={betaMode} t={t} />
          </aside>
        </div>
      )}

      <div className="lg:ml-64">
        {/* Header */}
        <header className="sticky top-0 z-30 flex items-center gap-4 border-b border-[var(--theme-border)] bg-[color-mix(in_srgb,var(--theme-surface)_88%,transparent)] px-4 py-3.5 backdrop-blur-xl sm:px-8">
          <button className="lg:hidden text-[var(--theme-text-secondary)]" onClick={() => setMobileOpen(true)} data-testid="mobile-menu" aria-label={t("nav.openMenu", { defaultValue: "Open navigation menu" })}>
            <Menu className="h-5 w-5" />
          </button>
          <h1 className="min-w-0 truncate text-lg font-semibold tracking-tight" data-testid="page-title">{pageTitle}</h1>
          {betaMode && (
            <span className="hidden rounded border border-white/10 px-2 py-0.5 text-[10px] font-medium tracking-wide text-zinc-400 sm:inline" data-testid="header-beta-badge">
              Assistify Beta
            </span>
          )}
          <div className="relative ml-auto hidden max-w-xs flex-1 sm:block">
            <button
              onClick={() => setPaletteOpen(true)}
              data-testid="open-command-palette"
              className="flex w-full items-center gap-2 rounded-lg border border-white/10 bg-zinc-950 py-2 pl-3 pr-2 text-sm text-zinc-500 transition-all hover:border-brand-500/40 hover:text-zinc-300"
            >
              <Search className="h-4 w-4" />
              <span>{t("command.placeholder")}</span>
              <kbd className="ml-auto rounded border border-white/10 bg-zinc-900 px-1.5 py-0.5 text-[10px] font-medium text-zinc-400">⌘K</kbd>
            </button>
          </div>
          <button
            onClick={() => setPaletteOpen(true)}
            data-testid="open-command-palette-mobile"
            aria-label="Search or run a command"
            className="rounded-lg border border-white/10 bg-zinc-950 p-2 text-zinc-400 transition-all hover:text-zinc-100 sm:hidden ml-auto"
          >
            <Search className="h-[18px] w-[18px]" />
          </button>
          {betaMode && <BetaFeedbackButton />}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="relative rounded-lg border border-white/10 bg-zinc-950 p-2 text-zinc-400 transition-all hover:text-zinc-100" data-testid="notifications-btn" aria-label={notifications.length ? `Notifications, ${notifications.length} recent` : "Notifications"}>
                <Bell className="h-[18px] w-[18px]" />
                {notifications.length > 0 && <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-brand-500 animate-pulse-glow" />}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-96 max-w-[92vw] border-white/10 bg-zinc-950 text-zinc-200">
              <DropdownMenuLabel className="flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5 text-brand-400" /> Assistify notifications</DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-white/10" />
              {notifications.length === 0 ? (
                <div className="px-2 py-6 text-center text-xs text-zinc-500" data-testid="notifications-empty">Nothing needs your attention right now.</div>
              ) : notifications.slice(0, 8).map((n, i) => (
                <DropdownMenuItem key={i} onClick={() => n.link && navigate(n.link)} className="flex items-start gap-2.5 focus:bg-zinc-900" data-testid="notification-item">
                  <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${n.kind === "insight" ? "bg-amber-500/15 text-amber-400" : "bg-emerald-500/15 text-emerald-400"}`}>
                    <AiIcon name={n.icon} className="h-3.5 w-3.5" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-zinc-100">{n.title}</span>
                    <span className="block text-xs leading-snug text-zinc-400 whitespace-normal">{n.message}</span>
                    <span className="block text-[11px] text-zinc-600">{relativeTime(n.created_at)}</span>
                  </span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2" data-testid="user-menu" aria-label="Account menu">
                <Avatar className="h-8 w-8 border border-white/10">
                  <AvatarImage src={user?.avatar} alt={fullName ? `${fullName} avatar` : "User avatar"} />
                  <AvatarFallback className="bg-brand-600/20 text-brand-300 text-xs">{initials}</AvatarFallback>
                </Avatar>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56 border-white/10 bg-zinc-950 text-zinc-200">
              <DropdownMenuLabel>
                <p className="text-sm font-medium" data-testid="user-name">{fullName}</p>
                <p className="text-xs font-normal text-zinc-500">{user?.email}</p>
                {user && !user.emailVerified && (
                  <span className="mt-1 inline-block rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-400" data-testid="unverified-badge">Email unverified</span>
                )}
              </DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-white/10" />
              {user && !user.emailVerified && (
                <DropdownMenuItem className="focus:bg-zinc-900" onClick={resendVerification} data-testid="resend-verification">
                  <MailWarning className="mr-2 h-4 w-4" /> Verify email
                </DropdownMenuItem>
              )}
              <DropdownMenuItem className="focus:bg-zinc-900" onClick={() => navigate("/ai-workspace")} data-testid="menu-ai-history">
                <Sparkles className="mr-2 h-4 w-4" /> AI Workspace
              </DropdownMenuItem>
              <DropdownMenuItem className="focus:bg-zinc-900" onClick={async () => { try { await onboardingApi.restart(); } catch (_) {} setUser((u) => (u ? { ...u, onboardingCompleted: false } : u)); navigate("/onboarding"); }} data-testid="menu-restart-onboarding">
                <Rocket className="mr-2 h-4 w-4" /> Restart onboarding
              </DropdownMenuItem>
              <DropdownMenuItem className="focus:bg-zinc-900" onClick={() => navigate("/settings")}>
                <SettingsIcon className="mr-2 h-4 w-4" /> {t("common.settings")}
              </DropdownMenuItem>
              <DropdownMenuItem className="focus:bg-zinc-900" onClick={handleLogout} data-testid="logout-btn">
                <LogOut className="mr-2 h-4 w-4" /> {t("common.logout")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        {user && !user.emailVerified && !bannerDismissed && (
          <div data-testid="verify-email-banner" role="status" className="flex flex-wrap items-center gap-3 border-b border-amber-500/20 bg-amber-500/10 px-4 py-2.5 sm:px-8">
            <MailWarning className="h-4 w-4 shrink-0 text-amber-400" />
            <p className="text-sm text-amber-200">{t("verifyEmail.banner")}</p>
            <button onClick={resendVerification} data-testid="banner-resend" className="ml-auto rounded-md border border-amber-500/40 px-2.5 py-1 text-xs font-medium text-amber-200 transition-colors hover:bg-amber-500/15 focus-visible:ring-2 focus-visible:ring-amber-400">{t("verifyEmail.resend")}</button>
            <button onClick={dismissBanner} data-testid="banner-dismiss" aria-label={t("verifyEmail.dismiss")} className="rounded-md p-1 text-amber-300/70 transition-colors hover:text-amber-200 focus-visible:ring-2 focus-visible:ring-amber-400">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        <main className="p-4 sm:p-8">
          <Outlet />
        </main>
      </div>
      <CommandPalette open={paletteOpen} setOpen={setPaletteOpen} />
      {user?.onboardingCompleted !== false && (
        <ProductTour onOpenCommandPalette={() => setPaletteOpen(true)} />
      )}
      <FloatingAssistant />
      <HelpPanel />
      <MiniWalkthrough />
      <GuidedTour />
    </div>
    </AssistantProvider>
  );
}
