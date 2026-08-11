import { useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
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

/** Synonyms so Dutch/English terms both find modules. */
const SYNONYMS = {
  dashboard: "dashboard overzicht",
  opportunities: "opportunities kansen",
  automations: "automations automatiseringen",
  crm: "crm relaties",
  pipeline: "pipeline pijplijn deals",
  clients: "clients klanten",
  projects: "projects projecten",
  tasks: "tasks taken",
  copilot: "copilot assistent",
  aiWorkspace: "ai workspace werkruimte",
  knowledgeBrain: "knowledge brain kennis",
  aiAgents: "ai agents agenten",
  proposals: "proposals offertes voorstellen",
  contracts: "contracts contracten",
  invoices: "invoices facturen",
  documents: "documents documenten",
  emails: "emails e-mails",
  inbox: "inbox postvak",
  integrations: "integrations integraties",
  analytics: "analytics analyses",
  settings: "settings instellingen",
};

export default function CommandPalette({ open, setOpen }) {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const pages = useMemo(() => [
    { key: "dashboard", icon: LayoutDashboard, to: "/dashboard" },
    { key: "opportunities", icon: Target, to: "/opportunities" },
    { key: "automations", icon: Zap, to: "/automations" },
    { key: "crm", icon: Users, to: "/crm" },
    { key: "pipeline", icon: TrendingUp, to: "/pipeline" },
    { key: "clients", icon: Users, to: "/clients" },
    { key: "projects", icon: FolderKanban, to: "/projects" },
    { key: "tasks", icon: CheckSquare, to: "/tasks" },
    { key: "copilot", icon: Sparkles, to: "/ai-chat" },
    { key: "aiWorkspace", icon: LayoutGrid, to: "/ai-workspace" },
    { key: "knowledgeBrain", icon: Brain, to: "/knowledge-brain" },
    { key: "aiAgents", icon: Bot, to: "/ai-agents" },
    { key: "proposals", icon: FileText, to: "/proposals" },
    { key: "contracts", icon: ScrollText, to: "/contracts" },
    { key: "invoices", icon: Receipt, to: "/invoices" },
    { key: "documents", icon: FolderOpen, to: "/documents" },
    { key: "emails", icon: Mail, to: "/emails" },
    { key: "inbox", icon: Inbox, to: "/inbox" },
    { key: "integrations", icon: Plug, to: "/integrations" },
    { key: "analytics", icon: BarChart3, to: "/analytics" },
    { key: "settings", icon: SettingsIcon, to: "/settings" },
  ], []);

  const createActions = useMemo(() => [
    { label: t("command.newClient"), icon: Plus, to: "/clients", value: "create client klant" },
    { label: t("command.newProject"), icon: FolderKanban, to: "/projects", value: "create project project" },
    { label: t("command.newTask"), icon: CheckSquare, to: "/tasks", value: "create task taak" },
  ], [t]);

  const aiActions = useMemo(() => [
    { label: t("firstRun.copilot"), icon: MessageSquare, prompt: "", to: "/ai-chat" },
    { label: t("command.aiPlan"), icon: ClipboardList, prompt: "Create a detailed project plan with milestones.", to: "/ai-chat" },
    { label: t("command.aiFollowUp"), icon: Mail, prompt: "Write a polite follow-up email to a client.", to: "/ai-chat" },
    { label: t("command.aiResearch"), icon: SearchIcon, prompt: "Research and summarize a client company.", to: "/ai-chat" },
    { label: t("command.aiProposal"), icon: FileText, prompt: "Outline a professional business proposal.", to: "/ai-chat" },
  ], [t]);

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
      <CommandInput placeholder={t("command.placeholder")} data-testid="command-input" />
      <CommandList>
        <CommandEmpty>{t("command.empty")}</CommandEmpty>
        <CommandGroup heading={t("command.create")}>
          {createActions.map((a) => (
            <CommandItem
              key={a.to}
              value={a.value}
              onSelect={() => go(a.to)}
              data-testid={`cmd-create-${a.to.replace("/", "")}`}
              className="cursor-pointer data-[selected=true]:bg-brand-600/20 data-[selected=true]:text-brand-100"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-600/15 text-emerald-400">
                <a.icon className="h-4 w-4" aria-hidden="true" />
              </span>
              {a.label}
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading={t("command.ai")}>
          {aiActions.map((a) => (
            <CommandItem
              key={a.label}
              value={`ai ${a.label}`}
              onSelect={() => runAi(a)}
              data-testid={`cmd-ai-${a.label.toLowerCase().replace(/\s/g, "-")}`}
              className="cursor-pointer data-[selected=true]:bg-brand-600/20 data-[selected=true]:text-brand-100"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-600/15 text-brand-400">
                <a.icon className="h-4 w-4" aria-hidden="true" />
              </span>
              {a.label}
              <CommandShortcut><Sparkles className="h-3.5 w-3.5 text-brand-400" aria-hidden="true" /></CommandShortcut>
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading={t("command.pages")}>
          {pages.map((p) => {
            const label = t(`nav.${p.key}`);
            const syn = SYNONYMS[p.key] || p.key;
            return (
              <CommandItem
                key={p.to}
                value={`go ${label} ${syn}`}
                onSelect={() => go(p.to)}
                data-testid={`cmd-nav-${p.key}`}
                className="cursor-pointer data-[selected=true]:bg-brand-600/20 data-[selected=true]:text-brand-100"
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-md bg-zinc-800/80 text-zinc-400">
                  <p.icon className="h-4 w-4" aria-hidden="true" />
                </span>
                {label}
              </CommandItem>
            );
          })}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
