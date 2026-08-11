import { useState } from "react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { Area, AreaChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { BarChart3 } from "lucide-react";
import { useLocale } from "@/context/LocaleContext";
import { money } from "./execShared";

export function BusinessPerformanceChart({ trends, workspaceEmpty }) {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const [active, setActive] = useState("revenue");
  const metrics = [
    { k: "revenue", label: t("dashboard.performance.revenue"), color: "#34d399", fmt: (v) => money(v, locale) },
    { k: "pipeline", label: t("dashboard.performance.pipeline"), color: "#8b5cf6", fmt: (v) => money(v, locale) },
    { k: "hours_saved", label: t("dashboard.performance.hoursSaved"), color: "#22d3ee", fmt: (v) => `${v}h` },
    { k: "deals", label: t("dashboard.performance.deals"), color: "#f59e0b", fmt: (v) => `${v}` },
    { k: "clients", label: t("dashboard.performance.clients"), color: "#f472b6", fmt: (v) => `${v}` },
    { k: "automations", label: t("dashboard.performance.automations"), color: "#86EFAC", fmt: (v) => `${v}` },
    { k: "ai_activity", label: t("dashboard.performance.aiActivity"), color: "#60a5fa", fmt: (v) => `${v}` },
  ];
  const m = metrics.find((x) => x.k === active);
  const data = (trends?.labels || []).map((label, i) => ({ label, value: (trends?.series?.[active] || [])[i] || 0 }));
  const total = data.reduce((s, d) => s + d.value, 0);
  const empty = Boolean(workspaceEmpty) || data.every((d) => !d.value);

  return (
    <div className="rounded-2xl border border-white/10 bg-zinc-950/80 p-5 backdrop-blur-xl" data-testid="performance-chart">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-zinc-100"><BarChart3 className="h-4 w-4 text-brand-400" /> {t("dashboard.performance.title")}</h2>
        <span className="text-xs text-zinc-500">{t("dashboard.performance.lastWeeks", { count: 8 })}</span>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5" data-testid="chart-metric-switcher">
        {metrics.map((x) => (
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
          <p className="mt-3 text-sm font-medium text-zinc-300">{t("dashboard.performance.empty")}</p>
          <p className="mt-1 max-w-sm text-xs text-zinc-500">{t("dashboard.performance.emptyHint")}</p>
        </div>
      ) : (
        <>
          <div className="mt-4 flex items-baseline gap-2">
            <p className="text-2xl font-bold text-zinc-50">{m.fmt(total)}</p>
            <span className="text-xs text-zinc-500">{t("dashboard.performance.totalMetric", { metric: m.label })}</span>
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
