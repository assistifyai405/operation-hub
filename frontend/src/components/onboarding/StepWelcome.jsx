import { ArrowRight, Users, FolderKanban, ListTodo, Bot, Sparkles, FileText, Zap } from "lucide-react";
import { StepShell, PrimaryBtn, GhostBtn } from "./onboardingShared";

const CAPABILITIES = [
  { icon: Users, label: "Clients" },
  { icon: FolderKanban, label: "Projects" },
  { icon: ListTodo, label: "Tasks" },
  { icon: Sparkles, label: "Opportunities" },
  { icon: FileText, label: "Documents" },
  { icon: Bot, label: "AI workflows" },
];

export function StepWelcome({ next, onSkip }) {
  return (
    <StepShell>
      <div data-testid="onb-step-welcome" className="text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 glow-brand">
          <Sparkles className="h-7 w-7 text-white" />
        </div>
        <p className="mt-5 text-xs font-semibold uppercase tracking-[0.2em] text-brand-400">Assistify OS</p>
        <h2 className="mt-2 text-3xl font-bold tracking-tight text-zinc-50 sm:text-4xl">
          Your AI-powered business operating system.
        </h2>
        <p className="mx-auto mt-4 max-w-lg text-sm leading-relaxed text-zinc-400">
          Assistify helps small businesses, freelancers, and teams manage work and use AI from one workspace —
          without juggling separate tools for clients, projects, and documents.
        </p>

        <div className="mx-auto mt-8 grid max-w-md grid-cols-2 gap-2 sm:grid-cols-3">
          {CAPABILITIES.map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-2 rounded-xl border border-white/10 bg-zinc-950/80 px-3 py-2.5 text-left text-sm text-zinc-300"
            >
              <Icon className="h-4 w-4 shrink-0 text-brand-400" />
              {label}
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <PrimaryBtn onClick={next} data-testid="onb-welcome-continue">
            Get started <ArrowRight className="h-4 w-4" />
          </PrimaryBtn>
          {onSkip && (
            <GhostBtn onClick={onSkip} data-testid="onb-welcome-skip">
              Skip setup — explore the workspace
            </GhostBtn>
          )}
        </div>
        <p className="mt-4 text-xs text-zinc-600">Takes about 2 minutes. You can change everything later in Settings.</p>
      </div>
    </StepShell>
  );
}
