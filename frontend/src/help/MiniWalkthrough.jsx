import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useHelp } from "@/help/HelpContext";
import { getHelpModule } from "@/help/registry";

/**
 * Scripted CRM mini walkthrough — sandboxed mock UI, no real workspace writes.
 */
export default function MiniWalkthrough() {
  const { t } = useTranslation();
  const { tutorialModule, closeTutorial } = useHelp();
  const [step, setStep] = useState(0);
  const mod = tutorialModule ? getHelpModule(tutorialModule) : null;
  const contentId = mod?.contentId || tutorialModule;

  const steps = useMemo(() => {
    const raw = t(`help.modules.${contentId}.tutorial.steps`, { returnObjects: true });
    return Array.isArray(raw) ? raw : [];
  }, [t, contentId]);

  useEffect(() => {
    setStep(0);
  }, [tutorialModule]);

  useEffect(() => {
    if (!tutorialModule) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") closeTutorial("skipped");
      if (e.key === "ArrowRight") setStep((s) => Math.min(steps.length - 1, s + 1));
      if (e.key === "ArrowLeft") setStep((s) => Math.max(0, s - 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tutorialModule, closeTutorial, steps.length]);

  if (!tutorialModule || !steps.length) return null;

  const current = steps[step] || {};
  const last = step >= steps.length - 1;

  return (
    <div className="fixed inset-0 z-[90] flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-6" data-testid="mini-walkthrough" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="mini-walkthrough-title"
        className="flex max-h-[94vh] w-full max-w-2xl flex-col overflow-hidden rounded-t-3xl border border-white/10 bg-zinc-950 shadow-2xl sm:rounded-3xl"
      >
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-brand-300">
              {t(`help.modules.${contentId}.tutorial.title`)}
            </p>
            <h2 id="mini-walkthrough-title" className="mt-1 text-lg font-semibold text-zinc-50">
              {current.title}
            </h2>
          </div>
          <button
            type="button"
            onClick={() => closeTutorial("skipped")}
            data-testid="mini-walkthrough-close"
            className="rounded-lg p-2 text-zinc-400 hover:bg-white/5 hover:text-white"
            aria-label={t("help.close")}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-5">
          <CrmTutorialStage stage={current.stage || step} label={current.visual} />
          <p className="mt-5 text-sm leading-6 text-zinc-300">{current.body}</p>
          <p className="mt-3 text-xs text-zinc-500" data-testid="mini-walkthrough-progress">
            {t("help.tutorialProgress", { current: step + 1, total: steps.length })}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 px-5 py-4">
          <button
            type="button"
            onClick={() => closeTutorial("skipped")}
            data-testid="mini-walkthrough-skip"
            className="rounded-lg px-3 py-2 text-sm text-zinc-400 hover:text-zinc-200"
          >
            {t("help.skip")}
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={step === 0}
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              data-testid="mini-walkthrough-back"
              className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-200 disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
              {t("help.back")}
            </button>
            {last ? (
              <button
                type="button"
                onClick={() => closeTutorial("completed")}
                data-testid="mini-walkthrough-done"
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500"
              >
                {t("help.done")}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setStep((s) => Math.min(steps.length - 1, s + 1))}
                data-testid="mini-walkthrough-next"
                className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500"
              >
                {t("help.next")}
                <ChevronRight className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** Isolated visual demo — example labels only, never writes to the workspace. */
function CrmTutorialStage({ stage, label }) {
  const highlights = {
    0: "nav",
    1: "new",
    2: "form",
    3: "save",
    4: "stage",
    5: "note",
    6: "board",
  };
  const active = highlights[stage] || highlights[0];

  return (
    <div
      className="overflow-hidden rounded-2xl border border-white/10 bg-zinc-900"
      data-testid="crm-tutorial-stage"
      aria-label={label || "CRM tutorial demo"}
    >
      <div className="flex items-center gap-2 border-b border-white/10 px-3 py-2">
        <span className="h-2 w-2 rounded-full bg-zinc-600" />
        <span className="h-2 w-2 rounded-full bg-zinc-600" />
        <span className="h-2 w-2 rounded-full bg-zinc-600" />
        <span className="ml-2 text-[11px] text-zinc-500">Assistify · CRM</span>
      </div>
      <div className="grid gap-3 p-3 sm:grid-cols-[110px_1fr]">
        <aside className={`space-y-1.5 rounded-xl border p-2 text-[11px] ${active === "nav" ? "border-brand-500/50 bg-brand-500/10 text-brand-200" : "border-white/5 text-zinc-500"}`}>
          <div>Dashboard</div>
          <div className={active === "nav" ? "font-semibold text-brand-200" : ""}>CRM / Pipeline</div>
          <div>Clients</div>
        </aside>
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold text-zinc-200">Pipeline</p>
            <span className={`rounded-md px-2 py-1 text-[10px] font-semibold ${active === "new" ? "bg-brand-600 text-white ring-2 ring-brand-300" : "bg-zinc-800 text-zinc-400"}`}>
              + New lead
            </span>
          </div>
          <div className={`rounded-xl border p-3 ${active === "form" || active === "save" ? "border-brand-500/40 bg-brand-500/5" : "border-white/10 bg-zinc-950"}`}>
            <div className={`h-7 rounded-md border px-2 text-[10px] leading-7 ${active === "form" ? "border-brand-500/50 text-zinc-200" : "border-white/10 text-zinc-500"}`}>
              Acme redesign inquiry
            </div>
            <div className="mt-2 flex gap-2">
              <span className={`rounded-md px-2 py-1 text-[10px] ${active === "save" ? "bg-brand-600 text-white ring-2 ring-brand-300" : "bg-zinc-800 text-zinc-500"}`}>Save</span>
              <span className={`rounded-md px-2 py-1 text-[10px] ${active === "stage" ? "bg-brand-600/20 text-brand-200 ring-1 ring-brand-500/40" : "bg-zinc-800 text-zinc-500"}`}>Stage: New → Contacted</span>
            </div>
            <div className={`mt-2 rounded-md border px-2 py-1.5 text-[10px] ${active === "note" ? "border-brand-500/40 text-zinc-200" : "border-white/10 text-zinc-600"}`}>
              Note: Schedule intro call next week
            </div>
          </div>
          <div className={`rounded-xl border p-2 ${active === "board" ? "border-brand-500/40 bg-brand-500/5" : "border-white/10"}`}>
            <div className="grid grid-cols-3 gap-1.5">
              {["New", "Contacted", "Qualified"].map((col) => (
                <div key={col} className="rounded-lg bg-zinc-950 p-1.5">
                  <p className="text-[9px] text-zinc-500">{col}</p>
                  {col === "Contacted" && active === "board" ? (
                    <div className="mt-1 rounded bg-brand-600/20 px-1.5 py-1 text-[9px] text-brand-100">Acme redesign</div>
                  ) : (
                    <div className="mt-1 h-6 rounded bg-zinc-900" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
