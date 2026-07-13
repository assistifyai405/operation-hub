import { motion } from "framer-motion";
import { DollarSign, TrendingUp, TrendingDown, ArrowUpRight } from "lucide-react";
import { Section, money } from "./execShared";

export function RevenueSnapshot({ revenue }) {
  const g = revenue.growth_pct;
  const cards = [
    { label: "Pipeline Value", value: money(revenue.pipeline_value), tone: "text-violet-400" },
    { label: "Expected (weighted)", value: money(revenue.expected_monthly), tone: "text-cyan-400" },
    { label: "Outstanding Invoices", value: money(revenue.outstanding), tone: "text-amber-400" },
    { label: "Closed Revenue", value: money(revenue.closed_revenue), tone: "text-emerald-400" },
    { label: "Average Deal Size", value: money(revenue.avg_deal_size), tone: "text-zinc-100" },
    {
      label: "Growth vs last 30d",
      value: g === null || g === undefined ? "—" : `${g > 0 ? "+" : ""}${g}%`,
      tone: g > 0 ? "text-emerald-400" : g < 0 ? "text-red-400" : "text-zinc-400",
      icon: g > 0 ? TrendingUp : g < 0 ? TrendingDown : null,
    },
  ];
  return (
    <Section title="Revenue Snapshot" icon={DollarSign} testid="revenue-section">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {cards.map((c, i) => (
          <motion.div key={c.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
            className="rounded-2xl border border-white/10 bg-zinc-950 p-4" data-testid={`revenue-${c.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
            <p className="text-[11px] text-zinc-500">{c.label}</p>
            <p className={`mt-1.5 flex items-center gap-1 text-xl font-bold tracking-tight ${c.tone}`}>
              {c.icon && <c.icon className="h-4 w-4" />} {c.value}
            </p>
          </motion.div>
        ))}
      </div>
    </Section>
  );
}
