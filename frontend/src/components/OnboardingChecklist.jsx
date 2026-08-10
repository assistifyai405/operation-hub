import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Circle, Sparkles, ChevronRight, X } from "lucide-react";
import { onboardingApi } from "@/lib/api";

const SESSION_KEY = "onb_checklist_dismissed";

export default function OnboardingChecklist() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [dismissed, setDismissed] = useState(() => {
    try {
      return sessionStorage.getItem(SESSION_KEY) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    onboardingApi
      .checklist()
      .then((r) => {
        setData(r);
        if (r?.dismissed) {
          setDismissed(true);
          try { sessionStorage.setItem(SESSION_KEY, "1"); } catch { /* ignore */ }
        }
      })
      .catch(() => {});
  }, []);

  if (!data || dismissed || data.percent === 100) return null;

  const dismiss = async () => {
    setDismissed(true);
    try { sessionStorage.setItem(SESSION_KEY, "1"); } catch { /* ignore */ }
    try {
      await onboardingApi.dismissChecklist();
    } catch {
      /* session dismiss still stands for this browser session */
    }
  };

  const title = data.title || "Get Assistify working for you";
  const subtitle = data.subtitle || "Complete these steps with real workspace data.";

  return (
    <div className="rounded-xl border border-violet-500/25 bg-gradient-to-br from-violet-600/10 to-transparent p-5" data-testid="onboarding-checklist">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600/20 text-violet-400" aria-hidden="true">
            <Sparkles className="h-4 w-4" />
          </span>
          <div>
            <h3 className="text-sm font-semibold text-zinc-100">{title}</h3>
            <p className="text-xs text-zinc-500">{subtitle}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={dismiss}
          data-testid="dismiss-checklist"
          aria-label="Dismiss setup checklist"
          className="text-zinc-500 transition-colors hover:text-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50 rounded"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="text-zinc-400">
            {data.done} of {data.total} complete
          </span>
          <span className="font-semibold text-violet-400" data-testid="onboarding-percent">
            {data.percent}%
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-zinc-800" role="progressbar" aria-valuenow={data.percent} aria-valuemin={0} aria-valuemax={100} aria-label="Workspace setup progress">
          <div className="h-full rounded-full bg-violet-500 transition-all duration-500" style={{ width: `${data.percent}%` }} />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {data.items.map((it) => (
          <button
            key={it.key}
            type="button"
            onClick={() => navigate(it.to)}
            data-testid={`checklist-item-${it.key}`}
            className="group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50"
          >
            {it.done ? (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400" aria-hidden="true">
                <Check className="h-3 w-3" />
              </span>
            ) : (
              <Circle className="h-5 w-5 text-zinc-600" aria-hidden="true" />
            )}
            <span className={`flex-1 text-sm ${it.done ? "text-zinc-500 line-through" : "text-zinc-200"}`}>{it.label}</span>
            {!it.done && <ChevronRight className="h-4 w-4 text-zinc-600 opacity-0 transition-opacity group-hover:opacity-100" aria-hidden="true" />}
          </button>
        ))}
      </div>
    </div>
  );
}
