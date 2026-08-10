import { motion } from "framer-motion";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { TrendingUp, TrendingDown, Info, HeartPulse, DollarSign, Clock, Wallet } from "lucide-react";
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "@/components/ui/tooltip";
import { useCountUp } from "./useCountUp";
import { healthTone } from "./execShared";

const ICONS = { health: HeartPulse, pipeline: DollarSign, hours_saved: Clock, revenue_month: Wallet };

function Spark({ data, color }) {
  const d = (data || []).map((v, i) => ({ i, v }));
  return (
    <ResponsiveContainer width="100%" height={40} minHeight={40}>
      <AreaChart data={d} margin={{ top: 4, bottom: 0, left: 0, right: 0 }}>
        <defs>
          <linearGradient id={`sp-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={2} fill={`url(#sp-${color})`} isAnimationActive />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function KpiCard({ id, title, kpi, format, color, tooltip, delay = 0 }) {
  const Icon = ICONS[id];
  const empty = Boolean(kpi?.empty) || kpi?.value === null || kpi?.value === undefined;
  const animated = useCountUp(empty ? 0 : kpi.value);
  const isHealth = id === "health";
  const tone = isHealth && !empty ? healthTone(kpi.value) : null;
  const display = empty ? "—" : format(isHealth ? Math.round(animated) : animated);
  const change = empty ? null : kpi.change_pct;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay, duration: 0.45 }}
      className="relative overflow-hidden rounded-2xl border border-white/10 bg-zinc-950/80 p-4 backdrop-blur-xl"
      data-testid={`kpi-${id}`}
    >
      <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full opacity-[0.12] blur-2xl" style={{ background: color }} />
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-xs font-medium text-zinc-400">
          <Icon className="h-3.5 w-3.5" style={{ color }} /> {title}
        </span>
        <TooltipProvider delayDuration={150}>
          <Tooltip>
            <TooltipTrigger asChild><button data-testid={`kpi-${id}-info`} className="text-zinc-600 hover:text-zinc-300"><Info className="h-3.5 w-3.5" /></button></TooltipTrigger>
            <TooltipContent className="max-w-xs border-white/10 bg-zinc-900 text-xs text-zinc-200">{tooltip}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <div className="mt-2 flex items-end justify-between gap-2">
        <div>
          <p className={`text-2xl font-bold tracking-tight ${empty ? "text-zinc-500" : isHealth ? tone.text : "text-zinc-50"}`} data-testid={`kpi-${id}-value`}>{display}</p>
          <div className="mt-0.5 flex items-center gap-1.5 text-[11px]">
            {empty ? (
              <span className="text-zinc-600" data-testid={`kpi-${id}-empty`}>No data yet</span>
            ) : isHealth ? (
              <span className={`rounded-full px-1.5 py-0.5 font-medium ${tone.chip}`}>{kpi.grade}</span>
            ) : change === null || change === undefined ? (
              <span className="text-zinc-600">no prior data</span>
            ) : (
              <span className={`inline-flex items-center gap-0.5 font-medium ${change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {change >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}{change > 0 ? "+" : ""}{change}%
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-2 h-10">
        {empty ? (
          <div className="flex h-10 items-center text-[11px] text-zinc-600">Add workspace activity to populate this metric.</div>
        ) : isHealth ? (
          <div className="flex h-10 items-end gap-1" data-testid="kpi-health-bars">
            {(kpi.categories || []).map((c) => {
              const t = healthTone(c.score);
              return <div key={c.name} className="flex-1 rounded-t" style={{ height: `${Math.max(12, c.score)}%`, background: t.bar, opacity: 0.85 }} title={`${c.name}: ${c.score}`} />;
            })}
          </div>
        ) : (
          <Spark data={kpi.spark} color={color} />
        )}
      </div>
    </motion.div>
  );
}
