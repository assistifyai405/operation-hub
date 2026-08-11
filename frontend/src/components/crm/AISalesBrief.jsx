import { useState } from "react";
import { Sparkles, Loader2, Heart, TrendingUp, Zap, ShieldAlert, ArrowRight, AlertCircle, HelpCircle, MessageSquare, RefreshCw } from "lucide-react";
import { crmApi } from "@/lib/api";
import { toast } from "sonner";

const HEALTH = { "Healthy": "text-emerald-400 bg-emerald-500/15", "At Risk": "text-amber-400 bg-amber-500/15", "Critical": "text-red-400 bg-red-500/15" };
const LEVEL = { "Low": "text-emerald-400", "Medium": "text-amber-400", "High": "text-red-400" };

function Stat({ icon: Icon, label, value, cls }) {
  return (
    <div className="rounded-xl border border-white/10 bg-zinc-900/60 p-3">
      <div className="flex items-center gap-1.5 text-[11px] text-zinc-500"><Icon className="h-3.5 w-3.5" /> {label}</div>
      <p className={`mt-1 text-sm font-bold ${cls || "text-zinc-100"}`}>{value}</p>
    </div>
  );
}

export function AISalesBrief({ leadId }) {
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(false);

  const gen = async (refresh = false) => {
    setLoading(true);
    try { setBrief(await crmApi.leadBrief(leadId, refresh)); }
    catch (e) { toast.error(e.message || "AI brief failed"); }
    finally { setLoading(false); }
  };

  if (!brief) {
    return (
      <button onClick={() => gen(false)} disabled={loading} data-testid="lead-generate-brief"
        className="flex w-full items-center justify-center gap-2 rounded-xl border border-brand-500/30 bg-brand-500/[0.06] py-3 text-sm font-semibold text-brand-200 transition-all hover:bg-brand-500/15 disabled:opacity-60">
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        {loading ? "Analyzing this deal…" : "Generate AI Sales Brief"}
      </button>
    );
  }

  return (
    <div className="space-y-3" data-testid="lead-ai-brief">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat icon={Heart} label="Deal health" value={brief.deal_health} cls={HEALTH[brief.deal_health]?.split(" ")[0]} />
        <Stat icon={TrendingUp} label="Win prob." value={`${brief.win_probability}%`} cls="text-brand-300" />
        <Stat icon={Zap} label="Urgency" value={brief.urgency} cls={LEVEL[brief.urgency]} />
        <Stat icon={ShieldAlert} label="Risk" value={brief.risk_level} cls={LEVEL[brief.risk_level]} />
      </div>
      <div className="rounded-xl border border-brand-500/25 bg-brand-500/[0.05] p-3.5" data-testid="lead-next-action">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-brand-300"><ArrowRight className="h-3.5 w-3.5" /> Next best action</div>
        <p className="mt-1 text-sm text-zinc-200">{brief.next_best_action}</p>
      </div>
      {brief.relationship_summary && <Block icon={MessageSquare} title="Relationship summary" text={brief.relationship_summary} />}
      {brief.conversation_summary && <Block icon={MessageSquare} title="Conversation summary" text={brief.conversation_summary} />}
      {brief.suggested_followup && <Block icon={ArrowRight} title="Suggested follow-up" text={brief.suggested_followup} />}
      {brief.objections?.length > 0 && <List icon={AlertCircle} title="Objections detected" items={brief.objections} color="text-amber-400" />}
      {brief.missing_info?.length > 0 && <List icon={HelpCircle} title="Missing information" items={brief.missing_info} color="text-cyan-400" />}
      <button onClick={() => gen(true)} disabled={loading} data-testid="lead-refresh-brief"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-500 hover:text-zinc-300">
        {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />} Regenerate brief
      </button>
    </div>
  );
}

const Block = ({ icon: Icon, title, text }) => (
  <div className="rounded-xl border border-white/10 bg-zinc-900/40 p-3">
    <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-400"><Icon className="h-3.5 w-3.5" /> {title}</div>
    <p className="mt-1 text-sm leading-snug text-zinc-300">{text}</p>
  </div>
);

const List = ({ icon: Icon, title, items, color }) => (
  <div className="rounded-xl border border-white/10 bg-zinc-900/40 p-3">
    <div className={`flex items-center gap-1.5 text-xs font-semibold ${color}`}><Icon className="h-3.5 w-3.5" /> {title}</div>
    <ul className="mt-1.5 space-y-1">
      {items.map((it, i) => <li key={i} className="flex gap-2 text-sm text-zinc-300"><span className={`mt-1.5 h-1 w-1 shrink-0 rounded-full ${color.replace("text-", "bg-")}`} /> {it}</li>)}
    </ul>
  </div>
);
