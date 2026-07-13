import { Clock, Pencil, Trash2, Zap } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { AiIcon, relTime } from "@/components/ai/aiHelpers";
import { MODE_META } from "./automationShared";

export function AutomationCard({ a, onToggle, onMode, onEdit, onDelete }) {
  const mode = MODE_META[a.mode] || MODE_META.prepare;
  return (
    <div
      data-testid={`automation-card-${a.id}`}
      className={`rounded-2xl border bg-zinc-950 p-5 transition-all ${a.enabled ? "border-white/10 hover:border-violet-500/30" : "border-white/5 opacity-70"}`}
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-600/15 text-violet-300">
          <AiIcon name={a.trigger_icon} className="h-[18px] w-[18px]" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-zinc-100">{a.name}</p>
              <p className="mt-0.5 line-clamp-2 text-xs text-zinc-500">{a.description}</p>
            </div>
            <Switch
              checked={a.enabled}
              onCheckedChange={(v) => onToggle(a, v)}
              data-testid={`automation-toggle-${a.id}`}
              aria-label={`Toggle ${a.name}`}
            />
          </div>

          <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
            <div className="rounded-lg border border-white/5 bg-zinc-900/60 px-2.5 py-2">
              <p className="text-[10px] uppercase tracking-wide text-zinc-600">When</p>
              <p className="mt-0.5 font-medium text-zinc-300">{a.trigger_label}</p>
            </div>
            <div className="rounded-lg border border-white/5 bg-zinc-900/60 px-2.5 py-2">
              <p className="text-[10px] uppercase tracking-wide text-zinc-600">If</p>
              <p className="mt-0.5 font-medium text-zinc-300">{a.conditions?.length ? `${a.conditions.length} condition${a.conditions.length > 1 ? "s" : ""}` : "Always"}</p>
            </div>
            <div className="rounded-lg border border-white/5 bg-zinc-900/60 px-2.5 py-2">
              <p className="text-[10px] uppercase tracking-wide text-zinc-600">Then</p>
              <p className="mt-0.5 truncate font-medium text-zinc-300">{(a.action_labels || []).join(", ")}</p>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Select value={a.mode} onValueChange={(v) => onMode(a, v)}>
              <SelectTrigger data-testid={`automation-mode-${a.id}`} className="h-8 w-[190px] border-white/10 bg-zinc-900 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">
                {Object.entries(MODE_META).map(([v, m]) => (
                  <SelectItem key={v} value={v} className="text-xs">{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${mode.chip}`}>
              <Zap className="h-3 w-3" /> {mode.short}
            </span>
            {a.pending_count > 0 && (
              <span className="rounded-full border border-amber-500/30 bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300" data-testid={`automation-pending-${a.id}`}>
                {a.pending_count} awaiting approval
              </span>
            )}
            <div className="ml-auto flex items-center gap-1">
              {a.source === "custom" && (
                <button onClick={() => onEdit(a)} data-testid={`automation-edit-${a.id}`} aria-label="Edit automation" className="rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-zinc-900 hover:text-zinc-200">
                  <Pencil className="h-3.5 w-3.5" />
                </button>
              )}
              <button onClick={() => onDelete(a)} data-testid={`automation-delete-${a.id}`} aria-label="Delete automation" className="rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-red-500/10 hover:text-red-300">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/5 pt-2.5 text-[11px] text-zinc-600">
            <span className="inline-flex items-center gap-1"><Clock className="h-3 w-3" /> Last run {a.last_run ? relTime(a.last_run) : "—"}</span>
            <span>Next check {a.next_evaluation ? relTime(a.next_evaluation) : "soon"}</span>
            <span className="text-emerald-500/80">{a.runs_count || 0} runs · {a.time_saved_total || 0} min saved</span>
          </div>
        </div>
      </div>
    </div>
  );
}
