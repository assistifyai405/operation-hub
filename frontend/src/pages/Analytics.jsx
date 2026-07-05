import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import { TrendingUp, Users, DollarSign, Activity } from "lucide-react";
import { revenueData, trafficData, projectStatusData, agentActivityData } from "@/data/mock";

const ChartTip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-xs shadow-xl">
      <p className="mb-1 font-medium text-zinc-300">{label}</p>
      {payload.map((p) => <p key={p.name} style={{ color: p.color || p.fill }}>{p.name}: {p.value.toLocaleString()}</p>)}
    </div>
  );
};

const kpis = [
  { label: "MRR", value: "$46.7k", change: "+12%", icon: DollarSign },
  { label: "Conversion", value: "4.8%", change: "+0.6%", icon: TrendingUp },
  { label: "New Visitors", value: "16.7k", change: "+8.2%", icon: Users },
  { label: "Avg. Session", value: "4m 12s", change: "+18s", icon: Activity },
];

export default function Analytics() {
  return (
    <div className="space-y-6" data-testid="analytics-page">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {kpis.map((k) => (
          <div key={k.label} className="rounded-xl border border-white/10 bg-zinc-950 p-5">
            <div className="flex items-center justify-between">
              <k.icon className="h-5 w-5 text-violet-400" />
              <span className="text-xs font-medium text-emerald-400">{k.change}</span>
            </div>
            <p className="mt-4 text-2xl font-bold text-zinc-50">{k.value}</p>
            <p className="mt-1 text-sm text-zinc-500">{k.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <h3 className="mb-4 text-sm font-semibold text-zinc-100">Revenue vs Expenses</h3>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={revenueData}>
              <defs>
                <linearGradient id="a1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.4} /><stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} /></linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="month" stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip content={<ChartTip />} />
              <Area type="monotone" dataKey="revenue" stroke="#8b5cf6" strokeWidth={2} fill="url(#a1)" isAnimationActive={false} />
              <Line type="monotone" dataKey="expenses" stroke="#f87171" strokeWidth={2} dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <h3 className="mb-4 text-sm font-semibold text-zinc-100">Traffic by Source</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={trafficData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
              <XAxis type="number" stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="source" stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} width={70} />
              <Tooltip content={<ChartTip />} cursor={{ fill: "rgba(139,92,246,0.08)" }} />
              <Bar dataKey="visits" fill="#8b5cf6" radius={[0, 4, 4, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <h3 className="mb-4 text-sm font-semibold text-zinc-100">AI Agent Runs</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={agentActivityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="day" stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTip />} />
              <Line type="monotone" dataKey="runs" stroke="#22d3ee" strokeWidth={2} dot={{ fill: "#22d3ee", r: 3 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-white/10 bg-zinc-950 p-5">
          <h3 className="mb-4 text-sm font-semibold text-zinc-100">Project Distribution</h3>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={projectStatusData} dataKey="value" outerRadius={90} stroke="none" label isAnimationActive={false}>
                {projectStatusData.map((e) => <Cell key={e.name} fill={e.color} />)}
              </Pie>
              <Tooltip content={<ChartTip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
