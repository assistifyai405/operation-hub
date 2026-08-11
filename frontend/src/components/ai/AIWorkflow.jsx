import { useEffect, useState } from "react";
import { Check, Loader2, Sparkles } from "lucide-react";

/**
 * Premium live AI workflow. Reveals contextual stages sequentially with checkmarks;
 * the final stage keeps working until `running` flips to false, then all complete.
 * Cosmetic staging over a single backend request — never a bare "Loading...".
 */
export function AIWorkflow({ steps, running, title = "Assistify is working" }) {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (!running) {
      setIdx(steps.length);
      return;
    }
    setIdx(0);
    const timers = [];
    // advance through all but the last stage; the last stays active until the request returns
    for (let i = 0; i < steps.length - 1; i++) {
      timers.push(setTimeout(() => setIdx((c) => Math.max(c, i + 1)), (i + 1) * 850));
    }
    return () => timers.forEach(clearTimeout);
  }, [running, steps.length]);

  const done = idx >= steps.length;

  return (
    <div data-testid="ai-workflow" className="rounded-xl border border-brand-500/20 bg-brand-500/[0.04] p-5">
      <div className="mb-4 flex items-center gap-2">
        <span className="relative flex h-6 w-6 items-center justify-center rounded-lg bg-brand-600/20">
          <Sparkles className="h-3.5 w-3.5 text-brand-300" />
          {!done && <span className="absolute inset-0 animate-ping rounded-lg bg-brand-500/20" />}
        </span>
        <p className="text-sm font-semibold text-zinc-100">{done ? "Done" : title}</p>
      </div>
      <div className="space-y-2.5">
        {steps.map((s, i) => {
          const complete = i < idx;
          const active = i === idx && !done;
          return (
            <div key={i} className={`flex items-center gap-3 transition-all duration-300 ${i > idx ? "opacity-40" : "opacity-100"}`}>
              <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${complete ? "border-emerald-500/40 bg-emerald-500/15" : active ? "border-brand-500/50 bg-brand-500/15" : "border-white/10 bg-zinc-800"}`}>
                {complete ? <Check className="h-3 w-3 text-emerald-400 ai-pop" /> : active ? <Loader2 className="h-3 w-3 animate-spin text-brand-300" /> : <span className="h-1.5 w-1.5 rounded-full bg-zinc-600" />}
              </span>
              <span className={`text-sm ${complete ? "text-zinc-400" : active ? "text-zinc-100" : "text-zinc-500"}`}>{s}</span>
            </div>
          );
        })}
      </div>
      {!done && (
        <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-zinc-800">
          <div className="h-full rounded-full bg-gradient-to-r from-brand-500 to-cyan-400 ai-progress" />
        </div>
      )}
    </div>
  );
}
