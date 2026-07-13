import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Circle, Sparkles, ChevronRight, X } from "lucide-react";
import { onboardingApi } from "@/lib/api";

export default function OnboardingChecklist() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [dismissed, setDismissed] = useState(() => sessionStorage.getItem("onb_checklist_dismissed") === "1");

  useEffect(() => {
    onboardingApi.checklist().then(setData).catch(() => {});
  }, []);

  if (!data || dismissed || data.percent === 100) return null;

  const dismiss = () => { sessionStorage.setItem("onb_checklist_dismissed", "1"); setDismissed(true); };

  return (
    <div className="rounded-xl border border-violet-500/25 bg-gradient-to-br from-violet-600/10 to-transparent p-5" data-testid="onboarding-checklist">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600/20 text-violet-400"><Sparkles className="h-4 w-4" /></span>
          <div>
            <h3 className="text-sm font-semibold text-zinc-100">Finish setting up your AI employee</h3>
            <p className="text-xs text-zinc-500">Complete these to get the most out of Assistify.</p>
          </div>
        </div>
        <button onClick={dismiss} data-testid="dismiss-checklist" className="text-zinc-500 transition-colors hover:text-zinc-300"><X className="h-4 w-4" /></button>
      </div>

      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="text-zinc-400">{data.done} of {data.total} complete</span>
          <span className="font-semibold text-violet-400" data-testid="onboarding-percent">{data.percent}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-zinc-800">
          <div className="h-full rounded-full bg-violet-500 transition-all duration-500" style={{ width: `${data.percent}%` }} />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {data.items.map((it) => (
          <button key={it.key} onClick={() => navigate(it.to)} data-testid={`checklist-item-${it.key}`}
            className="group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-white/5">
            {it.done
              ? <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400"><Check className="h-3 w-3" /></span>
              : <Circle className="h-5 w-5 text-zinc-600" />}
            <span className={`flex-1 text-sm ${it.done ? "text-zinc-500 line-through" : "text-zinc-200"}`}>{it.label}</span>
            {!it.done && <ChevronRight className="h-4 w-4 text-zinc-600 opacity-0 transition-opacity group-hover:opacity-100" />}
          </button>
        ))}
      </div>
    </div>
  );
}
