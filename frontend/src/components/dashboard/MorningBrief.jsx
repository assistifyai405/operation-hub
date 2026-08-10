import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  Sparkles, ChevronDown, ArrowRight, Trophy, AlertTriangle, ListChecks, Activity, Loader2, Sun,
} from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { dashboardApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { AiIcon, fmtDuration } from "@/components/ai/aiHelpers";
import { money, relTime, PRIORITY_META } from "./execShared";

function Collapsible({ icon: Icon, title, count, tone = "text-violet-400", defaultOpen = true, children, testid }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-2xl border border-white/10 bg-zinc-950/70" data-testid={testid}>
      <button onClick={() => setOpen((o) => !o)} data-testid={`${testid}-toggle`} className="flex w-full items-center justify-between px-4 py-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-zinc-100"><Icon className={`h-4 w-4 ${tone}`} /> {title}{count != null && <span className="rounded-full bg-white/10 px-1.5 text-[10px] text-zinc-400">{count}</span>}</span>
        <ChevronDown className={`h-4 w-4 text-zinc-500 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }} className="overflow-hidden">
            <div className="px-4 pb-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function MorningBrief({ open, onOpenChange }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const firstName = (user?.firstName || (user?.email || "").split("@")[0] || "").trim();

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    dashboardApi.morningBrief().then(setData).catch((e) => toast.error(e.message)).finally(() => setLoading(false));
  }, [open]);

  const go = (link) => { if (link) { onOpenChange(false); navigate(link); } };

  const NUMBERS = data ? [
    { label: "Revenue", value: data.numbers.revenue == null ? "—" : money(data.numbers.revenue), tone: "text-emerald-400" },
    { label: "Pipeline", value: data.numbers.pipeline == null ? "—" : money(data.numbers.pipeline), tone: "text-violet-400" },
    { label: "Hours Saved", value: data.numbers.hours_saved == null ? "—" : `${data.numbers.hours_saved}h`, tone: "text-cyan-400" },
    { label: "Business Health", value: data.numbers.business_health == null ? "—" : `${data.numbers.business_health}`, tone: "text-emerald-400" },
    { label: "Active Clients", value: `${data.numbers.clients_active ?? 0}`, tone: "text-zinc-100" },
    { label: "Deals Closing", value: `${data.numbers.deals_closing ?? 0}`, tone: "text-amber-400" },
  ] : [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] gap-0 overflow-y-auto border-white/10 bg-zinc-950 p-0 text-zinc-100 sm:max-w-2xl" data-testid="morning-brief">
        <DialogTitle className="sr-only">AI Morning Brief</DialogTitle>
        {/* Hero */}
        <div className="relative overflow-hidden rounded-t-lg border-b border-white/10 p-6">
          <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-violet-600/20 blur-3xl" />
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-violet-300"><Sun className="h-4 w-4" /> AI Morning Brief</div>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-zinc-50">
            {data?.greeting || "Good morning"}{firstName ? `, ${firstName}` : ""} 👋
          </h2>
          <p className="mt-1 text-sm text-zinc-400">Here's what happened while you were away.</p>
        </div>

        {loading || !data ? (
          <div className="flex items-center justify-center py-16 text-zinc-600"><Loader2 className="h-6 w-6 animate-spin" /></div>
        ) : (
          <div className="space-y-3 p-4">
            {/* Numbers */}
            <div className="grid grid-cols-3 gap-2" data-testid="brief-numbers">
              {NUMBERS.map((n) => (
                <div key={n.label} className="rounded-xl border border-white/10 bg-zinc-900/50 p-3 text-center">
                  <p className={`text-lg font-bold ${n.tone}`}>{n.value}</p>
                  <p className="text-[10px] text-zinc-500">{n.label}</p>
                </div>
              ))}
            </div>

            {/* Summary */}
            <Collapsible icon={Sparkles} title="Today's Summary" testid="brief-summary">
              <div className="space-y-1.5">
                {data.summary.map((s, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm text-zinc-300" data-testid="brief-summary-item">
                    <AiIcon name={s.icon} className="h-3.5 w-3.5 shrink-0 text-violet-400" /> {s.text}
                  </div>
                ))}
              </div>
            </Collapsible>

            {/* Wins */}
            {data.wins.length > 0 && (
              <Collapsible icon={Trophy} title="Business Wins" count={data.wins.length} tone="text-emerald-400" testid="brief-wins">
                <div className="space-y-1.5">
                  {data.wins.map((w, i) => (
                    <div key={i} className="flex items-center gap-2.5 rounded-lg border border-emerald-500/15 bg-emerald-500/5 px-3 py-2" data-testid="brief-win-item">
                      <AiIcon name={w.icon} className="h-4 w-4 shrink-0 text-emerald-400" />
                      <div className="min-w-0"><p className="truncate text-sm font-medium text-zinc-100">{w.title}</p><p className="truncate text-xs text-zinc-500">{w.detail}</p></div>
                    </div>
                  ))}
                </div>
              </Collapsible>
            )}

            {/* Risks */}
            {data.risks.length > 0 && (
              <Collapsible icon={AlertTriangle} title="Risks" count={data.risks.length} tone="text-red-400" testid="brief-risks">
                <div className="space-y-1.5">
                  {data.risks.map((r, i) => {
                    const pm = PRIORITY_META[r.severity] || PRIORITY_META.Medium;
                    return (
                      <div key={i} className="flex items-center gap-2.5 rounded-lg border border-white/10 bg-zinc-900/50 px-3 py-2" data-testid="brief-risk-item">
                        <span className={`h-2 w-2 shrink-0 rounded-full ${pm.dot}`} />
                        <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-zinc-100">{r.title}</p><p className="truncate text-xs text-zinc-500">{r.detail}</p></div>
                        {r.action?.link && <button onClick={() => go(r.action.link)} data-testid="brief-risk-action" className="shrink-0 rounded-lg border border-white/10 px-2.5 py-1 text-[11px] font-medium text-zinc-300 hover:bg-zinc-800">{r.action.label}</button>}
                      </div>
                    );
                  })}
                </div>
              </Collapsible>
            )}

            {/* Recommendations */}
            {data.recommendations.length > 0 && (
              <Collapsible icon={ListChecks} title="AI Recommendations" count={data.recommendations.length} testid="brief-recommendations">
                <div className="space-y-1.5">
                  {data.recommendations.map((it) => {
                    const pm = PRIORITY_META[it.priority] || PRIORITY_META.Medium;
                    return (
                      <div key={it.id} className="flex items-center gap-2.5 rounded-lg border border-white/10 bg-zinc-900/50 px-3 py-2" data-testid="brief-rec-item">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600/15 text-violet-300"><AiIcon name={it.icon} className="h-4 w-4" /></span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-zinc-100">{it.title}</p>
                          <div className="flex items-center gap-2 text-[10px] text-zinc-500">
                            <span className={`rounded-full border px-1.5 ${pm.chip}`}>{it.priority}</span>
                            {it.revenue_impact ? <span className="text-emerald-400">≈{money(it.revenue_impact)}</span> : null}
                            <span>{it.confidence}%</span>
                          </div>
                        </div>
                        {it.action?.link && <button onClick={() => go(it.action.link)} data-testid="brief-rec-action" className="shrink-0 inline-flex items-center gap-1 rounded-lg bg-violet-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-violet-500">{it.action.label} <ArrowRight className="h-3 w-3" /></button>}
                      </div>
                    );
                  })}
                </div>
              </Collapsible>
            )}

            {/* What AI did */}
            {data.what_ai_did.length > 0 && (
              <Collapsible icon={Activity} title="What AI Did" count={data.what_ai_did.length} defaultOpen={false} testid="brief-ai-activity">
                <div className="space-y-1">
                  {data.what_ai_did.map((a) => (
                    <div key={a.id} className="flex items-start gap-2.5 rounded-lg px-1 py-1.5" data-testid="brief-ai-item">
                      <AiIcon name={a.icon} className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-400" />
                      <div className="min-w-0 flex-1"><p className="truncate text-sm text-zinc-200">{a.title}</p>
                        <p className="text-[10px] text-zinc-600">{relTime(a.created_at)}{a.time_saved ? ` · saved ~${fmtDuration(a.time_saved)}` : ""}{a.confidence ? ` · ${a.confidence}%` : ""}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </Collapsible>
            )}

            <div className="flex justify-end gap-2 pt-1">
              <button onClick={() => onOpenChange(false)} data-testid="brief-dismiss" className="rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-900">View dashboard</button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
