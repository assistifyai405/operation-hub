import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Users, TrendingUp, FolderKanban, ListTodo, FolderOpen, Brain, Zap, Sparkles, FileText, ScrollText, Receipt } from "lucide-react";
import { Section } from "./execShared";

export function WorkspaceSnapshot({ workspace }) {
  const navigate = useNavigate();
  const items = [
    { k: "clients", label: "Clients", icon: Users, to: "/clients" },
    { k: "deals", label: "Open Deals", icon: TrendingUp, to: "/pipeline" },
    { k: "projects", label: "Projects", icon: FolderKanban, to: "/projects" },
    { k: "tasks", label: "Open Tasks", icon: ListTodo, to: "/tasks" },
    { k: "documents", label: "Documents", icon: FolderOpen, to: "/documents" },
    { k: "memories", label: "Memories", icon: Brain, to: "/knowledge-brain" },
    { k: "automations", label: "Automations", icon: Zap, to: "/automations" },
    { k: "ai_reports", label: "AI Actions", icon: Sparkles, to: "/ai-workspace" },
    { k: "proposals", label: "Proposals", icon: FileText, to: "/projects" },
    { k: "contracts", label: "Contracts", icon: ScrollText, to: "/projects" },
    { k: "invoices", label: "Invoices", icon: Receipt, to: "/projects" },
  ];
  return (
    <Section title="Workspace Snapshot" icon={FolderKanban} testid="workspace-section">
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        {items.map((it, i) => (
          <motion.button key={it.k} onClick={() => navigate(it.to)} initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.03 }}
            className="rounded-2xl border border-white/10 bg-zinc-950 p-4 text-left transition-all hover:border-brand-500/40" data-testid={`workspace-${it.k}`}>
            <it.icon className="h-4 w-4 text-brand-400" />
            <p className="mt-2 text-xl font-bold tracking-tight text-zinc-50">{workspace[it.k] ?? 0}</p>
            <p className="text-[11px] text-zinc-500">{it.label}</p>
          </motion.button>
        ))}
      </div>
    </Section>
  );
}
