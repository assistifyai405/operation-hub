import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles, X } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { isProductTourEligible, markProductTourDone } from "@/lib/productTour";

const STEPS = [
  {
    id: "dashboard",
    title: "Your dashboard",
    body: "See priorities, quick actions, and workspace health once you add real clients and projects.",
    to: "/dashboard",
  },
  {
    id: "clients",
    title: "Clients",
    body: "Start with the people and companies you work with — everything else links back here.",
    to: "/clients",
  },
  {
    id: "copilot",
    title: "Copilot",
    body: "Ask for summaries, drafts, project plans, or proposals grounded in your workspace.",
    to: "/ai-chat",
  },
  {
    id: "agents",
    title: "AI Agents",
    body: "Chat with specialists for sales, writing, and ops when you want focused help.",
    to: "/ai-agents",
  },
  {
    id: "search",
    title: "Search & command palette",
    body: "Press ⌘K (or Ctrl+K) anytime to jump to a page or start a useful AI action.",
    to: null,
  },
];

/**
 * Lightweight optional first-dashboard tour. Never blocks the app.
 */
export default function ProductTour({ forceOpen = false, onOpenCommandPalette }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!user?.id) return;
    if (forceOpen) {
      setOpen(true);
      return;
    }
    if (user.onboardingCompleted === false) return;
    // Only first-run users marked eligible after onboarding (not every returning account)
    if (isProductTourEligible(user.id)) setOpen(true);
  }, [user?.id, user?.onboardingCompleted, forceOpen]);

  if (!open || !user) return null;

  const current = STEPS[step];
  const last = step >= STEPS.length - 1;

  const finish = () => {
    markProductTourDone(user.id);
    setOpen(false);
  };

  const next = () => {
    if (last) {
      finish();
      return;
    }
    const upcoming = STEPS[step + 1];
    if (upcoming?.to) navigate(upcoming.to);
    setStep((s) => s + 1);
  };

  const skip = () => finish();

  const primary = () => {
    if (current.to) navigate(current.to);
    if (current.id === "search" && onOpenCommandPalette) onOpenCommandPalette();
    next();
  };

  return (
    <div
      className="fixed inset-x-0 bottom-0 z-[60] flex justify-center p-4 sm:bottom-6 sm:justify-end sm:p-6 pointer-events-none"
      data-testid="product-tour"
    >
      <div
        role="dialog"
        aria-modal="false"
        aria-labelledby="product-tour-title"
        className="pointer-events-auto w-full max-w-sm rounded-2xl border border-violet-500/30 bg-zinc-950/95 p-4 shadow-2xl backdrop-blur sm:p-5"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600/20 text-violet-400" aria-hidden="true">
              <Sparkles className="h-4 w-4" />
            </span>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-400">
                Quick tour · {step + 1}/{STEPS.length}
              </p>
              <h2 id="product-tour-title" className="text-sm font-semibold text-zinc-50">{current.title}</h2>
            </div>
          </div>
          <button
            type="button"
            onClick={skip}
            aria-label="Dismiss product tour"
            data-testid="product-tour-dismiss"
            className="rounded-lg p-1 text-zinc-500 hover:bg-white/5 hover:text-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-zinc-400">{current.body}</p>
        <div className="mt-4 flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={skip}
            data-testid="product-tour-skip"
            className="text-xs font-medium text-zinc-500 hover:text-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50 rounded"
          >
            Skip tour
          </button>
          <button
            type="button"
            onClick={primary}
            data-testid="product-tour-next"
            className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50"
          >
            {last ? "Got it" : "Next"} <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}
