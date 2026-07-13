import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Lightbulb, ArrowRight } from "lucide-react";
import { AiIcon } from "@/components/ai/aiHelpers";
import { Section, PRIORITY_META } from "./execShared";

export function ExecInsights({ insights }) {
  const navigate = useNavigate();
  if (!insights?.length) {
    return (
      <Section title="AI Executive Insights" icon={Lightbulb} testid="insights-section">
        <div className="rounded-2xl border border-white/10 bg-zinc-950 py-10 text-center text-sm text-zinc-500" data-testid="insights-empty">
          No pressing insights — Assistify will surface opportunities here as they appear.
        </div>
      </Section>
    );
  }
  return (
    <Section title="AI Executive Insights" icon={Lightbulb} testid="insights-section">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {insights.map((it, i) => {
          const pm = PRIORITY_META[it.priority] || PRIORITY_META.Medium;
          return (
            <motion.div key={it.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
              className="flex flex-col rounded-2xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-violet-500/30" data-testid={`insight-card-${it.type}`}>
              <div className="flex items-start gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-600/15 text-violet-300"><AiIcon name={it.icon} className="h-4 w-4" /></span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`h-1.5 w-1.5 rounded-full ${pm.dot}`} />
                    <p className="truncate text-sm font-semibold text-zinc-100">{it.title}</p>
                  </div>
                  <p className="mt-1 text-xs text-zinc-400">{it.explanation}</p>
                </div>
              </div>
              <p className="mt-2 rounded-lg bg-zinc-900/60 px-2.5 py-1.5 text-[11px] leading-relaxed text-zinc-400"><span className="font-medium text-zinc-300">Why it matters: </span>{it.why}</p>
              <div className="mt-3 flex items-center gap-2 text-[11px] text-zinc-500">
                <span className={`rounded-full border px-2 py-0.5 font-medium ${pm.chip}`}>{it.priority}</span>
                <span>{it.confidence}% confidence</span>
                <span className="text-emerald-500/80">~{it.time_saved}m saved</span>
                {it.action?.link && (
                  <button onClick={() => navigate(it.action.link)} data-testid={`insight-action-${it.type}`} className="ml-auto inline-flex items-center gap-1 rounded-lg bg-violet-600 px-2.5 py-1 text-[11px] font-semibold text-white transition-all hover:bg-violet-500">
                    {it.action.label} <ArrowRight className="h-3 w-3" />
                  </button>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </Section>
  );
}
