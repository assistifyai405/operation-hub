import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  TrendingUp, DollarSign, Target, Trophy, Percent, CalendarClock, Sparkles, ArrowRight, Gauge,
} from "lucide-react";
import { crmApi } from "@/lib/api";
import { fmtMoney, SCORE_COLOR } from "@/components/crm/crmShared";
import { useLocale } from "@/context/LocaleContext";

const Kpi = ({ icon: Icon, label, value, accent, testid, onClick }) => (
  <button onClick={onClick} data-testid={testid}
    className="rounded-xl border border-white/10 bg-zinc-950 p-3.5 text-left transition-all hover:border-brand-500/40">
    <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${accent}`}><Icon className="h-4 w-4" /></div>
    <p className="mt-2 text-xl font-extrabold tracking-tight text-zinc-50">{value}</p>
    <p className="text-[11px] text-zinc-500">{label}</p>
  </button>
);

export default function DashboardSales() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const navigate = useNavigate();
  const [m, setM] = useState(null);
  useEffect(() => { crmApi.salesMetrics().then(setM).catch(() => setM(null)); }, []);
  if (!m) return null;

  return (
    <div className="space-y-4" data-testid="dashboard-sales">
      <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500"><TrendingUp className="h-3.5 w-3.5 text-brand-400" /> {t("crm.sales.title")}</p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Kpi testid="sales-pipeline-value" icon={DollarSign} label={t("crm.sales.pipelineValue")} accent="bg-emerald-500/15 text-emerald-300" value={fmtMoney(m.pipeline_value, locale)} onClick={() => navigate("/pipeline")} />
        <Kpi testid="sales-closing-week" icon={CalendarClock} label={t("crm.sales.closingWeek")} accent="bg-amber-500/15 text-amber-300" value={m.closing_this_week.length} onClick={() => navigate("/pipeline")} />
        <Kpi testid="sales-attention" icon={Target} label={t("crm.sales.needAttention")} accent="bg-orange-500/15 text-orange-300" value={m.leads_needing_attention.length} onClick={() => navigate("/pipeline")} />
        <Kpi testid="sales-win-rate" icon={Trophy} label={t("crm.sales.winRate")} accent="bg-brand-500/15 text-brand-300" value={`${m.win_rate}%`} onClick={() => navigate("/pipeline")} />
        <Kpi testid="sales-avg-deal" icon={Gauge} label={t("crm.sales.averageDeal")} accent="bg-cyan-500/15 text-cyan-300" value={fmtMoney(m.avg_deal_size, locale)} onClick={() => navigate("/pipeline")} />
        <Kpi testid="sales-conversion" icon={Percent} label={t("crm.sales.conversion")} accent="bg-blue-500/15 text-blue-300" value={`${m.conversion_rate}%`} onClick={() => navigate("/pipeline")} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* AI Sales insights */}
        <div className="rounded-2xl border border-brand-500/20 bg-brand-500/[0.05] p-4" data-testid="sales-insights">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-brand-300"><Sparkles className="h-3.5 w-3.5" /> {t("crm.sales.insights")}</p>
          <ul className="mt-2.5 space-y-2">
            {m.ai_insights.map((t, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-zinc-200"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" /> {t}</li>
            ))}
          </ul>
        </div>
        {/* Leads needing attention */}
        <div className="rounded-2xl border border-white/10 bg-zinc-950 p-4">
          <div className="mb-2.5 flex items-center justify-between">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500"><Target className="h-3.5 w-3.5 text-orange-400" /> {t("crm.sales.leadsNeedingAttention")}</p>
            <button onClick={() => navigate("/pipeline")} className="inline-flex items-center gap-1 text-xs font-medium text-brand-300 hover:text-brand-200">{t("nav.pipeline")} <ArrowRight className="h-3.5 w-3.5" /></button>
          </div>
          {m.leads_needing_attention.length === 0 ? (
            <p className="text-xs text-zinc-500">{t("crm.sales.noneStalled")}</p>
          ) : (
            <div className="space-y-2">
              {m.leads_needing_attention.slice(0, 4).map((l) => (
                <button key={l.id} onClick={() => navigate("/pipeline")} className="flex w-full items-center justify-between gap-2 rounded-lg border border-white/10 bg-zinc-900/40 px-3 py-2 text-left transition-all hover:border-brand-500/30">
                  <div className="min-w-0"><p className="truncate text-sm text-zinc-200">{l.title}</p><p className="text-xs text-zinc-500">{l.stage} · {l.client_name || "—"}</p></div>
                  <div className="flex shrink-0 items-center gap-2"><span className="text-sm font-bold text-emerald-300">{fmtMoney(l.value, locale)}</span><span className={`text-xs font-bold ${SCORE_COLOR(l.score).split(" ")[0]}`}>{l.score}</span></div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
