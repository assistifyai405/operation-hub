import { useEffect, useId, useRef } from "react";
import { Check, Play, Sparkles, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { getHelpModule } from "@/help/registry";
import { useHelp } from "@/help/HelpContext";

function asList(value) {
  return Array.isArray(value) ? value : [];
}

/**
 * Side panel (desktop) / bottom sheet (mobile) with module help.
 */
export default function HelpPanel() {
  const { t } = useTranslation();
  const { panelModule, closeHelp, startTutorial, startTour } = useHelp();
  const titleId = useId();
  const closeRef = useRef(null);
  const mod = panelModule ? getHelpModule(panelModule) : null;
  const contentId = mod?.contentId || panelModule;

  useEffect(() => {
    if (!panelModule) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") closeHelp();
    };
    window.addEventListener("keydown", onKey);
    const tmr = setTimeout(() => closeRef.current?.focus(), 40);
    return () => {
      window.removeEventListener("keydown", onKey);
      clearTimeout(tmr);
    };
  }, [panelModule, closeHelp]);

  if (!panelModule || !mod) return null;

  const learn = asList(t(`help.modules.${contentId}.learn`, { returnObjects: true }));
  const tips = asList(t(`help.modules.${contentId}.quickTips`, { returnObjects: true }));
  const duration = t(`help.modules.${contentId}.tutorial.duration`, { defaultValue: "" });

  return (
    <div className="fixed inset-0 z-[80]" data-testid="help-panel" role="presentation">
      <button
        type="button"
        className="absolute inset-0 bg-black/50 backdrop-blur-[2px]"
        aria-label={t("help.close")}
        onClick={closeHelp}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="absolute inset-x-0 bottom-0 flex max-h-[92vh] flex-col rounded-t-3xl border border-white/10 bg-zinc-950 shadow-2xl sm:inset-y-0 sm:left-auto sm:right-0 sm:max-h-none sm:w-full sm:max-w-md sm:rounded-none sm:rounded-l-3xl"
      >
        <div className="flex items-start justify-between gap-3 border-b border-white/10 px-5 py-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-brand-300">{t("help.panelEyebrow")}</p>
            <h2 id={titleId} className="mt-1 text-xl font-semibold text-zinc-50" data-testid="help-panel-title">
              {t(`help.modules.${contentId}.title`)}
            </h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={closeHelp}
            data-testid="help-panel-close"
            className="rounded-lg p-2 text-zinc-400 hover:bg-white/5 hover:text-white"
            aria-label={t("help.close")}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
          <p className="text-sm leading-6 text-zinc-300" data-testid="help-panel-description">
            {t(`help.modules.${contentId}.description`)}
          </p>

          {mod.hasFullTutorial ? (
            <button
              type="button"
              onClick={() => startTutorial(contentId)}
              data-testid="help-start-tutorial"
              className="flex w-full items-center gap-3 rounded-2xl border border-brand-500/30 bg-brand-500/10 px-4 py-3 text-left transition-colors hover:bg-brand-500/15"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white">
                <Play className="h-4 w-4" aria-hidden="true" />
              </span>
              <span>
                <span className="block text-sm font-semibold text-zinc-50">{t("help.watchTutorial")}</span>
                {duration ? <span className="mt-0.5 block text-xs text-zinc-400">{duration}</span> : null}
              </span>
            </button>
          ) : null}

          {learn.length > 0 ? (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">{t("help.youLearn")}</p>
              <ul className="mt-3 space-y-2">
                {learn.map((item) => (
                  <li key={item} className="flex gap-2 text-sm text-zinc-300">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-brand-400" aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {tips.length > 0 ? (
            <div className="rounded-2xl border border-white/10 bg-zinc-900/70 p-4">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                <Sparkles className="h-3.5 w-3.5 text-brand-400" aria-hidden="true" />
                {t("help.quickTips")}
              </p>
              <ul className="mt-3 space-y-2">
                {tips.map((tip) => (
                  <li key={tip} className="text-sm leading-6 text-zinc-400">{tip}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {mod.betaLimited ? (
            <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs leading-5 text-amber-100">
              {t(`help.modules.${contentId}.betaNote`, { defaultValue: t("help.betaDefault") })}
            </p>
          ) : null}

          {mod.hasGuidedTour ? (
            <button
              type="button"
              onClick={() => startTour(mod.id)}
              data-testid="help-try-yourself"
              className="w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-500"
            >
              {t("help.tryYourself")}
            </button>
          ) : null}

          <p className="text-xs text-zinc-600">{t("help.moreHelp")}</p>
        </div>
      </aside>
    </div>
  );
}
