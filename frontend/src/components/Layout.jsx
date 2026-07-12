import { useState, useEffect } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Users, FolderKanban, CheckSquare, MessageSquare,
  Bot, FileText, FolderOpen, BarChart3, Settings as SettingsIcon,
  Search, Bell, Menu, X, Sparkles, LogOut, MailWarning, ScrollText, Receipt, LayoutGrid,
} from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/context/AuthContext";
import { authApi, notificationsApi, aiApi } from "@/lib/api";
import { toast } from "sonner";
import CommandPalette from "@/components/CommandPalette";
import OnboardingWizard from "@/components/OnboardingWizard";
import { AiIcon } from "@/components/ai/aiHelpers";
import { BILLING_ENABLED } from "@/lib/config";
import { AssistantProvider } from "@/context/AssistantContext";
import FloatingAssistant from "@/components/assistant/FloatingAssistant";

const relativeTime = (iso) => {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/clients", label: "Clients", icon: Users },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/tasks", label: "Tasks", icon: CheckSquare },
  { to: "/ai-chat", label: "Copilot", icon: Sparkles },
  { to: "/ai-workspace", label: "AI Workspace", icon: LayoutGrid },
  { to: "/ai-agents", label: "AI Agents", icon: Bot },
  { to: "/proposals", label: "Proposals", icon: FileText },
  { to: "/contracts", label: "Contracts", icon: ScrollText },
  { to: "/invoices", label: "Invoices", icon: Receipt },
  { to: "/documents", label: "Documents", icon: FolderOpen },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

