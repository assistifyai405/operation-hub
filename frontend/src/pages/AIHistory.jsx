import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Clock, Sparkles, ArrowLeft } from "lucide-react";
import { aiApi } from "@/lib/api";
import { AiIcon, fmtDuration, relTime } from "@/components/ai/aiHelpers";

export default function AIHistory() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    aiApi.history().then(setData).catch(() => setData({ groups: [], total: 0, total_time_saved: 0 })).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center py-32 text-zinc-500" data-testid="ai-history-loading"><Loader2 className="h-7 w-7 animate-spin" /></div>;

  const empty = !data || data.total === 0;

  return (
    <div className="mx-auto max-w-3xl space-y-6" data-testid="ai-history-page">
      <div>
        <button onClick={() => navigate("/dashboard")} className="mb-3 inline-flex items-center gap-1.5 text-sm text-zinc-400 transition-colors hover:text-zinc-100"><ArrowLeft className="h-4 w-4" /> Back to dashboard</button>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-zinc-50"><Sparkles className="h-6 w-6 text-violet-400" /> AI History</h1>
            <p className="mt-1 text-sm text-zinc-400">Everything Assistify has done for you — and why.</p>
          </div>
          <div className="rounded-xl border border-violet-500/20 bg-violet-500/[0.06] px-4 py-2.5 text-right">
            <p className="flex items-center justify-end gap-1.5 text-xs text-zinc-500"><Clock className="h-3.5 w-3.5" /> Total time saved</p>
            <p className="text-xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-violet-300 to-cyan-300" data-testid="ai-history-total-saved">{fmtDuration(data.total_time_saved)}</p>
          </div>
        </div>
      </div>

      {empty ? (
        <div className="rounded-2xl border border-white/10 bg-zinc-950 py-16 text-center" data-testid="ai-history-empty">
          <Sparkles className="mx-auto h-8 w-8 text-zinc-700" />
          <p className="mt-3 text-sm font-medium text-zinc-300">No AI activity yet</p>
          <p className="mx-auto mt-1 max-w-sm text-xs text-zinc-500">Generate a proposal, contract, invoice or plan and it'll appear here with the time it saved you.</p>
        </div>
      ) : (
        data.groups.map((g) => (
          <div key={g.label} data-testid={`ai-history-group-${g.label.replace(/\s/g, "-").toLowerCase()}`}>
            <p className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">{g.label}</p>
            <div className="space-y-2">
              {g.items.map((a) => (
                <div key={a.id} className="flex items-start gap-3 rounded-xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-violet-500/30" data-testid="ai-history-item">
                  <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-violet-600/15 text-violet-300"><AiIcon name={a.icon} className="h-4 w-4" /></span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-semibold text-zinc-100">{a.title}</p>
                      <span className="shrink-0 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-400">+{a.time_saved}m saved</span>
                    </div>
                    <p className="mt-1 text-sm leading-snug text-zinc-400">{a.explanation}</p>
                    <p className="mt-1.5 text-xs text-zinc-600">{a.source_page} · {relTime(a.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
