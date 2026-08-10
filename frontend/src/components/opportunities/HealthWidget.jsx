import { Activity } from "lucide-react";

const GRADE_COLOR = (s) => (s >= 90 ? "text-emerald-400" : s >= 75 ? "text-violet-300" : s >= 55 ? "text-yellow-400" : "text-orange-400");
const barColor = (s) => (s >= 90 ? "bg-emerald-500" : s >= 75 ? "bg-violet-500" : s >= 55 ? "bg-yellow-500" : "bg-orange-500");

export function HealthWidget({ data, loading }) {
  if (loading || !data) {
    return <div className="flex h-64 items-center justify-center rounded-2xl border border-white/10 bg-zinc-950 text-zinc-600" data-testid="health-loading">…</div>;
  }

  if (data.has_workspace_data === false || data.score == null) {
    return (
      <div className="rounded-2xl border border-dashed border-white/10 bg-zinc-950 p-8 text-center" data-testid="workspace-health-empty">
        <Activity className="mx-auto h-8 w-8 text-zinc-600" />
        <p className="mt-3 text-sm font-semibold text-zinc-200">No health score yet</p>
        <p className="mx-auto mt-1 max-w-md text-xs text-zinc-500">
          {(data.top_reasons && data.top_reasons[0]) || "Add clients, projects or deals to start measuring workspace health."}
        </p>
      </div>
    );
  }

  const { score, grade, categories, top_reasons } = data;
  const r = 52, circ = 2 * Math.PI * r;
  return (
    <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5" data-testid="workspace-health">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500"><Activity className="h-3.5 w-3.5 text-violet-400" /> Workspace Health</div>
      <div className="mt-4 flex flex-col items-center gap-5 sm:flex-row sm:items-center">
        <div className="relative flex h-32 w-32 shrink-0 items-center justify-center">
          <svg className="h-32 w-32 -rotate-90" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r={r} className="fill-none stroke-white/10" strokeWidth="9" />
            <circle cx="60" cy="60" r={r} className={`fill-none ${barColor(score).replace("bg-", "stroke-")} transition-all duration-700`}
              strokeWidth="9" strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={circ - (score / 100) * circ} />
          </svg>
          <div className="absolute text-center">
            <p className={`text-3xl font-extrabold ${GRADE_COLOR(score)}`} data-testid="health-score">{score}%</p>
            <p className="text-[11px] text-zinc-500">{grade}</p>
          </div>
        </div>
        <div className="w-full flex-1 space-y-2">
          {(categories || []).map((c) => (
            <div key={c.name} data-testid={`health-cat-${c.name.replace(/\s/g, "-").toLowerCase()}`}>
              <div className="mb-0.5 flex items-center justify-between text-xs">
                <span className="text-zinc-400">{c.name}</span>
                <span className="font-medium text-zinc-300">{c.score}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
                <div className={`h-full rounded-full ${barColor(c.score)} transition-all duration-700`} style={{ width: `${c.score}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
      {top_reasons?.length > 0 && (
        <div className="mt-4 border-t border-white/10 pt-3">
          <p className="mb-1.5 text-xs font-medium text-zinc-500">What's holding the score back</p>
          <ul className="space-y-1">
            {top_reasons.map((reason, i) => (
              <li key={i} className="flex items-center gap-2 text-xs text-zinc-400"><span className="h-1 w-1 rounded-full bg-orange-400" /> {reason}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
