import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { DollarSign, TrendingUp, TrendingDown, ArrowUpRight } from "lucide-react";
import { useLocale } from "@/context/LocaleContext";
import { Section, money } from "./execShared";

export function RevenueSnapshot({ revenue }) {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const g = revenue.growth_pct;
  const cards = [
    { label: t("dashboard.revenue.pipelineValue"), value: money(revenue.pipeline_value, locale), tone: "text-brand-400" },
    { label: t("dashboard.revenue.expectedWeighted"), value: money(revenue.expected_monthly, locale), tone: "text-cyan-400" },
    { label: t("dashboard.revenue.outstandingInvoices"), value: money(revenue.outstanding, locale), tone: "text-amber-400" },
    { label: t("dashboard.revenue.closedRevenue"), value: money(revenue.closed_revenue, locale), tone: "text-emerald-400" },
    { label: t("dashboard.revenue.averageDealSize"), value: money(revenue.avg_deal_size, locale), tone: "text-zinc-100" },
    {
      label: t("dashboard.revenue.growth"),
      value: g === null || g === undefined ? "—" : `${g > 0 ? "+" : ""}${g}%`,
      tone: g > 0 ? "text-emerald-400" : g < 0 ? "text-red-400" : "text-zinc-400",
      icon: g > 0 ? TrendingUp : g < 0 ? TrendingDown : null,
    },
  ];
  return (
    <Section title={t("dashboard.revenue.title")} icon={DollarSign} testid="revenue-section">
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
