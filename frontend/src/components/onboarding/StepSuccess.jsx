import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { PartyPopper, Brain, Bot, Zap, LayoutGrid, FileText, ArrowRight, Sparkles } from "lucide-react";
import { StepShell, PrimaryBtn, GhostBtn } from "./onboardingShared";

const SUMMARY = [
  { i: Brain, t: "Business profile created" },
  { i: Sparkles, t: "Knowledge Brain active" },
  { i: Bot, t: "AI Assistant active" },
  { i: Zap, t: "Automations enabled" },
  { i: LayoutGrid, t: "Workspace ready" },
];

export function StepSuccess({ data, finish, onComplete }) {
  const done = useRef(false);
  useEffect(() => { if (!done.current) { done.current = true; onComplete(); } }, [onComplete]);
  const pid = data.firstProjectId;

  return (
    <StepShell>
      <div className="relative text-center" data-testid="onb-step-success">
        {/* subtle burst */}
        <div className="pointer-events-none absolute inset-x-0 top-0 flex justify-center">
          {[...Array(9)].map((_, i) => (
            <motion.span key={i}
              initial={{ opacity: 0, y: 0, x: 0 }}
              animate={{ opacity: [0, 1, 0], y: [-4, -60 - i * 6], x: (i - 4) * 26 }}
              transition={{ duration: 1.6, delay: 0.1 + i * 0.05 }}
              className={`absolute h-2 w-2 rounded-full ${["bg-brand-500", "bg-cyan-400", "bg-emerald-400", "bg-amber-400", "bg-pink-400"][i % 5]}`} />
          ))}
        </div>

        <motion.div initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: "spring", stiffness: 200, damping: 14 }}
          className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-brand-600 glow-brand">
          <PartyPopper className="h-10 w-10 text-white" />
        </motion.div>

        <h2 className="mt-6 text-3xl font-bold tracking-tight text-zinc-50 sm:text-4xl">🎉 Your AI employee is ready</h2>
        <p className="mx-auto mt-3 max-w-md text-sm text-zinc-400">Everything's set up and working for you. Here's what's live:</p>

        <div className="mx-auto mt-6 flex max-w-lg flex-wrap justify-center gap-2" data-testid="onb-success-summary">
          {SUMMARY.map((s, i) => (
            <motion.span key={s.t} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 + i * 0.08 }}
              className="inline-flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-200">
              <s.i className="h-3.5 w-3.5" /> {s.t}
            </motion.span>
          ))}
        </div>

        <div className="mx-auto mt-9 flex max-w-md flex-col items-center gap-3">
          {pid ? (
            <PrimaryBtn onClick={() => finish(`/projects/${pid}?tab=proposal`)} data-testid="onb-cta-proposal" className="w-full justify-center">
              <FileText className="h-4 w-4" /> Open the Proposal Generator <ArrowRight className="h-4 w-4" />
            </PrimaryBtn>
          ) : (
            <PrimaryBtn onClick={() => finish("/projects")} data-testid="onb-cta-proposal" className="w-full justify-center">
              <FileText className="h-4 w-4" /> Create your first document <ArrowRight className="h-4 w-4" />
            </PrimaryBtn>
          )}
          <div className="flex w-full flex-wrap justify-center gap-2">
            <GhostBtn onClick={() => finish("/ai-workspace")} data-testid="onb-cta-workspace"><LayoutGrid className="h-4 w-4" /> Explore Workspace</GhostBtn>
            <GhostBtn onClick={() => finish("/ai-chat")} data-testid="onb-cta-assistant"><Bot className="h-4 w-4" /> Open AI Assistant</GhostBtn>
          </div>
        </div>
      </div>
    </StepShell>
  );
}
