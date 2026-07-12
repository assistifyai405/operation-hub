import { useNavigate } from "react-router-dom";
import { Sparkles, Clock, ArrowRight } from "lucide-react";
import { AiIcon, fmtDuration } from "@/components/ai/aiHelpers";

export function DailyBrief({ data, loading }) {
  const navigate = useNavigate();
  if (loading || !data) {
    return <div className="flex h-48 items-center justify-center rounded-2xl border border-white/10 bg-zinc-950 text-zinc-600" data-testid="brief-loading">…</div>;
  }
  return (
    <div className="relative overflow-hidden rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-600/[0.12] to-zinc-950 p-5" data-testid="daily-brief">
      <div className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-violet-600/20 blur-3xl" />
      <div className="relative">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-violet-300"><Sparkles className="h-3.5 w-3.5" /> Today's AI Brief</div>
        <p className="mt-2 text-lg font-bold text-zinc-50" data-testid="brief-greeting">{data.greeting}.</p>
        <p className="text-sm text-zinc-400">Here's what I found across your workspace:</p>
        <ul className="mt-3 space-y-2">
          {data.lines.map((l, i) => (
            <li key={i} className="flex items-center gap-2.5 text-sm text-zinc-200 animate-fade-up" style={{ animationDelay: `${i * 60}ms` }} data-testid="brief-line">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-violet-600/15 text-violet-300"><AiIcon name={l.icon} className="h-3.5 w-3.5" /></span>
              {l.text}
            </li>
          ))}
        </ul>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-3">
          <span className="inline-flex items-center gap-1.5 text-sm text-zinc-300"><Clock className="h-4 w-4 text-emerald-400" /> Est. <b className="text-emerald-300">{fmtDuration(data.total_time_saved)}</b> can be saved today</span>
          {data.total > 0 && (
            <button onClick={() => navigate("/opportunities")} data-testid="brief-view-all" className="inline-flex items-center gap-1 text-sm font-medium text-violet-300 transition-colors hover:text-violet-200">
              View all {data.total} <ArrowRight className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
