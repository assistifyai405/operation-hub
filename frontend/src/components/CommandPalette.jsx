import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  CommandDialog, CommandInput, CommandList, CommandEmpty,
  CommandGroup, CommandItem, CommandSeparator, CommandShortcut,
} from "@/components/ui/command";
import {
  LayoutDashboard, Users, FolderKanban, CheckSquare, MessageSquare,
  Bot, FileText, FolderOpen, BarChart3, Settings as SettingsIcon,
  Sparkles, FilePlus, ClipboardList, Mail, Search as SearchIcon, Plus,
} from "lucide-react";

const pages = [
  { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard" },
  { label: "Clients", icon: Users, to: "/clients" },
  { label: "Projects", icon: FolderKanban, to: "/projects" },
  { label: "Tasks", icon: CheckSquare, to: "/tasks" },
  { label: "AI Chat", icon: MessageSquare, to: "/ai-chat" },
  { label: "AI Agents", icon: Bot, to: "/ai-agents" },
  { label: "Proposals", icon: FileText, to: "/proposals" },
  { label: "Documents", icon: FolderOpen, to: "/documents" },
  { label: "Analytics", icon: BarChart3, to: "/analytics" },
  { label: "Settings", icon: SettingsIcon, to: "/settings" },
];

const aiActions = [
  { label: "Create proposal", icon: FilePlus, agent: "writer", prompt: "Draft a professional business proposal.", to: "/proposals" },
  { label: "Create project plan", icon: ClipboardList, agent: "copilot", prompt: "Create a detailed project plan with milestones.", to: "/ai-chat" },
  { label: "Write follow-up email", icon: Mail, agent: "sales", prompt: "Write a polite follow-up email to a client.", to: "/ai-chat" },
  { label: "Research a client", icon: SearchIcon, agent: "analyst", prompt: "Research and summarize a client company.", to: "/ai-chat" },
  { label: "Create task", icon: Plus, agent: "copilot", prompt: "Create a new task with priority and due date.", to: "/tasks" },
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
    toast.success(`AI action: ${a.label}`, { description: "Routing to your AI workspace…" });
    navigate(a.agent && a.to === "/ai-chat" ? `/ai-chat?agent=${a.agent}` : a.to);
  };

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search pages or run an AI action…" data-testid="command-input" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="AI Quick Actions">
          {aiActions.map((a) => (
            <CommandItem
              key={a.label}
              value={`ai ${a.label}`}
              onSelect={() => runAi(a)}
              data-testid={`cmd-ai-${a.label.toLowerCase().replace(/\s/g, "-")}`}
              className="cursor-pointer data-[selected=true]:bg-violet-600/20 data-[selected=true]:text-violet-100"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-violet-600/15 text-violet-400">
                <a.icon className="h-4 w-4" />
              </span>
              {a.label}
              <CommandShortcut><Sparkles className="h-3.5 w-3.5 text-violet-400" /></CommandShortcut>
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
                <p.icon className="h-4 w-4" />
              </span>
              {p.label}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
