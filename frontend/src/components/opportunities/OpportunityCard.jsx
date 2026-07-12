import { ArrowRight, Clock, Gauge, X } from "lucide-react";
import { AiIcon } from "@/components/ai/aiHelpers";
import { COLORS } from "@/components/opportunities/shared";

function ScoreRing({ score, color }) {
  const c = COLORS[color] || COLORS.green;
  const r = 18, circ = 2 * Math.PI * r;
  return (
    <div className="relative flex h-12 w-12 shrink-0 items-center justify-center">
      <svg className="h-12 w-12 -rotate-90" viewBox="0 0 44 44">
        <circle cx="22" cy="22" r={r} className="fill-none stroke-white/10" strokeWidth="4" />
        <circle cx="22" cy="22" r={r} className={`fill-none ${c.ring} transition-all`} strokeWidth="4"
          strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={circ - (score / 100) * circ} />
      </svg>
      <span className={`absolute text-xs font-bold ${c.text}`}>{score}</span>
    </div>
  );
}

export function OpportunityCard({ item, onRun, onDismiss, compact = false }) {
  const c = COLORS[item.color] || COLORS.green;
  return (
    <div data-testid="opportunity-card" data-priority={item.priority}
      className="group relative flex gap-4 rounded-2xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-violet-500/30 animate-fade-up">
      <ScoreRing score={item.score} color={item.color} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-violet-600/15 text-violet-300"><AiIcon name={item.icon} className="h-3.5 w-3.5" /></span>
          <p className="text-sm font-semibold text-zinc-100">{item.title}</p>
          <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${c.chip}`} data-testid="opportunity-priority">{item.priority}</span>
        </div>
        <p className="mt-1.5 text-sm leading-snug text-zinc-400">{item.explanation}</p>
        {!compact && (
          <p className="mt-1.5 text-xs leading-snug text-zinc-500"><span className="font-medium text-zinc-400">Why it matters: </span>{item.why}</p>
        )}
        <div className="mt-2.5 flex flex-wrap items-center gap-3 text-[11px] text-zinc-500">
          <span className="inline-flex items-center gap-1"><Clock className="h-3 w-3 text-emerald-400" /> Saves ~{item.time_saved}m</span>
          <span className="inline-flex items-center gap-1"><Gauge className="h-3 w-3 text-cyan-400" /> {item.confidence}% confidence</span>
          {item.entity?.project_name && <span className="truncate text-zinc-600">· {item.entity.project_name}</span>}
        </div>
        <div className="mt-3 flex items-center gap-2">
          <button onClick={() => onRun(item)} data-testid="opportunity-action-btn"
            className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-violet-500">
            {item.action.label} <ArrowRight className="h-3.5 w-3.5" />
          </button>
          {onDismiss && (
            <button onClick={() => onDismiss(item)} data-testid="opportunity-dismiss-btn"
              className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-zinc-900 px-2.5 py-1.5 text-xs font-medium text-zinc-500 transition-colors hover:text-zinc-200">
              <X className="h-3.5 w-3.5" /> Snooze
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
