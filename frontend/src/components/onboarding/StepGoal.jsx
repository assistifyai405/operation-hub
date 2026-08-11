import { useTranslation } from "react-i18next";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { toast } from "sonner";
import { StepShell, PrimaryBtn, GhostBtn } from "./onboardingShared";

export const PRIMARY_GOAL_IDS = [
  "win_clients",
  "manage_clients",
  "organize_projects",
  "save_time_ai",
  "create_documents",
  "automate",
];

/** @deprecated Prefer PRIMARY_GOAL_IDS + i18n; kept for callers that still map labels. */
export const PRIMARY_GOALS = PRIMARY_GOAL_IDS.map((id) => ({ id, label: id, hint: id }));

export function StepGoal({ data, setData, next, back }) {
  const { t } = useTranslation();
  const selected = data.primaryGoal || "";

  const choose = (id) => setData((d) => ({ ...d, primaryGoal: id }));

  const cont = () => {
    if (!selected) {
      toast.error(t("onboarding.goalRequired"));
      return;
    }
    next();
  };

  return (
    <StepShell>
      <div data-testid="onb-step-goal">
        <h2 className="text-2xl font-bold tracking-tight text-zinc-50">{t("onboarding.goalTitle")}</h2>
        <p className="mt-2 text-sm text-zinc-500">{t("onboarding.goalBody")}</p>

        <div className="mt-6 grid gap-2 sm:grid-cols-2">
          {PRIMARY_GOAL_IDS.map((id) => {
            const on = selected === id;
            return (
              <button
                key={id}
                type="button"
                onClick={() => choose(id)}
                data-testid={`onb-goal-${id}`}
                className={`flex items-start gap-3 rounded-xl border px-4 py-3.5 text-left transition-all ${
                  on
                    ? "border-brand-500/50 bg-brand-600/15 ring-1 ring-brand-500/30"
                    : "border-white/10 bg-zinc-950 hover:border-brand-500/30"
                }`}
              >
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                    on ? "border-brand-400 bg-brand-500 text-white" : "border-zinc-600"
                  }`}
                >
                  {on && <Check className="h-3 w-3" />}
                </span>
                <span>
                  <span className="block text-sm font-semibold text-zinc-100">{t(`onboarding.goals.${id}.label`)}</span>
                  <span className="mt-0.5 block text-xs text-zinc-500">{t(`onboarding.goals.${id}.hint`)}</span>
                </span>
              </button>
            );
          })}
        </div>

        <div className="mt-8 flex items-center justify-between">
          <GhostBtn onClick={back} data-testid="onb-goal-back">
            <ArrowLeft className="h-4 w-4" /> {t("onboarding.back")}
          </GhostBtn>
          <PrimaryBtn onClick={cont} data-testid="onb-goal-continue">
            {t("onboarding.continue")} <ArrowRight className="h-4 w-4" />
          </PrimaryBtn>
        </div>
      </div>
    </StepShell>
  );
}
