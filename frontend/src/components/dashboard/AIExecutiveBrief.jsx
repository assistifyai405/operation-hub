import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles, ArrowRight, CheckCircle2 } from "lucide-react";
import { AiIcon } from "@/components/ai/aiHelpers";
import { money } from "./execShared";

const DOT = { Critical: "bg-red-500", High: "bg-orange-500", Medium: "bg-amber-500", Low: "bg-emerald-500", positive: "bg-emerald-500", risk: "bg-red-500" };

export function AIExecutiveBrief({ insights, hero, health, workspaceEmpty }) {
  const navigate = useNavigate();

  const lines = [];
  if (!workspaceEmpty && health?.score != null && health.score >= 75) {
    lines.push({ id: "pos", tone: "positive", title: `Business health is strong at ${health.score}/100`, why: health.grade, action: null });
  }
  if (!workspaceEmpty && hero?.revenue_at_risk > 0) {
    lines.push({ id: "risk", tone: "risk", title: `${money(hero.revenue_at_risk)} at risk`, why: "Across unpaid invoices and stalled open deals.", confidence: null, action: { label: "Review", link: "/pipeline" } });
  }
  (insights || []).slice(0, 4).forEach((it) => {
    lines.push({ id: it.id, tone: it.priority, icon: it.icon, title: it.title, why: it.why, confidence: it.confidence, impact: it.revenue_impact, action: it.action });
  });

  return (
    <div className="flex h-full flex-col rounded-2xl border border-white/10 bg-zinc-950/80 p-5 backdrop-blur-xl" data-testid="ai-executive-brief">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-zinc-100"><Sparkles className="h-4 w-4 text-violet-400" /> AI Executive Brief</h2>
      <div className="mt-3 flex-1 space-y-2.5">
        {lines.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center" data-testid="brief-empty">
            <CheckCircle2 className="h-8 w-8 text-emerald-500" />
            <p className="mt-2 text-sm text-zinc-300">
              {workspaceEmpty ? "No workspace insights yet." : "All clear — nothing needs your attention."}
            </p>
            {workspaceEmpty && (
              <p className="mt-1 max-w-xs text-xs text-zinc-500">Add clients, projects or deals and Assistify will surface real recommendations here.</p>
            )}
          </div>
        ) : lines.map((l, i) => (
          <motion.div key={l.id} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }}
            className="flex items-start gap-3 rounded-xl border border-white/5 bg-zinc-900/40 p-3" data-testid={`brief-line-${l.tone}`}>
            <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${DOT[l.tone] || "bg-zinc-500"}`} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-zinc-100">{l.title}</p>
              <p className="mt-0.5 line-clamp-2 text-xs text-zinc-500">{l.why}</p>
              {(l.confidence || l.action || l.impact) && (
                <div className="mt-1.5 flex items-center gap-2">
                  {l.impact ? <span className="rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-medium text-emerald-300" data-testid={`brief-impact-${l.id}`}>≈{money(l.impact)}</span> : null}
                  {l.confidence ? <span className="text-[10px] text-zinc-600">{l.confidence}% confidence</span> : null}
                  {l.action?.link && (
                    <button onClick={() => navigate(l.action.link)} data-testid={`brief-action-${l.id}`}
                      className="ml-auto inline-flex items-center gap-1 rounded-lg bg-violet-600/90 px-2.5 py-1 text-[11px] font-semibold text-white transition-all hover:bg-violet-500">
                      {l.action.label} <ArrowRight className="h-3 w-3" />
                    </button>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
