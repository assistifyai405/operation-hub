import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { getHelpModule } from "@/help/registry";
import { useHelp } from "@/help/HelpContext";

function pickElement(selector) {
  if (!selector || typeof document === "undefined") return null;
  const parts = selector.split(",").map((s) => s.trim()).filter(Boolean);
  for (const part of parts) {
    const el = document.querySelector(part);
    if (el) return el;
  }
  return null;
}

/**
 * Interactive guided tour — highlights real UI, never auto-operates.
 * User must click real controls; tour never submits/deletes/emails/AI-calls.
 */
export default function GuidedTour() {
  const { t } = useTranslation();
  const {
    tourModule,
    tourStepIndex,
    advanceTour,
    closeTour,
    restartTour,
    startTour,
  } = useHelp();
  const [searchParams, setSearchParams] = useSearchParams();
  const [rect, setRect] = useState(null);

  // Resume tour from ?guidedTour=crm
  useEffect(() => {
    const id = searchParams.get("guidedTour");
    if (!id) return;
    if (!tourModule) startTour(id);
    const next = new URLSearchParams(searchParams);
    next.delete("guidedTour");
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams, startTour, tourModule]);

  const mod = tourModule ? getHelpModule(tourModule) : null;
  const contentId = mod?.contentId || tourModule;
  const steps = mod?.tourSteps || [];
  const step = steps[tourStepIndex];
  const last = tourStepIndex >= steps.length - 1;

  const measure = useCallback(() => {
    if (!step?.selector) {
      setRect(null);
      return;
    }
    const el = pickElement(step.selector);
    if (!el) {
      setRect(null);
      return;
    }
    const r = el.getBoundingClientRect();
    const pad = 8;
    setRect({
      top: Math.max(8, r.top - pad),
      left: Math.max(8, r.left - pad),
      width: Math.min(window.innerWidth - 16, r.width + pad * 2),
      height: Math.min(window.innerHeight - 16, r.height + pad * 2),
    });
    try {
      el.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
    } catch {
      /* ignore */
    }
  }, [step]);

  useLayoutEffect(() => {
    if (!tourModule) return undefined;
    measure();
    const onResize = () => measure();
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onResize, true);
    const id = window.setInterval(measure, 400);
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onResize, true);
      window.clearInterval(id);
    };
  }, [tourModule, tourStepIndex, measure]);

  // Advance when user clicks the highlighted control (if waitForClick)
  useEffect(() => {
    if (!tourModule || !step?.waitForClick || !step.selector) return undefined;
    const el = pickElement(step.selector);
    if (!el) return undefined;
    const onClick = () => {
      window.setTimeout(() => {
        if (tourStepIndex >= steps.length - 1) closeTour("completed");
        else advanceTour(1);
      }, 120);
    };
    el.addEventListener("click", onClick);
    return () => el.removeEventListener("click", onClick);
  }, [tourModule, step, tourStepIndex, steps.length, advanceTour, closeTour]);

  useEffect(() => {
    if (!tourModule) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") closeTour("skipped");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tourModule, closeTour]);

  if (!tourModule || !step) return null;

  const copyKey = `help.modules.${contentId}.tour.steps.${step.id}`;

  return (
    <div className="pointer-events-none fixed inset-0 z-[85]" data-testid="guided-tour" aria-live="polite">
      {rect ? (
        <div
          data-testid="guided-tour-highlight"
          className="pointer-events-none absolute rounded-xl border-2 border-brand-400 shadow-[0_0_0_9999px_rgba(0,0,0,0.55)]"
          style={{
            top: rect.top,
            left: rect.left,
            width: rect.width,
            height: rect.height,
          }}
        />
      ) : (
        <div className="absolute inset-0 bg-black/35" aria-hidden="true" />
      )}

      <div
        role="dialog"
        aria-modal="false"
        aria-labelledby="guided-tour-title"
        className="pointer-events-auto absolute inset-x-3 bottom-3 mx-auto max-w-md rounded-2xl border border-brand-500/30 bg-zinc-950 p-4 shadow-2xl sm:inset-x-auto sm:bottom-6 sm:right-6"
      >
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-brand-300">
          {t("help.tourProgress", { current: tourStepIndex + 1, total: steps.length })}
        </p>
        <h2 id="guided-tour-title" className="mt-1 text-base font-semibold text-zinc-50" data-testid="guided-tour-title">
          {t(`${copyKey}.title`)}
        </h2>
        <p className="mt-2 text-sm leading-6 text-zinc-300">{t(`${copyKey}.body`)}</p>
        {step.waitForClick ? (
          <p className="mt-2 text-xs text-zinc-500">{t("help.tourClickHint")}</p>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => closeTour("skipped")}
              data-testid="guided-tour-skip"
              className="rounded-lg px-2.5 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
            >
              {t("help.skip")}
            </button>
            <button
              type="button"
              onClick={restartTour}
              data-testid="guided-tour-restart"
              className="rounded-lg px-2.5 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
            >
              {t("help.restart")}
            </button>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={tourStepIndex === 0}
              onClick={() => advanceTour(-1)}
              data-testid="guided-tour-back"
              className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-zinc-200 disabled:opacity-40"
            >
              {t("help.back")}
            </button>
            {last ? (
              <button
                type="button"
                onClick={() => closeTour("completed")}
                data-testid="guided-tour-done"
                className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white"
              >
                {t("help.tourDone")}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  if (step.waitForClick) return;
                  advanceTour(1);
                }}
                data-testid="guided-tour-next"
                className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                disabled={Boolean(step.waitForClick)}
              >
                {t("help.next")}
              </button>
            )}
            <button
              type="button"
              onClick={() => closeTour("skipped")}
              data-testid="guided-tour-close"
              className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-zinc-300"
              aria-label={t("help.close")}
            >
              {t("help.close")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
