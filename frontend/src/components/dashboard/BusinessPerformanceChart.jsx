import { useState } from "react";
import { motion } from "framer-motion";
import { Area, AreaChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { BarChart3 } from "lucide-react";
import { money } from "./execShared";

const METRICS = [
  { k: "revenue", label: "Revenue", color: "#34d399", fmt: money },
  { k: "pipeline", label: "Pipeline", color: "#8b5cf6", fmt: money },
  { k: "hours_saved", label: "Hours Saved", color: "#22d3ee", fmt: (v) => `${v}h` },
  { k: "deals", label: "Deals", color: "#f59e0b", fmt: (v) => `${v}` },
  { k: "clients", label: "Clients", color: "#f472b6", fmt: (v) => `${v}` },
  { k: "automations", label: "Automations", color: "#86EFAC", fmt: (v) => `${v}` },
  { k: "ai_activity", label: "AI Activity", color: "#60a5fa", fmt: (v) => `${v}` },
];

export function BusinessPerformanceChart({ trends, workspaceEmpty }) {
  const [active, setActive] = useState("revenue");
  const m = METRICS.find((x) => x.k === active);
  const data = (trends?.labels || []).map((label, i) => ({ label, value: (trends?.series?.[active] || [])[i] || 0 }));
  const total = data.reduce((s, d) => s + d.value, 0);
  const empty = Boolean(workspaceEmpty) || data.every((d) => !d.value);

  return (
    <div className="rounded-2xl border border-white/10 bg-zinc-950/80 p-5 backdrop-blur-xl" data-testid="performance-chart">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-zinc-100"><BarChart3 className="h-4 w-4 text-brand-400" /> Business Performance</h2>
        <span className="text-xs text-zinc-500">Last 8 weeks</span>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5" data-testid="chart-metric-switcher">
        {METRICS.map((x) => (
          <button key={x.k} onClick={() => setActive(x.k)} data-testid={`chart-metric-${x.k}`}
            className={`rounded-full border px-2.5 py-1 text-[11px] font-medium transition-all ${active === x.k ? "border-transparent text-black" : "border-white/10 bg-zinc-900 text-zinc-400 hover:text-zinc-200"}`}
            style={active === x.k ? { background: x.color } : {}}>
            {x.label}
          </button>
        ))}
      </div>

      {empty ? (
        <div className="mt-8 flex flex-col items-center justify-center py-16 text-center" data-testid="performance-empty">
          <BarChart3 className="h-8 w-8 text-zinc-600" />
          <p className="mt-3 text-sm font-medium text-zinc-300">No performance data yet</p>
          <p className="mt-1 max-w-sm text-xs text-zinc-500">Once you add clients, deals, invoices or AI activity, trends will appear here.</p>
        </div>
      ) : (
        <>
          <div className="mt-4 flex items-baseline gap-2">
            <p className="text-2xl font-bold text-zinc-50">{m.fmt(total)}</p>
            <span className="text-xs text-zinc-500">total · {m.label.toLowerCase()}</span>
          </div>

          <div className="mt-2 h-56" data-testid={`chart-canvas-${active}`}>
            <ResponsiveContainer width="100%" height="100%" minHeight={200}>
              <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                <defs>
                  <linearGradient id="pcg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={m.color} stopOpacity={0.4} />
                    <stop offset="100%" stopColor={m.color} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false} width={48} />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, fontSize: 12 }}
                  labelStyle={{ color: "#a1a1aa" }} formatter={(v) => [m.fmt(v), m.label]} />
                <Area type="monotone" dataKey="value" stroke={m.color} strokeWidth={2.5} fill="url(#pcg)" isAnimationActive animationDuration={600} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
