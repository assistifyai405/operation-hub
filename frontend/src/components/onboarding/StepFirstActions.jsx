import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Users, FolderKanban, CheckSquare, Sparkles } from "lucide-react";
import { StepShell, PrimaryBtn, GhostBtn } from "./onboardingShared";

const ACTIONS = [
  { key: "client", icon: Users, to: "/clients" },
  { key: "project", icon: FolderKanban, to: "/projects" },
  { key: "task", icon: CheckSquare, to: "/tasks" },
  { key: "copilot", icon: Sparkles, to: "/ai-chat" },
];

/**
 * Guided setup prompts — links to real pages. Never auto-creates data.
 */
export function StepFirstActions({ next, back, onSkip }) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <StepShell>
      <div data-testid="onb-step-first-actions" className="mx-auto max-w-xl">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-400">{t("onboarding.firstActions.eyebrow")}</p>
        <h2 className="mt-2 text-3xl font-bold tracking-tight text-zinc-50">{t("onboarding.firstActions.title")}</h2>
        <p className="mt-3 text-sm leading-relaxed text-zinc-400">{t("onboarding.firstActions.body")}</p>

        <ul className="mt-8 space-y-3">
          {ACTIONS.map(({ key, icon: Icon, to }, index) => (
            <li key={key}>
              <button
                type="button"
                data-testid={`onb-action-${key}`}
                onClick={() => navigate(to)}
                className="flex w-full items-center gap-3 rounded-xl border border-white/10 bg-zinc-950/80 px-4 py-3 text-left transition-colors hover:border-brand-500/40"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600/15 text-sm font-bold text-brand-300">
                  {index + 1}
                </span>
                <Icon className="h-4 w-4 shrink-0 text-brand-400" aria-hidden="true" />
                <span className="flex-1">
                  <span className="block text-sm font-semibold text-zinc-100">{t(`onboarding.firstActions.items.${key}.title`)}</span>
                  <span className="block text-xs text-zinc-500">{t(`onboarding.firstActions.items.${key}.body`)}</span>
                </span>
                <ArrowRight className="h-4 w-4 text-zinc-600" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>

        <p className="mt-4 text-xs text-zinc-600">{t("onboarding.firstActions.note")}</p>

        <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
          <GhostBtn onClick={back} data-testid="onb-first-actions-back">{t("common.back")}</GhostBtn>
          <div className="flex flex-wrap gap-2">
            {onSkip ? (
              <GhostBtn onClick={onSkip} data-testid="onb-first-actions-skip">{t("onboarding.skipExplore")}</GhostBtn>
            ) : null}
            <PrimaryBtn onClick={next} data-testid="onb-first-actions-continue">
              {t("onboarding.continue")} <ArrowRight className="h-4 w-4" />
            </PrimaryBtn>
          </div>
        </div>
      </div>
    </StepShell>
  );
}
