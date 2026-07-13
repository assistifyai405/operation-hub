import { useNavigate } from "react-router-dom";
import { FileText, ScrollText, Receipt, ListChecks, Users, Bot, Brain, Zap, LayoutGrid, Sparkles } from "lucide-react";
import { Section } from "./execShared";

const ACTIONS = [
  { label: "Generate Proposal", icon: FileText, to: "/projects", primary: true },
  { label: "Generate Contract", icon: ScrollText, to: "/projects", primary: true },
  { label: "Generate Invoice", icon: Receipt, to: "/projects", primary: true },
  { label: "Generate Project Plan", icon: ListChecks, to: "/projects", primary: true },
  { label: "Open CRM", icon: Users, to: "/pipeline" },
  { label: "Ask AI", icon: Bot, to: "/ai-chat" },
  { label: "Knowledge Brain", icon: Brain, to: "/knowledge-brain" },
  { label: "Automations", icon: Zap, to: "/automations" },
  { label: "Workspace", icon: LayoutGrid, to: "/ai-workspace" },
  { label: "Assistant", icon: Sparkles, to: "/ai-chat" },
];

export function QuickActions() {
  const navigate = useNavigate();
  return (
    <Section title="Quick Actions" icon={Sparkles} testid="quick-actions-section">
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
        {ACTIONS.map((a) => (
          <button key={a.label} onClick={() => navigate(a.to)} data-testid={`quick-action-${a.label.toLowerCase().replace(/\s+/g, "-")}`}
            className={`flex items-center gap-2.5 rounded-xl border px-3.5 py-3 text-sm font-medium transition-all ${a.primary ? "border-violet-500/30 bg-violet-600/10 text-violet-100 hover:bg-violet-600/20" : "border-white/10 bg-zinc-950 text-zinc-300 hover:border-violet-500/40 hover:text-white"}`}>
            <a.icon className={`h-4 w-4 ${a.primary ? "text-violet-300" : "text-violet-400"}`} /> {a.label}
          </button>
        ))}
      </div>
    </Section>
  );
}
