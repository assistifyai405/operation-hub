import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Users, FolderKanban, CheckSquare, MessageSquare,
  Bot, FileText, FolderOpen, BarChart3, Settings as SettingsIcon,
  Search, Bell, Menu, X, Sparkles, LogOut,
} from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { currentUser, notifications } from "@/data/mock";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/clients", label: "Clients", icon: Users },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/tasks", label: "Tasks", icon: CheckSquare },
  { to: "/ai-chat", label: "AI Chat", icon: MessageSquare },
  { to: "/ai-agents", label: "AI Agents", icon: Bot },
  { to: "/proposals", label: "Proposals", icon: FileText },
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
      <p className="text-sm font-semibold text-zinc-100">Upgrade to Pro</p>
      <p className="mt-1 text-xs text-zinc-400">Unlock unlimited AI agents & automations.</p>
      <button data-testid="upgrade-btn" className="mt-3 w-full rounded-lg bg-violet-600 py-2 text-xs font-semibold text-white transition-all hover:bg-violet-500">
        Upgrade
      </button>
    </div>
  </div>
);

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const pageTitle = nav.find((n) => n.to === location.pathname)?.label || "Dashboard";

  return (
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
            <button className="absolute right-3 top-5 text-zinc-400" onClick={() => setMobileOpen(false)} data-testid="mobile-close">
              <X className="h-5 w-5" />
            </button>
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <div className="lg:ml-64">
        {/* Header */}
        <header className="sticky top-0 z-30 flex items-center gap-4 border-b border-white/10 bg-black/60 px-4 py-3.5 backdrop-blur-xl sm:px-8">
          <button className="lg:hidden text-zinc-400" onClick={() => setMobileOpen(true)} data-testid="mobile-menu">
            <Menu className="h-5 w-5" />
          </button>
          <h1 className="text-lg font-semibold tracking-tight" data-testid="page-title">{pageTitle}</h1>
          <div className="relative ml-auto hidden max-w-xs flex-1 sm:block">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input
              data-testid="global-search"
              placeholder="Search anything..."
              className="w-full rounded-lg border border-white/10 bg-zinc-950 py-2 pl-9 pr-3 text-sm text-zinc-200 outline-none transition-all placeholder:text-zinc-600 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40"
            />
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="relative rounded-lg border border-white/10 bg-zinc-950 p-2 text-zinc-400 transition-all hover:text-zinc-100" data-testid="notifications-btn">
                <Bell className="h-[18px] w-[18px]" />
                <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-violet-500 animate-pulse-glow" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80 border-white/10 bg-zinc-950 text-zinc-200">
              <DropdownMenuLabel>Notifications</DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-white/10" />
              {notifications.map((n) => (
                <DropdownMenuItem key={n.id} className="flex flex-col items-start gap-0.5 focus:bg-zinc-900">
                  <span className="text-sm text-zinc-200">{n.text}</span>
                  <span className="text-xs text-zinc-500">{n.time}</span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2" data-testid="user-menu">
                <Avatar className="h-8 w-8 border border-white/10">
                  <AvatarImage src={currentUser.avatar} />
                  <AvatarFallback>JR</AvatarFallback>
                </Avatar>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56 border-white/10 bg-zinc-950 text-zinc-200">
              <DropdownMenuLabel>
                <p className="text-sm font-medium">{currentUser.name}</p>
                <p className="text-xs font-normal text-zinc-500">{currentUser.email}</p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-white/10" />
              <DropdownMenuItem className="focus:bg-zinc-900" onClick={() => navigate("/settings")}>
                <SettingsIcon className="mr-2 h-4 w-4" /> Settings
              </DropdownMenuItem>
              <DropdownMenuItem className="focus:bg-zinc-900" onClick={() => navigate("/")} data-testid="logout-btn">
                <LogOut className="mr-2 h-4 w-4" /> Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        <main className="p-4 sm:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
