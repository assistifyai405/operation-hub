import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Zap, ArrowRight, ArrowLeft, Clock } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { onboardingApi, automationApi } from "@/lib/api";
import { StepShell, PrimaryBtn, GhostBtn } from "./onboardingShared";

export function StepAutomations({ data, next, back }) {
  const recommended = data.automations || [];
  const [autos, setAutos] = useState([]);

  useEffect(() => { automationApi.automations().then(setAutos).catch(() => {}); }, []);

  const findAuto = (key) => autos.find((a) => a.template_key === key);

  const toggle = async (key, v) => {
    const a = findAuto(key);
    if (!a) return;
    setAutos((prev) => prev.map((x) => (x.id === a.id ? { ...x, enabled: v } : x)));
    try { await automationApi.toggleAutomation(a.id, v); }
    catch (e) { toast.error(e.message); }
  };

  return (
    <StepShell>
      <div data-testid="onb-step-automations">
        <div className="mb-5 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-600/15 text-brand-400"><Zap className="h-5 w-5" /></span>
          <div>
            <h2 className="text-2xl font-bold text-zinc-50">Smart automations, ready to go</h2>
            <p className="text-sm text-zinc-500">Enabled by default — Assistify prepares these for your approval. Turn off any you don't want.</p>
          </div>
        </div>

        <div className="space-y-2.5">
          {recommended.map((r) => {
            const a = findAuto(r.key);
            const enabled = a ? a.enabled : true;
            return (
              <div key={r.key} data-testid={`onb-automation-${r.key}`} className="flex items-center gap-3 rounded-xl border border-white/10 bg-zinc-950 p-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-600/15 text-brand-300"><Zap className="h-4 w-4" /></span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-zinc-100">{r.name}</p>
                  <p className="text-xs text-zinc-500">{r.description}</p>
                </div>
                <span className="hidden items-center gap-1 text-xs text-emerald-400 sm:inline-flex"><Clock className="h-3 w-3" /> ~{r.time_saved} min saved</span>
                <Switch checked={enabled} onCheckedChange={(v) => toggle(r.key, v)} data-testid={`onb-automation-toggle-${r.key}`} disabled={!a} />
              </div>
            );
          })}
        </div>

        <div className="mt-8 flex items-center justify-between">
          <GhostBtn onClick={back}><ArrowLeft className="h-4 w-4" /> Back</GhostBtn>
          <PrimaryBtn onClick={next} data-testid="onb-automations-continue">Continue <ArrowRight className="h-4 w-4" /></PrimaryBtn>
        </div>
      </div>
    </StepShell>
  );
}
