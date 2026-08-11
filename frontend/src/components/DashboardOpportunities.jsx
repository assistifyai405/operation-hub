import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Target, ArrowRight } from "lucide-react";
import { opportunitiesApi } from "@/lib/api";
import { DailyBrief } from "@/components/opportunities/DailyBrief";
import { HealthWidget } from "@/components/opportunities/HealthWidget";
import { OpportunityCard } from "@/components/opportunities/OpportunityCard";
import { useOpportunityActions } from "@/components/opportunities/shared";

export default function DashboardOpportunities() {
  const navigate = useNavigate();
  const [brief, setBrief] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    Promise.all([
      opportunitiesApi.brief().then(setBrief).catch(() => setBrief(null)),
      opportunitiesApi.health().then(setHealth).catch(() => setHealth(null)),
    ]).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);
  const { run, dismiss } = useOpportunityActions(load);

  const top = brief?.top || [];
  return (
    <div className="space-y-4" data-testid="dashboard-opportunities">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <DailyBrief data={brief} loading={loading} />
        <HealthWidget data={health} loading={loading} />
      </div>
      {top.length > 0 && (
        <div>
          <div className="mb-2.5 flex items-center justify-between">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500"><Target className="h-3.5 w-3.5 text-brand-400" /> Top opportunities</p>
            <button onClick={() => navigate("/opportunities")} data-testid="dash-view-opportunities" className="inline-flex items-center gap-1 text-xs font-medium text-brand-300 hover:text-brand-200">View all <ArrowRight className="h-3.5 w-3.5" /></button>
          </div>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            {top.map((it) => <OpportunityCard key={it.id} item={it} onRun={run} onDismiss={dismiss} compact />)}
          </div>
        </div>
      )}
    </div>
  );
}
