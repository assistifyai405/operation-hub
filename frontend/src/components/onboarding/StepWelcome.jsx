import { Sparkles, Users, Brain, Zap, ArrowRight, FileText } from "lucide-react";
import { motion } from "framer-motion";
import { StepShell, PrimaryBtn } from "./onboardingShared";

export function StepWelcome({ next }) {
  const pills = [
    { i: Users, t: "Knows your clients & pipeline" },
    { i: Brain, t: "Learns your business" },
    { i: Zap, t: "Works while you sleep" },
  ];
  return (
    <StepShell>
      <div className="text-center" data-testid="onb-step-welcome">
        <motion.div
          initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 15 }}
          className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-violet-600 glow-violet"
        >
          <Sparkles className="h-10 w-10 text-white" />
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="mt-6 text-4xl font-bold tracking-tight text-zinc-50 sm:text-5xl"
        >
          Welcome to Assistify AI
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.28 }}
          className="mx-auto mt-4 max-w-md text-base text-zinc-400"
        >
          Let's set up your AI employee in just a few minutes.
        </motion.p>
        <div className="mx-auto mt-8 flex max-w-lg flex-wrap justify-center gap-2">
          {pills.map((p, i) => (
            <motion.span
              key={p.t} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 + i * 0.1 }}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-zinc-900/60 px-3.5 py-2 text-xs font-medium text-zinc-300"
            >
              <p.i className="h-3.5 w-3.5 text-violet-400" /> {p.t}
            </motion.span>
          ))}
        </div>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.75 }} className="mt-10">
          <PrimaryBtn onClick={next} data-testid="onb-welcome-start">
            Set up my AI employee <ArrowRight className="h-4 w-4" />
          </PrimaryBtn>
        </motion.div>
        <p className="mt-4 text-xs text-zinc-600">Takes ~3 minutes · You can save and continue later.</p>
      </div>
    </StepShell>
  );
}
