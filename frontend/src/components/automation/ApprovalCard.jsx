import { useState } from "react";
import { Check, X, Pencil, Ban, Clock, ChevronDown, Sparkles, Info } from "lucide-react";
import { AiIcon, relTime, fmtDuration } from "@/components/ai/aiHelpers";
import { RISK_META, KIND_META } from "./automationShared";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

export function ApprovalCard({ item, onApprove, onReject, onPrepare, onEdit, onDisable, busy }) {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.actions || []);
  const risk = RISK_META[item.risk_level] || RISK_META.low;
  const isSuggestion = item.status === "suggested";
  const emailAction = (item.actions || []).find((a) => a.payload?.email);

  const saveEdit = () => { onEdit(item, draft); setEditing(false); };

  const updateEmail = (idx, field, value) => {
    setDraft((prev) => prev.map((a, i) => (i === idx ? { ...a, payload: { ...a.payload, email: { ...a.payload.email, [field]: value } } } : a)));
  };
  const updateTaskTitle = (idx, value) => {
    setDraft((prev) => prev.map((a, i) => (i === idx ? { ...a, payload: { ...a.payload, task: { ...a.payload.task, title: value } } } : a)));
  };

  return (
    <div data-testid={`approval-card-${item.id}`} className="rounded-2xl border border-white/10 bg-zinc-950 p-5 transition-all hover:border-violet-500/25">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-600/15 text-violet-300">
          <AiIcon name={(item.actions?.[0]?.icon) || "sparkles"} className="h-[18px] w-[18px]" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-zinc-100">{item.what}</p>
            <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${risk.chip}`} data-testid={`approval-risk-${item.id}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${risk.dot}`} /> {risk.label}
            </span>
            {isSuggestion && <span className="rounded-full border border-sky-500/30 bg-sky-500/15 px-2 py-0.5 text-[10px] font-medium text-sky-300">Suggestion</span>}
          </div>

          <p className="mt-1.5 flex items-start gap-1.5 text-xs text-zinc-400"><Info className="mt-0.5 h-3 w-3 shrink-0 text-violet-400" /> {item.why}</p>

          <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
            <div className="rounded-lg border border-white/5 bg-zinc-900/60 px-2.5 py-2">
              <p className="text-[10px] uppercase tracking-wide text-zinc-600">Trigger</p>
              <p className="mt-0.5 font-medium text-zinc-300">{item.trigger}</p>
            </div>
            <div className="rounded-lg border border-white/5 bg-zinc-900/60 px-2.5 py-2">
              <p className="text-[10px] uppercase tracking-wide text-zinc-600">Expected result</p>
              <p className="mt-0.5 font-medium text-zinc-300">{item.expected_result}</p>
            </div>
          </div>

          <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500">
            <span className="inline-flex items-center gap-1 text-emerald-400"><Clock className="h-3 w-3" /> Saves ~{fmtDuration(item.time_saved)}</span>
            <span>from {item.automation_name}</span>
            <span>{relTime(item.created_at)}</span>
          </div>

          {/* Prepared draft preview / editor */}
          {!isSuggestion && (item.actions || []).some((a) => a.payload?.email || a.payload?.task) && (
            <button onClick={() => setOpen((o) => !o)} data-testid={`approval-expand-${item.id}`} className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-violet-300 hover:text-violet-200">
              <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`} /> {open ? "Hide" : "View"} prepared draft
            </button>
          )}
          {open && !isSuggestion && (
            <div className="mt-2 space-y-3">
              {(editing ? draft : item.actions).map((a, idx) => (
                <div key={idx} className="rounded-lg border border-white/10 bg-black/40 p-3">
                  <div className="mb-1.5 flex items-center gap-2">
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${(KIND_META[a.kind] || KIND_META.internal).chip}`}>{(KIND_META[a.kind] || KIND_META.internal).label}</span>
                    <span className="text-xs font-medium text-zinc-300">{a.label}</span>
                  </div>
                  {a.payload?.email && (
                    editing ? (
                      <div className="space-y-2">
                        <Input value={a.payload.email.subject} onChange={(e) => updateEmail(idx, "subject", e.target.value)} data-testid={`approval-edit-subject-${item.id}`} className="h-8 border-white/10 bg-zinc-900 text-xs" />
                        <Textarea value={a.payload.email.body} onChange={(e) => updateEmail(idx, "body", e.target.value)} data-testid={`approval-edit-body-${item.id}`} rows={6} className="border-white/10 bg-zinc-900 text-xs" />
                      </div>
                    ) : (
                      <div className="text-xs text-zinc-400">
                        <p className="font-semibold text-zinc-300">{a.payload.email.subject}</p>
                        <p className="mt-1 whitespace-pre-wrap leading-relaxed">{a.payload.email.body}</p>
                      </div>
                    )
                  )}
                  {a.payload?.task && (
                    editing ? (
                      <Input value={a.payload.task.title} onChange={(e) => updateTaskTitle(idx, e.target.value)} data-testid={`approval-edit-task-${item.id}`} className="h-8 border-white/10 bg-zinc-900 text-xs" />
                    ) : (
                      <p className="text-xs text-zinc-400">Task: <span className="text-zinc-200">{a.payload.task.title}</span> · {a.payload.task.priority}</p>
                    )
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Transparency: data used */}
          <details className="mt-2.5 text-[11px] text-zinc-600">
            <summary className="cursor-pointer select-none hover:text-zinc-400" data-testid={`approval-data-used-${item.id}`}>Why it ran · data it used</summary>
            <ul className="mt-1 list-disc space-y-0.5 pl-4">
              {(item.data_used || []).map((d, i) => <li key={i}>{d}</li>)}
              <li>Approval was required before anything ran (Prepare-for-approval mode).</li>
            </ul>
          </details>

          {/* Actions */}
          <div className="mt-3.5 flex flex-wrap items-center gap-2">
            {isSuggestion ? (
              <>
                <button onClick={() => onPrepare(item)} disabled={busy} data-testid={`approval-prepare-${item.id}`} className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-50">
                  <Sparkles className="h-3.5 w-3.5" /> Prepare it
                </button>
                <button onClick={() => onReject(item)} disabled={busy} data-testid={`approval-dismiss-${item.id}`} className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium text-zinc-400 transition-all hover:text-zinc-200">
                  <X className="h-3.5 w-3.5" /> Dismiss
                </button>
              </>
            ) : editing ? (
              <>
                <button onClick={saveEdit} data-testid={`approval-save-${item.id}`} className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white transition-all hover:bg-emerald-500">
                  <Check className="h-3.5 w-3.5" /> Save changes
                </button>
                <button onClick={() => { setEditing(false); setDraft(item.actions || []); }} className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-200">Cancel</button>
              </>
            ) : (
              <>
                <button onClick={() => onApprove(item)} disabled={busy} data-testid={`approval-approve-${item.id}`} className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white transition-all hover:bg-emerald-500 disabled:opacity-50">
                  <Check className="h-3.5 w-3.5" /> Approve
                </button>
                {emailAction && (
                  <button onClick={() => { setOpen(true); setEditing(true); setDraft(item.actions || []); }} data-testid={`approval-edit-${item.id}`} className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium text-zinc-300 transition-all hover:bg-zinc-900">
                    <Pencil className="h-3.5 w-3.5" /> Edit
                  </button>
                )}
                <button onClick={() => onReject(item)} disabled={busy} data-testid={`approval-reject-${item.id}`} className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium text-zinc-400 transition-all hover:text-red-300">
                  <X className="h-3.5 w-3.5" /> Reject
                </button>
                <button onClick={() => onDisable(item)} data-testid={`approval-disable-${item.id}`} className="ml-auto inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-medium text-zinc-500 transition-all hover:text-amber-300">
                  <Ban className="h-3 w-3" /> Disable this automation
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
