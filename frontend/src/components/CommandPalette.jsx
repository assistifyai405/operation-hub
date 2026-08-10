import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  CommandDialog, CommandInput, CommandList, CommandEmpty,
  CommandGroup, CommandItem, CommandSeparator, CommandShortcut,
} from "@/components/ui/command";
import {
  LayoutDashboard, Users, FolderKanban, CheckSquare, MessageSquare,
  Bot, FileText, FolderOpen, BarChart3, Settings as SettingsIcon,
  Sparkles, ClipboardList, Mail, Search as SearchIcon, Plus,
  Target, Zap, TrendingUp, LayoutGrid, Brain, ScrollText, Receipt, Inbox, Plug,
} from "lucide-react";

/** Keep in sync with Layout nav — only real, available routes. */
const pages = [
  { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard" },
  { label: "Opportunities", icon: Target, to: "/opportunities" },
  { label: "Automations", icon: Zap, to: "/automations" },
  { label: "CRM", icon: Users, to: "/crm" },
  { label: "Pipeline", icon: TrendingUp, to: "/pipeline" },
  { label: "Clients", icon: Users, to: "/clients" },
  { label: "Projects", icon: FolderKanban, to: "/projects" },
  { label: "Tasks", icon: CheckSquare, to: "/tasks" },
  { label: "Copilot", icon: Sparkles, to: "/ai-chat" },
  { label: "AI Workspace", icon: LayoutGrid, to: "/ai-workspace" },
  { label: "Knowledge Brain", icon: Brain, to: "/knowledge-brain" },
  { label: "AI Agents", icon: Bot, to: "/ai-agents" },
  { label: "Proposals", icon: FileText, to: "/proposals" },
  { label: "Contracts", icon: ScrollText, to: "/contracts" },
  { label: "Invoices", icon: Receipt, to: "/invoices" },
  { label: "Documents", icon: FolderOpen, to: "/documents" },
  { label: "Emails", icon: Mail, to: "/emails" },
  { label: "Inbox", icon: Inbox, to: "/inbox" },
  { label: "Integrations", icon: Plug, to: "/integrations" },
  { label: "Analytics", icon: BarChart3, to: "/analytics" },
  { label: "Settings", icon: SettingsIcon, to: "/settings" },
];

const createActions = [
  { label: "New client", icon: Plus, to: "/clients" },
  { label: "New project", icon: FolderKanban, to: "/projects" },
  { label: "New task", icon: CheckSquare, to: "/tasks" },
];

/** AI actions that land on Copilot with a prefilled prompt (handled by AICopilot). */
const aiActions = [
  { label: "Ask Copilot", icon: MessageSquare, prompt: "", to: "/ai-chat" },
  { label: "Create project plan", icon: ClipboardList, prompt: "Create a detailed project plan with milestones.", to: "/ai-chat" },
  { label: "Write follow-up email", icon: Mail, prompt: "Write a polite follow-up email to a client.", to: "/ai-chat" },
  { label: "Research a client", icon: SearchIcon, prompt: "Research and summarize a client company.", to: "/ai-chat" },
  { label: "Draft a proposal outline", icon: FileText, prompt: "Outline a professional business proposal.", to: "/ai-chat" },
];

export default function CommandPalette({ open, setOpen }) {
  const navigate = useNavigate();

  useEffect(() => {
    const down = (e) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [setOpen]);

  const go = (to) => {
    setOpen(false);
    navigate(to);
  };

  const runAi = (a) => {
    setOpen(false);
    if (a.prompt) {
      navigate(`/ai-chat?q=${encodeURIComponent(a.prompt)}`);
    } else {
      navigate(a.to);
    }
  };

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search pages or run an action…" data-testid="command-input" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Create">
          {createActions.map((a) => (
            <CommandItem
              key={a.label}
              value={`create ${a.label}`}
              onSelect={() => go(a.to)}
              data-testid={`cmd-create-${a.label.toLowerCase().replace(/\s/g, "-")}`}
              className="cursor-pointer data-[selected=true]:bg-violet-600/20 data-[selected=true]:text-violet-100"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-600/15 text-emerald-400">
                <a.icon className="h-4 w-4" aria-hidden="true" />
              </span>
              {a.label}
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="AI">
          {aiActions.map((a) => (
            <CommandItem
              key={a.label}
              value={`ai ${a.label}`}
              onSelect={() => runAi(a)}
              data-testid={`cmd-ai-${a.label.toLowerCase().replace(/\s/g, "-")}`}
              className="cursor-pointer data-[selected=true]:bg-violet-600/20 data-[selected=true]:text-violet-100"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-violet-600/15 text-violet-400">
                <a.icon className="h-4 w-4" aria-hidden="true" />
              </span>
              {a.label}
              <CommandShortcut><Sparkles className="h-3.5 w-3.5 text-violet-400" aria-hidden="true" /></CommandShortcut>
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Navigation">
          {pages.map((p) => (
            <CommandItem
              key={p.to}
              value={`go ${p.label}`}
              onSelect={() => go(p.to)}
              data-testid={`cmd-nav-${p.label.toLowerCase().replace(/\s/g, "-")}`}
              className="cursor-pointer data-[selected=true]:bg-violet-600/20 data-[selected=true]:text-violet-100"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-zinc-800/80 text-zinc-400">
                <p.icon className="h-4 w-4" aria-hidden="true" />
              </span>
              {p.label}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
