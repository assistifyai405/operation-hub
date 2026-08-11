import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, Check, ArrowRight, Clock } from "lucide-react";
import { aiApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { AiIcon, fmtDuration } from "@/components/ai/aiHelpers";

const greeting = () => {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
};

const sevRing = {
  high: "border-red-500/30 bg-red-500/[0.06]",
  medium: "border-amber-500/25 bg-amber-500/[0.05]",
  low: "border-white/10 bg-zinc-950",
};

export default function DashboardAIAssistant() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [saved, setSaved] = useState(null);
  const [done, setDone] = useState([]);
  const [insights, setInsights] = useState([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    Promise.all([
      aiApi.timeSaved().catch(() => null),
      aiApi.activities("today", 6).catch(() => []),
      aiApi.insights().catch(() => []),
    ]).then(([ts, acts, ins]) => {
      setSaved(ts); setDone(acts || []); setInsights(ins || []);
    }).finally(() => setLoaded(true));
  }, []);

  if (!loaded) return null;

  return (
    <div className="animate-fade-up rounded-2xl border border-brand-500/20 bg-gradient-to-br from-brand-600/10 via-zinc-950 to-zinc-950 p-5 sm:p-6" data-testid="dashboard-ai-assistant">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="mb-1 flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-600/20"><Sparkles className="h-4 w-4 text-brand-300" /></span>
            <h2 className="text-lg font-bold text-zinc-50" data-testid="ai-greeting">{greeting()}, {user?.firstName || "there"} 👋</h2>
          </div>
          <p className="text-sm text-zinc-400">Here's what Assistify has been working on for you.</p>

          <div className="mt-4 space-y-2" data-testid="ai-completed-list">
            {done.length === 0 ? (
              <p className="text-sm text-zinc-500">No AI work yet today — generate a proposal, contract or plan and I'll take it from here.</p>
            ) : (
              done.map((a) => (
                <div key={a.id} className="flex items-center gap-2.5 text-sm">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full border border-emerald-500/40 bg-emerald-500/15"><Check className="h-3 w-3 text-emerald-400" /></span>
                  <AiIcon name={a.icon} className="h-3.5 w-3.5 shrink-0 text-brand-300" />
                  <span className="truncate text-zinc-200">{a.title}</span>
                  <span className="ml-auto hidden shrink-0 text-xs text-zinc-500 sm:inline">saved {a.time_saved}m</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Time saved today */}
        <div className="shrink-0 rounded-xl border border-white/10 bg-zinc-950/70 px-5 py-4 text-center" data-testid="ai-time-saved-today">
          <p className="flex items-center justify-center gap-1.5 text-xs text-zinc-500"><Clock className="h-3.5 w-3.5" /> Time saved today</p>
          <p className="mt-1 text-3xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-brand-300 to-cyan-300">{fmtDuration(saved?.today || 0)}</p>
          <button onClick={() => navigate("/ai-workspace")} data-testid="ai-view-history" className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-brand-300 transition-colors hover:text-brand-200">
            View all activity <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Proactive insights */}
      {insights.length > 0 && (
        <div className="mt-5 border-t border-white/10 pt-4" data-testid="ai-insights">
          <p className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">Assistify noticed</p>
          <div className="grid gap-2.5 sm:grid-cols-2">
            {insights.map((i) => (
              <button key={i.id} onClick={() => navigate(i.link)} data-testid={`ai-insight-${i.type}`}
                className={`flex items-start gap-3 rounded-xl border p-3.5 text-left transition-all hover:border-brand-500/40 ${sevRing[i.severity] || sevRing.low}`}>
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-600/15 text-brand-300"><AiIcon name={i.icon} className="h-4 w-4" /></span>
                <span className="min-w-0">
                  <span className="block text-sm leading-snug text-zinc-200">{i.explanation}</span>
                  <span className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-brand-300">{i.action_label} <ArrowRight className="h-3 w-3" /></span>
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
