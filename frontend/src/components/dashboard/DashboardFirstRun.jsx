import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Users, FolderKanban, Bot, Sparkles, ArrowRight } from "lucide-react";

const ACTIONS = [
  {
    labelKey: "firstRun.client",
    hintKey: "firstRun.clientHint",
    to: "/clients",
    icon: Users,
    primary: true,
    testid: "first-run-client",
  },
  {
    labelKey: "firstRun.project",
    hintKey: "firstRun.projectHint",
    to: "/projects",
    icon: FolderKanban,
    testid: "first-run-project",
  },
  {
    labelKey: "firstRun.copilot",
    hintKey: "firstRun.copilotHint",
    to: "/ai-chat",
    icon: Sparkles,
    testid: "first-run-copilot",
  },
  {
    labelKey: "firstRun.agents",
    hintKey: "firstRun.agentsHint",
    to: "/ai-agents",
    icon: Bot,
    testid: "first-run-agents",
  },
];

export function DashboardFirstRun() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <div
      className="rounded-2xl border border-brand-500/25 bg-gradient-to-br from-brand-600/10 via-transparent to-transparent p-6 sm:p-8 theme-surface"
      data-testid="dashboard-first-run"
    >
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-400">{t("firstRun.eyebrow")}</p>
      <h2 className="mt-2 text-xl font-bold tracking-tight text-zinc-50 sm:text-2xl">
        {t("firstRun.title", { defaultValue: "Let's get your workspace working for you." })}
      </h2>
      <p className="mt-2 max-w-xl text-sm text-zinc-400">
        {t("firstRun.body", { defaultValue: "Your dashboard stays empty until you add real clients, projects, and tasks — no sample charts or fake scores. Pick a starting point below." })}
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
                  ? "border-brand-500/40 bg-brand-600/15 hover:bg-brand-600/25"
                  : "border-white/10 bg-zinc-900/60 hover:border-brand-500/30"
              }`}
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-brand-400">
                <Icon className="h-4 w-4" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold text-zinc-100">{t(a.labelKey)}</span>
                <span className="mt-0.5 block text-xs text-zinc-500">{t(a.hintKey)}</span>
              </span>
              <ArrowRight className="h-4 w-4 shrink-0 text-zinc-600" aria-hidden="true" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
