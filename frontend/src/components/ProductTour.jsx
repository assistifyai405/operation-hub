import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRight, Sparkles, X } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { isProductTourEligible, markProductTourDone } from "@/lib/productTour";

const STEPS = [
  {
    id: "dashboard",
    titleKey: "tour.steps.dashboard.title",
    bodyKey: "tour.steps.dashboard.body",
    to: "/dashboard",
  },
  {
    id: "clients",
    titleKey: "tour.steps.clients.title",
    bodyKey: "tour.steps.clients.body",
    to: "/clients",
  },
  {
    id: "copilot",
    titleKey: "tour.steps.copilot.title",
    bodyKey: "tour.steps.copilot.body",
    to: "/ai-chat",
  },
  {
    id: "agents",
    titleKey: "tour.steps.agents.title",
    bodyKey: "tour.steps.agents.body",
    to: "/ai-agents",
  },
  {
    id: "search",
    titleKey: "tour.steps.search.title",
    bodyKey: "tour.steps.search.body",
    to: null,
  },
];

/**
 * Lightweight optional first-dashboard tour. Never blocks the app.
 */
export default function ProductTour({ forceOpen = false, onOpenCommandPalette }) {
  const { t } = useTranslation();
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
        className="pointer-events-auto w-full max-w-sm rounded-2xl border border-brand-500/30 bg-zinc-950/95 p-4 shadow-2xl backdrop-blur sm:p-5"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600/20 text-brand-400" aria-hidden="true">
              <Sparkles className="h-4 w-4" />
            </span>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-400">
                {t("tour.progress", { current: step + 1, total: STEPS.length })}
              </p>
              <h2 id="product-tour-title" className="text-sm font-semibold text-zinc-50">{t(current.titleKey)}</h2>
            </div>
          </div>
          <button
            type="button"
            onClick={skip}
            aria-label={t("tour.dismiss")}
            data-testid="product-tour-dismiss"
            className="rounded-lg p-1 text-zinc-500 hover:bg-white/5 hover:text-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-zinc-400">{t(current.bodyKey)}</p>
        <div className="mt-4 flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={skip}
            data-testid="product-tour-skip"
            className="text-xs font-medium text-zinc-500 hover:text-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 rounded"
          >
            {t("tour.skip")}
          </button>
          <button
            type="button"
            onClick={primary}
            data-testid="product-tour-next"
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50"
          >
            {last ? t("tour.done") : t("tour.next")} <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}
