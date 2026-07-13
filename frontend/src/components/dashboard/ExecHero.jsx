import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Clock, Gauge, TrendingDown, ArrowRight } from "lucide-react";
import { AiIcon } from "@/components/ai/aiHelpers";
import { money, PRIORITY_META } from "./execShared";

const card = (i) => ({ initial: { opacity: 0, y: 14 }, animate: { opacity: 1, y: 0 }, transition: { delay: i * 0.06, duration: 0.4 } });

export function ExecHero({ hero, userName }) {
  const navigate = useNavigate();
  const tp = hero.top_priority;
  const metrics = [
    { label: "Revenue at risk", value: money(hero.revenue_at_risk), icon: TrendingDown, tone: "text-red-400", testid: "hero-revenue-risk" },
    { label: "Hours saved this week", value: `${hero.hours_saved_week}h`, icon: Clock, tone: "text-emerald-400", testid: "hero-hours-saved" },
    { label: "AI confidence", value: `${hero.ai_confidence}%`, icon: Gauge, tone: "text-violet-400", testid: "hero-ai-confidence" },
  ];

  return (
    <div className="space-y-4" data-testid="exec-hero">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-zinc-50 sm:text-4xl">
          {hero.greeting}{userName ? `, ${userName}` : ""}
        </h1>
        <p className="mt-1 text-sm text-zinc-400">Here's what your business needs today.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Biggest priority + brief */}
        <motion.div {...card(0)} className="rounded-2xl border border-violet-500/25 bg-gradient-to-br from-violet-600/[0.12] to-transparent p-5 lg:col-span-2" data-testid="hero-priority">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-violet-300">
            <AlertTriangle className="h-3.5 w-3.5" /> Biggest priority today
          </div>
          {tp ? (
            <>
              <div className="mt-2 flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-600/20 text-violet-300"><AiIcon name={tp.icon} className="h-5 w-5" /></span>
                <div className="min-w-0">
                  <p className="text-lg font-bold text-zinc-50">{tp.title}</p>
                  <p className="mt-0.5 text-sm text-zinc-400">{tp.why}</p>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${(PRIORITY_META[tp.priority] || PRIORITY_META.Medium).chip}`}>{tp.priority}</span>
                <span className="text-xs text-zinc-500">{tp.confidence}% confidence</span>
                {tp.action?.link && (
                  <button onClick={() => navigate(tp.action.link)} data-testid="hero-priority-action" className="ml-auto inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white transition-all hover:bg-violet-500">
                    {tp.action.label} <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </>
          ) : (
            <p className="mt-3 text-sm text-zinc-300">Your workspace is in great shape — nothing urgent right now. 🎉</p>
          )}
          {hero.brief_lines?.length > 0 && (
            <div className="mt-4 border-t border-white/10 pt-3">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Today's AI brief</p>
              <div className="grid gap-1.5 sm:grid-cols-2">
                {hero.brief_lines.map((l, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-zinc-300" data-testid="hero-brief-line">
                    <AiIcon name={l.icon} className="h-3.5 w-3.5 text-violet-400" /> {l.text}
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        {/* Metric stack */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:grid-cols-1">
          {metrics.map((m, i) => (
            <motion.div key={m.label} {...card(i + 1)} className="rounded-2xl border border-white/10 bg-zinc-950 p-4" data-testid={m.testid}>
              <div className="flex items-center justify-between">
                <p className="text-xs text-zinc-500">{m.label}</p>
                <m.icon className={`h-4 w-4 ${m.tone}`} />
              </div>
              <p className={`mt-1.5 text-2xl font-bold tracking-tight ${m.tone}`}>{m.value}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
