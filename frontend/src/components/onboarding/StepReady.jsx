import { useTranslation } from "react-i18next";
import { ArrowRight, Users, FolderKanban, Bot, Sparkles, ListTodo } from "lucide-react";
import { StepShell, PrimaryBtn, GhostBtn } from "./onboardingShared";

const NEXT_BY_GOAL = {
  win_clients: [
    { labelKey: "createClient", to: "/clients", icon: Users, primary: true },
    { labelKey: "askOutreach", to: "/ai-chat", icon: Sparkles },
    { labelKey: "exploreAgents", to: "/ai-agents", icon: Bot },
  ],
  manage_clients: [
    { labelKey: "createClient", to: "/clients", icon: Users, primary: true },
    { labelKey: "openOpportunities", to: "/opportunities", icon: Sparkles },
    { labelKey: "askCopilot", to: "/ai-chat", icon: Bot },
  ],
  organize_projects: [
    { labelKey: "createProject", to: "/projects", icon: FolderKanban, primary: true },
    { labelKey: "addTask", to: "/tasks", icon: ListTodo },
    { labelKey: "askPlan", to: "/ai-chat", icon: Sparkles },
  ],
  save_time_ai: [
    { labelKey: "askCopilot", to: "/ai-chat", icon: Sparkles, primary: true },
    { labelKey: "exploreAgents", to: "/ai-agents", icon: Bot },
    { labelKey: "createClient", to: "/clients", icon: Users },
  ],
  create_documents: [
    { labelKey: "projectForDocs", to: "/projects", icon: FolderKanban, primary: true },
    { labelKey: "askProposal", to: "/ai-chat", icon: Sparkles },
    { labelKey: "exploreAgents", to: "/ai-agents", icon: Bot },
  ],
  automate: [
    { labelKey: "exploreAutomations", to: "/automations", icon: Sparkles, primary: true },
    { labelKey: "askCopilot", to: "/ai-chat", icon: Bot },
    { labelKey: "createClient", to: "/clients", icon: Users },
  ],
};

const DEFAULT_NEXT = [
  { labelKey: "createClient", to: "/clients", icon: Users, primary: true },
  { labelKey: "askCopilot", to: "/ai-chat", icon: Sparkles },
  { labelKey: "exploreAgents", to: "/ai-agents", icon: Bot },
  { labelKey: "createProject", to: "/projects", icon: FolderKanban },
];

export function StepReady({ data, finish }) {
  const { t } = useTranslation();
  const goalId = data.primaryGoal;
  const company = data.company?.company_name || data.company?.name || t("app.name");
  const actions = NEXT_BY_GOAL[goalId] || DEFAULT_NEXT;
  const goalLabel = goalId ? t(`onboarding.goals.${goalId}.label`) : "";

  return (
    <StepShell>
      <div data-testid="onb-step-ready" className="text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/15 text-emerald-400">
          <Sparkles className="h-7 w-7" />
        </div>
        <h2 className="mt-5 text-3xl font-bold tracking-tight text-zinc-50">
          {t("onboarding.readyTitle", { company })}
        </h2>
        <p className="mx-auto mt-3 max-w-md text-sm text-zinc-400">
          {goalId
            ? t("onboarding.readyBodyGoal", { goal: goalLabel })
            : t("onboarding.readyBody")}
        </p>

        <div className="mx-auto mt-8 grid max-w-lg gap-2 text-left">
          {actions.map((a) => {
            const Icon = a.icon;
            const label = t(`onboarding.actions.${a.labelKey}`);
            return (
              <button
                key={`${a.to}-${a.labelKey}`}
                type="button"
                onClick={() => finish(a.to)}
                data-testid={`onb-ready-${a.to.replace(/\//g, "") || "home"}`}
                className={`flex items-center gap-3 rounded-xl border px-4 py-3.5 transition-all ${
                  a.primary
                    ? "border-brand-500/40 bg-brand-600/15 hover:bg-brand-600/25"
                    : "border-white/10 bg-zinc-950 hover:border-brand-500/30"
                }`}
              >
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-900 text-brand-400">
                  <Icon className="h-4 w-4" />
                </span>
                <span className="flex-1 text-sm font-semibold text-zinc-100">{label}</span>
                <ArrowRight className="h-4 w-4 text-zinc-500" />
              </button>
            );
          })}
        </div>

        <div className="mt-8">
          <PrimaryBtn onClick={() => finish("/dashboard")} data-testid="onb-ready-dashboard">
            {t("onboarding.openDashboard")} <ArrowRight className="h-4 w-4" />
          </PrimaryBtn>
          <div className="mt-3">
            <GhostBtn onClick={() => finish("/dashboard")} data-testid="onb-ready-later">
              {t("onboarding.skipExplore")}
            </GhostBtn>
          </div>
        </div>
      </div>
    </StepShell>
  );
}
