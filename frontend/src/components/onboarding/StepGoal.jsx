import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { toast } from "sonner";
import { StepShell, PrimaryBtn, GhostBtn } from "./onboardingShared";

export const PRIMARY_GOALS = [
  { id: "win_clients", label: "Win more clients", hint: "Pipeline, outreach, proposals" },
  { id: "manage_clients", label: "Manage clients", hint: "Relationships, follow-ups, CRM" },
  { id: "organize_projects", label: "Organize projects", hint: "Plans, tasks, delivery" },
  { id: "save_time_ai", label: "Save time with AI", hint: "Copilot, agents, summaries" },
  { id: "create_documents", label: "Create proposals & documents", hint: "Proposals, contracts, invoices" },
  { id: "automate", label: "Automate repetitive work", hint: "Rules, reminders, hand-offs" },
];

export function StepGoal({ data, setData, next, back }) {
  const selected = data.primaryGoal || "";

  const choose = (id) => setData((d) => ({ ...d, primaryGoal: id }));

  const cont = () => {
    if (!selected) {
      toast.error("Pick what you mainly want help with");
      return;
    }
    next();
  };

  return (
    <StepShell>
      <div data-testid="onb-step-goal">
        <h2 className="text-2xl font-bold tracking-tight text-zinc-50">What do you mainly want help with?</h2>
        <p className="mt-2 text-sm text-zinc-500">
          We&apos;ll highlight the most relevant next steps. You can change this later.
        </p>

        <div className="mt-6 grid gap-2 sm:grid-cols-2">
          {PRIMARY_GOALS.map((g) => {
            const on = selected === g.id;
            return (
              <button
                key={g.id}
                type="button"
                onClick={() => choose(g.id)}
                data-testid={`onb-goal-${g.id}`}
                className={`flex items-start gap-3 rounded-xl border px-4 py-3.5 text-left transition-all ${
                  on
                    ? "border-violet-500/50 bg-violet-600/15 ring-1 ring-violet-500/30"
                    : "border-white/10 bg-zinc-950 hover:border-violet-500/30"
                }`}
              >
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                    on ? "border-violet-400 bg-violet-500 text-white" : "border-zinc-600"
                  }`}
                >
                  {on && <Check className="h-3 w-3" />}
                </span>
                <span>
                  <span className="block text-sm font-semibold text-zinc-100">{g.label}</span>
                  <span className="mt-0.5 block text-xs text-zinc-500">{g.hint}</span>
                </span>
              </button>
            );
          })}
        </div>

        <div className="mt-8 flex items-center justify-between">
          <GhostBtn onClick={back} data-testid="onb-goal-back">
            <ArrowLeft className="h-4 w-4" /> Back
          </GhostBtn>
          <PrimaryBtn onClick={cont} data-testid="onb-goal-continue">
            Continue <ArrowRight className="h-4 w-4" />
          </PrimaryBtn>
        </div>
      </div>
    </StepShell>
  );
}
