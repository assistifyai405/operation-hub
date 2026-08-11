import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { ListChecks, ArrowRight } from "lucide-react";
import { AiIcon } from "@/components/ai/aiHelpers";
import { useLocale } from "@/context/LocaleContext";
import { Section, PRIORITY_META, money } from "./execShared";

const ORDER = ["Critical", "High", "Medium", "Low"];

export function TodayPriorities({ priorities, total }) {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const navigate = useNavigate();
  if (!total) {
    return (
      <Section title={t("dashboard.priorities.title")} icon={ListChecks} testid="priorities-section">
        <div className="rounded-2xl border border-white/10 bg-zinc-950 py-10 text-center text-sm text-zinc-500" data-testid="priorities-empty">
          {t("dashboard.priorities.empty")}
        </div>
      </Section>
    );
  }
  return (
    <Section title={t("dashboard.priorities.title")} icon={ListChecks} testid="priorities-section"
      action={<span className="text-xs text-zinc-500">{t("dashboard.priorities.items", { count: total })}</span>}>
      <div className="space-y-2">
        {ORDER.map((lvl) => {
          const group = priorities[lvl.toLowerCase()];
          if (!group || group.count === 0) return null;
          const pm = PRIORITY_META[lvl];
          return (
            <div key={lvl} data-testid={`priority-group-${lvl}`}>
              <div className="mb-1.5 flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${pm.dot}`} />
                <span className="text-xs font-semibold text-zinc-300">{t(`dashboard.priority.${lvl.toLowerCase()}`)}</span>
                <span className="text-[11px] text-zinc-600">{group.count}</span>
              </div>
              <div className="space-y-1.5">
                {group.items.map((it) => (
                  <button key={it.id} onClick={() => it.action?.link && navigate(it.action.link)} data-testid={`priority-item-${it.type}`}
                    className="flex w-full items-center gap-3 rounded-xl border border-white/10 bg-zinc-950 px-3.5 py-2.5 text-left transition-all hover:border-brand-500/30">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-600/15 text-brand-300"><AiIcon name={it.icon} className="h-4 w-4" /></span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-zinc-100">{it.title}</p>
                      <p className="truncate text-xs text-zinc-500">{it.why}</p>
                    </div>
                    <div className="hidden shrink-0 text-right sm:block">
                      {it.revenue_impact ? <p className="text-xs font-semibold text-emerald-400" data-testid="priority-revenue-impact">≈{money(it.revenue_impact, locale)}</p> : <p className={`text-xs font-semibold ${pm.ring}`}>{t("dashboard.priorities.score", { score: it.score })}</p>}
                      <p className="text-[10px] text-zinc-500">{it.revenue_impact ? t("dashboard.priorities.revenueImpact") : t("dashboard.priorities.minutesSaved", { count: it.time_saved })}</p>
                    </div>
                    <ArrowRight className="h-4 w-4 shrink-0 text-zinc-600" />
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Section>
  );
}
