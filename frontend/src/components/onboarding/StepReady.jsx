import { ArrowRight, Users, FolderKanban, Bot, Sparkles, ListTodo } from "lucide-react";
import { PRIMARY_GOALS } from "./StepGoal";
import { StepShell, PrimaryBtn, GhostBtn } from "./onboardingShared";

const NEXT_BY_GOAL = {
  win_clients: [
    { label: "Create your first client", to: "/clients", icon: Users, primary: true },
    { label: "Ask Copilot for outreach ideas", to: "/ai-chat", icon: Sparkles },
    { label: "Explore AI Agents", to: "/ai-agents", icon: Bot },
  ],
  manage_clients: [
    { label: "Create your first client", to: "/clients", icon: Users, primary: true },
    { label: "Open Opportunities", to: "/opportunities", icon: Sparkles },
    { label: "Ask Copilot", to: "/ai-chat", icon: Bot },
  ],
  organize_projects: [
    { label: "Create your first project", to: "/projects", icon: FolderKanban, primary: true },
    { label: "Add a task", to: "/tasks", icon: ListTodo },
    { label: "Ask Copilot to draft a plan", to: "/ai-chat", icon: Sparkles },
  ],
  save_time_ai: [
    { label: "Ask Copilot", to: "/ai-chat", icon: Sparkles, primary: true },
    { label: "Explore AI Agents", to: "/ai-agents", icon: Bot },
    { label: "Create your first client", to: "/clients", icon: Users },
  ],
  create_documents: [
    { label: "Create a project for documents", to: "/projects", icon: FolderKanban, primary: true },
    { label: "Ask Copilot to draft a proposal", to: "/ai-chat", icon: Sparkles },
    { label: "Explore AI Agents", to: "/ai-agents", icon: Bot },
  ],
  automate: [
    { label: "Explore Automations", to: "/automations", icon: Sparkles, primary: true },
    { label: "Ask Copilot", to: "/ai-chat", icon: Bot },
    { label: "Create your first client", to: "/clients", icon: Users },
  ],
};

const DEFAULT_NEXT = [
  { label: "Create your first client", to: "/clients", icon: Users, primary: true },
  { label: "Ask Copilot", to: "/ai-chat", icon: Sparkles },
  { label: "Explore AI Agents", to: "/ai-agents", icon: Bot },
  { label: "Create your first project", to: "/projects", icon: FolderKanban },
];

export function StepReady({ data, finish }) {
  const goal = PRIMARY_GOALS.find((g) => g.id === data.primaryGoal);
  const company = data.company?.company_name || data.company?.name || "your workspace";
  const actions = NEXT_BY_GOAL[data.primaryGoal] || DEFAULT_NEXT;

  return (
    <StepShell>
      <div data-testid="onb-step-ready" className="text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/15 text-emerald-400">
          <Sparkles className="h-7 w-7" />
        </div>
        <h2 className="mt-5 text-3xl font-bold tracking-tight text-zinc-50">
          {company} is ready
        </h2>
        <p className="mx-auto mt-3 max-w-md text-sm text-zinc-400">
          {goal
            ? `You chose “${goal.label}”. Here are the best next steps to get real value today.`
            : "Here are the best next steps to get real value today."}
        </p>

        <div className="mx-auto mt-8 grid max-w-lg gap-2 text-left">
          {actions.map((a) => {
            const Icon = a.icon;
            return (
              <button
                key={a.label}
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
                <span className="flex-1 text-sm font-semibold text-zinc-100">{a.label}</span>
                <ArrowRight className="h-4 w-4 text-zinc-500" />
              </button>
            );
          })}
        </div>

        <div className="mt-8">
          <PrimaryBtn onClick={() => finish("/dashboard")} data-testid="onb-ready-dashboard">
            Go to dashboard <ArrowRight className="h-4 w-4" />
          </PrimaryBtn>
          <div className="mt-3">
            <GhostBtn onClick={() => finish("/dashboard")} data-testid="onb-ready-later">
              I&apos;ll explore on my own
            </GhostBtn>
          </div>
        </div>
      </div>
    </StepShell>
  );
}
