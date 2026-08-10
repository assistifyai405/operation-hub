import { useNavigate } from "react-router-dom";
import { Users, FolderKanban, Bot, Sparkles, ArrowRight } from "lucide-react";

const ACTIONS = [
  {
    label: "Create your first client",
    hint: "Start tracking relationships and work",
    to: "/clients",
    icon: Users,
    primary: true,
    testid: "first-run-client",
  },
  {
    label: "Create your first project",
    hint: "Organize delivery around a client",
    to: "/projects",
    icon: FolderKanban,
    testid: "first-run-project",
  },
  {
    label: "Ask Copilot",
    hint: "Summaries, drafts, plans, and more",
    to: "/ai-chat",
    icon: Sparkles,
    testid: "first-run-copilot",
  },
  {
    label: "Explore AI Agents",
    hint: "Specialists for sales, ops, and writing",
    to: "/ai-agents",
    icon: Bot,
    testid: "first-run-agents",
  },
];

export function DashboardFirstRun() {
  const navigate = useNavigate();
  return (
    <div
      className="rounded-2xl border border-violet-500/25 bg-gradient-to-br from-violet-600/10 via-zinc-950/80 to-transparent p-6 sm:p-8"
      data-testid="dashboard-first-run"
    >
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-400">Welcome</p>
      <h2 className="mt-2 text-xl font-bold tracking-tight text-zinc-50 sm:text-2xl">
        Let&apos;s get your workspace working for you.
      </h2>
      <p className="mt-2 max-w-xl text-sm text-zinc-400">
        Your dashboard stays empty until you add real clients, projects, and tasks — no sample charts or fake scores.
        Pick a starting point below.
      </p>
      <div className="mt-6 grid gap-2 sm:grid-cols-2">
        {ACTIONS.map((a) => {
          const Icon = a.icon;
          return (
            <button
              key={a.to}
              type="button"
              onClick={() => navigate(a.to)}
              data-testid={a.testid}
              className={`flex items-center gap-3 rounded-xl border px-4 py-3.5 text-left transition-all ${
                a.primary
                  ? "border-violet-500/40 bg-violet-600/15 hover:bg-violet-600/25"
                  : "border-white/10 bg-zinc-950/80 hover:border-violet-500/30"
              }`}
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-violet-400">
                <Icon className="h-4 w-4" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold text-zinc-100">{a.label}</span>
                <span className="mt-0.5 block text-xs text-zinc-500">{a.hint}</span>
              </span>
              <ArrowRight className="h-4 w-4 shrink-0 text-zinc-600" aria-hidden="true" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
