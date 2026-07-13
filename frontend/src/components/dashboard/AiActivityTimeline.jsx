import { useNavigate } from "react-router-dom";
import { Activity } from "lucide-react";
import { AiIcon, fmtDuration } from "@/components/ai/aiHelpers";
import { Section, relTime } from "./execShared";

export function AiActivityTimeline({ activity }) {
  const navigate = useNavigate();
  return (
    <Section title="Recent AI Activity" icon={Activity} testid="ai-activity-section"
      action={<button onClick={() => navigate("/ai-workspace")} className="text-xs font-medium text-violet-400 hover:text-violet-300">View all</button>}>
      <div className="rounded-2xl border border-white/10 bg-zinc-950 p-2">
        {!activity?.length ? (
          <p className="py-8 text-center text-sm text-zinc-500" data-testid="ai-activity-empty">Assistify hasn't done anything yet — generate a document to see it here.</p>
        ) : (
          <div className="relative">
            {activity.map((a, i) => (
              <button key={a.id} onClick={() => a.project_id && navigate(`/projects/${a.project_id}`)} data-testid={`ai-activity-${a.type}`}
                className="flex w-full items-start gap-3 rounded-xl px-2.5 py-2.5 text-left transition-colors hover:bg-white/5">
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600/15 text-violet-300"><AiIcon name={a.icon} className="h-4 w-4" /></span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-zinc-100">{a.title}</p>
                  <p className="line-clamp-1 text-xs text-zinc-500">{a.explanation}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[10px] text-zinc-600">
                    <span>{relTime(a.created_at)}</span>
                    {a.time_saved ? <span className="text-emerald-500/80">saved ~{fmtDuration(a.time_saved)}</span> : null}
                    {a.confidence ? <span>{a.confidence}% confidence</span> : null}
                    {a.project_name ? <span>{a.project_name}</span> : null}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </Section>
  );
}
