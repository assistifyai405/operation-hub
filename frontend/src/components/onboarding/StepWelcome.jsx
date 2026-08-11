import { useTranslation } from "react-i18next";
import { ArrowRight, Users, FolderKanban, ListTodo, Bot, Sparkles, FileText } from "lucide-react";
import { StepShell, PrimaryBtn, GhostBtn } from "./onboardingShared";

const CAPABILITIES = [
  { icon: Users, key: "clients" },
  { icon: FolderKanban, key: "projects" },
  { icon: ListTodo, key: "tasks" },
  { icon: Sparkles, key: "opportunities" },
  { icon: FileText, key: "documents" },
  { icon: Bot, key: "ai" },
];

export function StepWelcome({ next, onSkip }) {
  const { t } = useTranslation();

  return (
    <StepShell>
      <div data-testid="onb-step-welcome" className="text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 glow-brand">
          <Sparkles className="h-7 w-7 text-white" />
        </div>
        <p className="mt-5 text-xs font-semibold uppercase tracking-[0.2em] text-brand-400">{t("app.name")}</p>
        <h2 className="mt-2 text-3xl font-bold tracking-tight text-zinc-50 sm:text-4xl">
          {t("onboarding.welcomeHeadline")}
        </h2>
        <p className="mx-auto mt-4 max-w-lg text-sm leading-relaxed text-zinc-400">
          {t("onboarding.welcomeBody")}
        </p>

        <div className="mx-auto mt-8 grid max-w-md grid-cols-2 gap-2 sm:grid-cols-3">
          {CAPABILITIES.map(({ icon: Icon, key }) => (
            <div
              key={key}
              className="flex items-center gap-2 rounded-xl border border-white/10 bg-zinc-950/80 px-3 py-2.5 text-left text-sm text-zinc-300"
            >
              <Icon className="h-4 w-4 shrink-0 text-brand-400" />
              {t(`onboarding.capabilities.${key}`)}
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <PrimaryBtn onClick={next} data-testid="onb-welcome-continue">
            {t("onboarding.getStarted")} <ArrowRight className="h-4 w-4" />
          </PrimaryBtn>
          {onSkip && (
            <GhostBtn onClick={onSkip} data-testid="onb-welcome-skip">
              {t("onboarding.skipExplore")}
            </GhostBtn>
          )}
        </div>
        <p className="mt-4 text-xs text-zinc-600">{t("onboarding.takesMinutes")}</p>
      </div>
    </StepShell>
  );
}
