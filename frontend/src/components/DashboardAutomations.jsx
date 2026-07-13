import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Zap, ArrowRight, ShieldCheck, PauseCircle, Inbox } from "lucide-react";
import { automationApi } from "@/lib/api";

export default function DashboardAutomations() {
  const [s, setS] = useState(null);
  const navigate = useNavigate();
  useEffect(() => { automationApi.summary().then(setS).catch(() => {}); }, []);
  if (!s) return null;

  return (
    <button
      onClick={() => navigate("/automations")}
      data-testid="dashboard-automations-widget"
      className="group w-full rounded-2xl border border-white/10 bg-gradient-to-br from-violet-600/[0.08] to-transparent p-5 text-left transition-all hover:border-violet-500/40"
    >
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600/20 text-violet-300"><Zap className="h-4 w-4" /></span>
          Automation Engine
        </span>
        <ArrowRight className="h-4 w-4 text-zinc-600 transition-transform group-hover:translate-x-0.5 group-hover:text-violet-300" />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-medium ${s.paused ? "border-amber-500/30 bg-amber-500/15 text-amber-300" : s.enabled ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-300" : "border-zinc-600/40 text-zinc-400"}`}>
          {s.paused ? <PauseCircle className="h-3 w-3" /> : <ShieldCheck className="h-3 w-3" />}
          {s.paused ? "Paused" : s.enabled ? "Active" : "Off"}
        </span>
        {s.pending > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full border border-violet-500/30 bg-violet-500/15 px-2 py-0.5 font-medium text-violet-200" data-testid="dashboard-pending-approvals">
            <Inbox className="h-3 w-3" /> {s.pending} awaiting approval
          </span>
        )}
        <span className="text-zinc-500">{s.active_automations} running · {s.time_saved_total} min saved</span>
      </div>
    </button>
  );
}
