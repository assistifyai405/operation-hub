import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { FileStack, ArrowRight } from "lucide-react";
import { AiIcon } from "@/components/ai/aiHelpers";
import { useLocale } from "@/context/LocaleContext";
import { Section, relTime, DOC_BADGE } from "./execShared";

export function RecentDocuments({ documents }) {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const navigate = useNavigate();
  const all = [
    ...(documents.proposals || []), ...(documents.contracts || []),
    ...(documents.invoices || []), ...(documents.plans || []),
  ].filter((d) => d.updated_at).sort((a, b) => (b.updated_at > a.updated_at ? 1 : -1)).slice(0, 8);

  return (
    <Section title={t("dashboard.documents.title")} icon={FileStack} testid="documents-section">
      {all.length === 0 ? (
        <div className="rounded-2xl border border-white/10 bg-zinc-950 py-10 text-center text-sm text-zinc-500" data-testid="documents-empty">
          {t("dashboard.documents.empty")}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {all.map((d, i) => {
            const badge = DOC_BADGE[d.type] || DOC_BADGE.proposal;
            return (
              <motion.button key={`${d.type}-${d.id}`} onClick={() => navigate(d.link)} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
                className="flex flex-col rounded-2xl border border-white/10 bg-zinc-950 p-4 text-left transition-all hover:border-brand-500/40" data-testid={`document-card-${d.type}`}>
                <div className="flex items-center justify-between">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${badge.chip}`}>
                    <AiIcon name={badge.icon} className="h-3 w-3" /> {t(badge.labelKey)}
                  </span>
                  <ArrowRight className="h-3.5 w-3.5 text-zinc-600" />
                </div>
                <p className="mt-2 line-clamp-2 text-sm font-medium text-zinc-100">{d.title}</p>
                <p className="mt-0.5 truncate text-[11px] text-zinc-500">{d.project_name || ""}</p>
                <div className="mt-auto flex items-center gap-2 pt-2 text-[10px] text-zinc-600">
                  <span className="rounded bg-zinc-900 px-1.5 py-0.5 text-zinc-400">{d.status}</span>
                  {d.confidence ? <span className="text-brand-400">{d.confidence}%</span> : null}
                  <span className="ml-auto">{relTime(d.updated_at, locale, t)}</span>
                </div>
              </motion.button>
            );
          })}
        </div>
      )}
    </Section>
  );
}