const Sidebar = ({ onNavigate }) => (
  <div className="flex h-full flex-col">
    <div className="flex items-center gap-2.5 px-6 py-6">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 glow-violet">
        <Sparkles className="h-5 w-5 text-white" />
      </div>
      <div className="leading-tight">
        <p className="text-[15px] font-bold tracking-tight text-zinc-50">Assistify</p>
        <p className="text-[10px] font-medium uppercase tracking-[0.25em] text-violet-400">OS</p>
      </div>
    </div>
    <nav className="flex-1 space-y-1 px-3 py-2" data-testid="sidebar-nav">
      {nav.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          onClick={onNavigate}
          data-testid={`nav-${label.toLowerCase().replace(/\s/g, "-")}`}
          className={({ isActive }) =>
            `group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
              isActive
                ? "bg-violet-600/15 text-violet-300 shadow-[inset_0_0_0_1px_rgba(139,92,246,0.25)]"
                : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100"
            }`
          }
        >
          {({ isActive }) => (
            <>
              <Icon className={`h-[18px] w-[18px] transition-colors ${isActive ? "text-violet-400" : "text-zinc-500 group-hover:text-zinc-300"}`} />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
    <div className="m-3 rounded-xl border border-white/10 bg-gradient-to-br from-violet-600/20 to-transparent p-4">
      {BILLING_ENABLED ? (
        <>
          <p className="text-sm font-semibold text-zinc-100">Upgrade to Pro</p>
          <p className="mt-1 text-xs text-zinc-400">Unlock unlimited AI agents & automations.</p>
          <button data-testid="upgrade-btn" className="mt-3 w-full rounded-lg bg-violet-600 py-2 text-xs font-semibold text-white transition-all hover:bg-violet-500">
            Upgrade
          </button>
        </>
      ) : (
        <>
          <p className="flex items-center gap-1.5 text-sm font-semibold text-zinc-100"><Sparkles className="h-3.5 w-3.5 text-violet-400" /> Pro plan</p>
          <p className="mt-1 text-xs text-zinc-400">Unlimited AI agents & automations — coming soon.</p>
        </>
      )}
    </div>
  </div>
);

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [bannerDismissed, setBannerDismissed] = useState(() => sessionStorage.getItem("verify_banner_dismissed") === "1");
  const location = useLocation();
  const navigate = useNavigate();
  const { user, setUser, logout } = useAuth();
  const pageTitle = [...nav].reverse().find((n) => location.pathname === n.to || location.pathname.startsWith(n.to + "/"))?.label || "Dashboard";

  useEffect(() => {
    if (user && user.onboardingCompleted === false) setWizardOpen(true);
  }, [user]);

  useEffect(() => {
    if (user) aiApi.notifications().then(setNotifications).catch(() => notificationsApi.list().then(setNotifications).catch(() => {}));
  }, [user, location.pathname]);

  const finishOnboarding = () => {
    setWizardOpen(false);
    setUser((u) => (u ? { ...u, onboardingCompleted: true } : u));
  };

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
      toast.success("Verification email sent — please check your inbox.");
    } catch (e) {
      toast.error(e.message);
    }
  };

  return (
    <AssistantProvider>
    <div className="min-h-screen bg-black text-zinc-50">
      {/* Desktop sidebar */}
      <aside className="fixed left-0 top-0 z-40 hidden h-screen w-64 border-r border-white/10 bg-black lg:block">
        <Sidebar />
      </aside>

      {/* Mobile sidebar */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 border-r border-white/10 bg-black animate-fade-up">
            <button className="absolute right-3 top-5 text-zinc-400 focus-visible:ring-2 focus-visible:ring-violet-500 rounded-md" onClick={() => setMobileOpen(false)} data-testid="mobile-close" aria-label="Close navigation menu">
              <X className="h-5 w-5" />
            </button>
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <div className="lg:ml-64">
        {/* Header */}
        <header className="sticky top-0 z-30 flex items-center gap-4 border-b border-white/10 bg-black/60 px-4 py-3.5 backdrop-blur-xl sm:px-8">
          <button className="lg:hidden text-zinc-400" onClick={() => setMobileOpen(true)} data-testid="mobile-menu" aria-label="Open navigation menu">
            <Menu className="h-5 w-5" />
          </button>
          <h1 className="text-lg font-semibold tracking-tight" data-testid="page-title">{pageTitle}</h1>
          <div className="relative ml-auto hidden max-w-xs flex-1 sm:block">
            <button
              onClick={() => setPaletteOpen(true)}
              data-testid="open-command-palette"
              className="flex w-full items-center gap-2 rounded-lg border border-white/10 bg-zinc-950 py-2 pl-3 pr-2 text-sm text-zinc-500 transition-all hover:border-violet-500/40 hover:text-zinc-300"
            >
              <Search className="h-4 w-4" />
              <span>Search or run command…</span>
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
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="relative rounded-lg border border-white/10 bg-zinc-950 p-2 text-zinc-400 transition-all hover:text-zinc-100" data-testid="notifications-btn" aria-label={notifications.length ? `Notifications, ${notifications.length} recent` : "Notifications"}>
                <Bell className="h-[18px] w-[18px]" />
                {notifications.length > 0 && <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-violet-500 animate-pulse-glow" />}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-96 max-w-[92vw] border-white/10 bg-zinc-950 text-zinc-200">
              <DropdownMenuLabel className="flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5 text-violet-400" /> Assistify notifications</DropdownMenuLabel>
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
                  <AvatarFallback className="bg-violet-600/20 text-violet-300 text-xs">{initials}</AvatarFallback>
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
              <DropdownMenuItem className="focus:bg-zinc-900" onClick={() => navigate("/settings")}>
                <SettingsIcon className="mr-2 h-4 w-4" /> Settings
              </DropdownMenuItem>
              <DropdownMenuItem className="focus:bg-zinc-900" onClick={handleLogout} data-testid="logout-btn">
                <LogOut className="mr-2 h-4 w-4" /> Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        {user && !user.emailVerified && !bannerDismissed && (
          <div data-testid="verify-email-banner" role="status" className="flex flex-wrap items-center gap-3 border-b border-amber-500/20 bg-amber-500/10 px-4 py-2.5 sm:px-8">
            <MailWarning className="h-4 w-4 shrink-0 text-amber-400" />
            <p className="text-sm text-amber-200">Verify your email to unlock sending proposals, contracts &amp; invoices to clients.</p>
            <button onClick={resendVerification} data-testid="banner-resend" className="ml-auto rounded-md border border-amber-500/40 px-2.5 py-1 text-xs font-medium text-amber-200 transition-colors hover:bg-amber-500/15 focus-visible:ring-2 focus-visible:ring-amber-400">Resend email</button>
            <button onClick={dismissBanner} data-testid="banner-dismiss" aria-label="Dismiss email verification reminder" className="rounded-md p-1 text-amber-300/70 transition-colors hover:text-amber-200 focus-visible:ring-2 focus-visible:ring-amber-400">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        <main className="p-4 sm:p-8">
          <Outlet />
        </main>
      </div>
      <CommandPalette open={paletteOpen} setOpen={setPaletteOpen} />
      {wizardOpen && <OnboardingWizard open={wizardOpen} onDone={finishOnboarding} />}
      <FloatingAssistant />
    </div>
    </AssistantProvider>
  );
}
