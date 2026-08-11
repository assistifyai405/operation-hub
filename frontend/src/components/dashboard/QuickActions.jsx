import { useNavigate } from "react-router-dom";
import { Users, FolderKanban, ListTodo, Bot, Brain, Zap, LayoutGrid, Sparkles, Target } from "lucide-react";
import { Section } from "./execShared";

const FIRST_RUN = [
  { label: "New Client", icon: Users, to: "/clients", primary: true },
  { label: "New Project", icon: FolderKanban, to: "/projects", primary: true },
  { label: "Ask Copilot", icon: Sparkles, to: "/ai-chat", primary: true },
  { label: "AI Agents", icon: Bot, to: "/ai-agents" },
  { label: "New Task", icon: ListTodo, to: "/tasks" },
];

const WITH_DATA = [
  { label: "Ask Copilot", icon: Sparkles, to: "/ai-chat", primary: true },
  { label: "New Client", icon: Users, to: "/clients" },
  { label: "New Project", icon: FolderKanban, to: "/projects" },
  { label: "Opportunities", icon: Target, to: "/opportunities" },
  { label: "Pipeline", icon: Target, to: "/pipeline" },
  { label: "AI Agents", icon: Bot, to: "/ai-agents" },
  { label: "Knowledge Brain", icon: Brain, to: "/knowledge-brain" },
  { label: "AI Workspace", icon: LayoutGrid, to: "/ai-workspace" },
  { label: "Automations", icon: Zap, to: "/automations" },
];

export function QuickActions({ firstRun = false }) {
  const navigate = useNavigate();
  const actions = firstRun ? FIRST_RUN : WITH_DATA;
  return (
    <Section title={firstRun ? "Suggested next steps" : "Quick Actions"} icon={Sparkles} testid="quick-actions-section">
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
        {actions.map((a) => (
          <button
            key={a.label}
            type="button"
            onClick={() => navigate(a.to)}
            data-testid={`quick-action-${a.label.toLowerCase().replace(/\s+/g, "-")}`}
            className={`flex items-center gap-2.5 rounded-xl border px-3.5 py-3 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 ${
              a.primary
                ? "border-brand-500/30 bg-brand-600/10 text-brand-100 hover:bg-brand-600/20"
                : "border-white/10 bg-zinc-950 text-zinc-300 hover:border-brand-500/40 hover:text-white"
            }`}
          >
            <a.icon className={`h-4 w-4 ${a.primary ? "text-brand-300" : "text-brand-400"}`} aria-hidden="true" /> {a.label}
          </button>
        ))}
      </div>
    </Section>
  );
}
