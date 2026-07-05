import { useNavigate } from "react-router-dom";
import {
  DollarSign, FolderKanban, Users, Bot, TrendingUp, ArrowUpRight,
  Plus, MessageSquare, FileText, UserPlus, Activity, Clock,
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar,
} from "recharts";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { stats, revenueData, projectStatusData, agentActivityData, clients, tasks } from "@/data/mock";

const iconMap = { DollarSign, FolderKanban, Users, Bot };

const ChartTip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-xs shadow-xl">
      <p className="mb-1 font-medium text-zinc-300">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color || p.fill }}>{p.name}: {p.value.toLocaleString()}</p>
      ))}
    </div>
  );
};

const quickActions = [
  { label: "New Project", icon: Plus, to: "/projects" },
  { label: "Add Client", icon: UserPlus, to: "/clients" },
  { label: "Ask AI", icon: MessageSquare, to: "/ai-chat" },
  { label: "New Proposal", icon: FileText, to: "/proposals" },
];

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s, i) => {
          const Icon = iconMap[s.icon];
          return (
            <div
              key={s.label}
              style={{ animationDelay: `${i * 60}ms` }}
              className="animate-fade-up rounded-xl border border-white/10 bg-zinc-950 p-5 transition-all duration-300 hover:border-violet-500/40"
              data-testid={`stat-card-${i}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-600/15 text-violet-400">
                  <Icon className="h-5 w-5" />
                </div>
                <span className="flex items-center gap-1 text-xs font-medium text-emerald-400">
                  <ArrowUpRight className="h-3.5 w-3.5" />{s.change}
                </span>
              </div>
              <p className="mt-4 text-2xl font-bold tracking-tight text-zinc-50">{s.value}</p>
              <p className="mt-1 text-sm text-zinc-500">{s.label}</p>
            </div>
          );
        })}
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-3">
        {quickActions.map((a) => (
          <button
            key={a.label}
            onClick={() => navigate(a.to)}
            data-testid={`quick-${a.label.toLowerCase().replace(/\s/g, "-")}`}
            className="flex items-center gap-2 rounded-lg border border-white/10 bg-zinc-950 px-4 py-2 text-sm font-medium text-zinc-300 transition-all hover:border-violet-500/40 hover:text-white"
          >
            <a.icon className="h-4 w-4 text-violet-400" />{a.label}
          </button>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-zinc-100">Revenue Overview</h3>
              <p className="text-xs text-zinc-500">Last 8 months</p>
            </div>
            <span className="flex items-center gap-1 text-xs font-medium text-emerald-400">
              <TrendingUp className="h-4 w-4" /> +18.2%
            </span>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={revenueData}>
              <defs>
                <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="exp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="month" stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip content={<ChartTip />} />
              <Area type="monotone" dataKey="revenue" stroke="#8b5cf6" strokeWidth={2} fill="url(#rev)" isAnimationActive={false} />
              <Area type="monotone" dataKey="expenses" stroke="#22d3ee" strokeWidth={2} fill="url(#exp)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <h3 className="mb-1 text-sm font-semibold text-zinc-100">Projects by Status</h3>
          <p className="mb-2 text-xs text-zinc-500">37 active projects</p>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={projectStatusData} dataKey="value" innerRadius={45} outerRadius={70} paddingAngle={3} stroke="none" isAnimationActive={false}>
                {projectStatusData.map((e) => <Cell key={e.name} fill={e.color} />)}
              </Pie>
              <Tooltip content={<ChartTip />} />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {projectStatusData.map((p) => (
              <div key={p.name} className="flex items-center gap-2 text-xs text-zinc-400">
                <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />{p.name}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Recent clients */}
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <h3 className="mb-4 text-sm font-semibold text-zinc-100">Recent Clients</h3>
          <div className="space-y-3">
            {clients.slice(0, 4).map((c) => (
              <div key={c.id} className="flex items-center gap-3" data-testid={`recent-client-${c.id}`}>
                <Avatar className="h-9 w-9 border border-white/10">
                  <AvatarImage src={c.avatar} />
                  <AvatarFallback>{c.name[0]}</AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-zinc-100">{c.name}</p>
                  <p className="truncate text-xs text-zinc-500">{c.contact}</p>
                </div>
                <span className="text-sm font-semibold text-violet-400">{c.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Upcoming tasks */}
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <div className="mb-4 flex items-center gap-2">
            <Clock className="h-4 w-4 text-violet-400" />
            <h3 className="text-sm font-semibold text-zinc-100">Upcoming Tasks</h3>
          </div>
          <div className="space-y-3">
            {tasks.filter((t) => !t.done).slice(0, 4).map((t) => (
              <div key={t.id} className="flex items-start gap-3">
                <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${t.priority === "High" ? "bg-red-400" : t.priority === "Medium" ? "bg-amber-400" : "bg-zinc-500"}`} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-zinc-200">{t.title}</p>
                  <p className="text-xs text-zinc-500">{t.project} · {t.due}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI agent activity */}
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <div className="mb-4 flex items-center gap-2">
            <Activity className="h-4 w-4 text-violet-400" />
            <h3 className="text-sm font-semibold text-zinc-100">AI Agent Activity</h3>
          </div>
          <ResponsiveContainer width="100%" height={150}>
            <BarChart data={agentActivityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="day" stroke="#71717a" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTip />} cursor={{ fill: "rgba(139,92,246,0.08)" }} />
              <Bar dataKey="runs" fill="#8b5cf6" radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
