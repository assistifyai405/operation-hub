import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FolderKanban, Users, CheckCircle2, ListTodo, TrendingUp,
  Plus, MessageSquare, FileText, UserPlus, Activity, Clock, Loader2,
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar,
} from "recharts";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { revenueData, agentActivityData } from "@/data/mock";
import { clientsApi, projectsApi, tasksApi } from "@/lib/api";
import { toast } from "sonner";

const ChartTip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-xs shadow-xl">
      <p className="mb-1 font-medium text-zinc-300">{label}</p>
      {payload.map((p) => <p key={p.name} style={{ color: p.color || p.fill }}>{p.name}: {p.value.toLocaleString()}</p>)}
    </div>
  );
};

const quickActions = [
  { label: "New Project", icon: Plus, to: "/projects" },
  { label: "Add Client", icon: UserPlus, to: "/clients" },
  { label: "Ask AI", icon: MessageSquare, to: "/ai-chat" },
  { label: "New Proposal", icon: FileText, to: "/proposals" },
];

const statusColor = { "In Progress": "#8b5cf6", Review: "#22d3ee", Completed: "#34d399", Blocked: "#f87171" };
const priorityDot = { High: "bg-red-400", Medium: "bg-amber-400", Low: "bg-zinc-500" };

export default function Dashboard() {
  const navigate = useNavigate();
  const [clients, setClients] = useState([]);
  const [projects, setProjects] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([clientsApi.list(), projectsApi.list(), tasksApi.list()])
      .then(([c, p, t]) => { setClients(c); setProjects(p); setTasks(t); })
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
  }, []);

  const activeProjects = projects.filter((p) => p.status !== "Completed").length;
  const openTasks = tasks.filter((t) => !t.done);
  const completedTasks = tasks.filter((t) => t.done).length;

  const stats = [
    { label: "Total Clients", value: clients.length, icon: Users, to: "/clients" },
    { label: "Active Projects", value: activeProjects, icon: FolderKanban, to: "/projects" },
    { label: "Open Tasks", value: openTasks.length, icon: ListTodo, to: "/tasks" },
    { label: "Completed Tasks", value: completedTasks, icon: CheckCircle2, to: "/tasks" },
  ];

  const recentClients = clients.slice(0, 5);
  const upcomingTasks = [...openTasks].sort((a, b) => {
    if (!a.due) return 1;
    if (!b.due) return -1;
    return new Date(a.due) - new Date(b.due);
  }).slice(0, 5);

  const projectPie = Object.entries(
    projects.reduce((acc, p) => { acc[p.status] = (acc[p.status] || 0) + 1; return acc; }, {})
  ).map(([name, value]) => ({ name, value, color: statusColor[name] || "#8b5cf6" }));

  const fmtDue = (d) => d ? new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "No due date";

  if (loading) {
    return <div className="flex items-center justify-center py-32 text-zinc-500" data-testid="dashboard-loading"><Loader2 className="h-7 w-7 animate-spin" /></div>;
  }

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s, i) => (
          <button
            key={s.label}
            onClick={() => navigate(s.to)}
            style={{ animationDelay: `${i * 60}ms` }}
            className="animate-fade-up rounded-xl border border-white/10 bg-zinc-950 p-5 text-left transition-all duration-300 hover:border-violet-500/40"
            data-testid={`stat-card-${i}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-600/15 text-violet-400">
                <s.icon className="h-5 w-5" />
              </div>
            </div>
            <p className="mt-4 text-2xl font-bold tracking-tight text-zinc-50" data-testid={`stat-value-${i}`}>{s.value}</p>
            <p className="mt-1 text-sm text-zinc-500">{s.label}</p>
          </button>
        ))}
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-3">
        {quickActions.map((a) => (
          <button key={a.label} onClick={() => navigate(a.to)} data-testid={`quick-${a.label.toLowerCase().replace(/\s/g, "-")}`}
            className="flex items-center gap-2 rounded-lg border border-white/10 bg-zinc-950 px-4 py-2 text-sm font-medium text-zinc-300 transition-all hover:border-violet-500/40 hover:text-white">
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
            <span className="flex items-center gap-1 text-xs font-medium text-emerald-400"><TrendingUp className="h-4 w-4" /> +18.2%</span>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={revenueData}>
              <defs>
                <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.4} /><stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} /></linearGradient>
                <linearGradient id="exp" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#22d3ee" stopOpacity={0.25} /><stop offset="100%" stopColor="#22d3ee" stopOpacity={0} /></linearGradient>
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
          <p className="mb-2 text-xs text-zinc-500">{projects.length} total project{projects.length !== 1 && "s"}</p>
          {projectPie.length === 0 ? (
            <div className="flex h-[180px] items-center justify-center text-center text-sm text-zinc-600" data-testid="pie-empty">No projects yet</div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={projectPie} dataKey="value" innerRadius={45} outerRadius={70} paddingAngle={3} stroke="none" isAnimationActive={false}>
                    {projectPie.map((e) => <Cell key={e.name} fill={e.color} />)}
                  </Pie>
                  <Tooltip content={<ChartTip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-2 grid grid-cols-2 gap-2">
                {projectPie.map((p) => (
                  <div key={p.name} className="flex items-center gap-2 text-xs text-zinc-400">
                    <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />{p.name}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Recent clients */}
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-100">Recent Clients</h3>
            <button onClick={() => navigate("/clients")} className="text-xs font-medium text-violet-400 hover:text-violet-300">View all</button>
          </div>
          {recentClients.length === 0 ? (
            <div className="flex flex-col items-center py-8 text-center" data-testid="recent-clients-empty">
              <Users className="h-6 w-6 text-zinc-600" />
              <p className="mt-2 text-sm text-zinc-500">No clients yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentClients.map((c) => (
                <div key={c.id} className="flex items-center gap-3" data-testid={`recent-client-${c.id}`}>
                  <Avatar className="h-9 w-9 border border-white/10"><AvatarFallback className="bg-violet-600/20 text-violet-300">{c.name[0]}</AvatarFallback></Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-zinc-100">{c.name}</p>
                    <p className="truncate text-xs text-zinc-500">{c.contact || c.email || "—"}</p>
                  </div>
                  <span className="text-sm font-semibold text-violet-400">${Number(c.value || 0).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Upcoming tasks */}
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2"><Clock className="h-4 w-4 text-violet-400" /><h3 className="text-sm font-semibold text-zinc-100">Upcoming Tasks</h3></div>
            <button onClick={() => navigate("/tasks")} className="text-xs font-medium text-violet-400 hover:text-violet-300">View all</button>
          </div>
          {upcomingTasks.length === 0 ? (
            <div className="flex flex-col items-center py-8 text-center" data-testid="upcoming-tasks-empty">
              <CheckCircle2 className="h-6 w-6 text-zinc-600" />
              <p className="mt-2 text-sm text-zinc-500">No open tasks</p>
            </div>
          ) : (
            <div className="space-y-3">
              {upcomingTasks.map((t) => (
                <div key={t.id} className="flex items-start gap-3" data-testid={`upcoming-task-${t.id}`}>
                  <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${priorityDot[t.priority]}`} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-zinc-200">{t.title}</p>
                    <p className="text-xs text-zinc-500">{t.project_name || "No project"} · {fmtDue(t.due)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI agent activity */}
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <div className="mb-4 flex items-center gap-2"><Activity className="h-4 w-4 text-violet-400" /><h3 className="text-sm font-semibold text-zinc-100">AI Agent Activity</h3></div>
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
