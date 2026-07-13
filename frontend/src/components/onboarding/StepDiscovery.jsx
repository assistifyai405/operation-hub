import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import { Brain, ArrowRight, Loader2 } from "lucide-react";
import { onboardingApi } from "@/lib/api";
import { StepShell, CheckLine, PrimaryBtn } from "./onboardingShared";

const SEQUENCE = [
  "Learning your business",
  "Creating your company profile",
  "Preparing your CRM",
  "Building your Knowledge Brain",
  "Configuring your AI Assistant",
  "Preparing smart automations",
  "Setting up your AI Workspace",
  "Personalizing your writing style",
];

export function StepDiscovery({ data, setData, next }) {
  const [visible, setVisible] = useState(0);
  const [ready, setReady] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    // Animate the sequence
    SEQUENCE.forEach((_, i) => setTimeout(() => setVisible(i + 1), 500 + i * 650));
    // Real work in parallel
    onboardingApi.generateProfile(data.company || {})
      .then((r) => setData((d) => ({ ...d, profile: r.sections, automations: r.automations })))
      .catch(() => {})
      .finally(() => setTimeout(() => setReady(true), 500 + SEQUENCE.length * 650));
  }, [data.company, setData]);

  return (
    <StepShell>
      <div className="text-center" data-testid="onb-step-discovery">
        <motion.div
          animate={{ rotate: ready ? 0 : [0, 8, -8, 0] }} transition={{ repeat: ready ? 0 : Infinity, duration: 2 }}
          className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-600 glow-violet"
        >
          <Brain className="h-8 w-8 text-white" />
        </motion.div>
        <h2 className="mt-5 text-2xl font-bold text-zinc-50">Building your AI employee</h2>
        <p className="mt-2 text-sm text-zinc-500">Assistify is studying your business and setting everything up.</p>

        <div className="mx-auto mt-7 max-w-sm space-y-1 text-left">
          {SEQUENCE.slice(0, visible).map((s, i) => (
            <CheckLine key={s} done={ready || i < visible - 1} delay={0}>{s}</CheckLine>
          ))}
        </div>

        <div className="mt-9">
          <PrimaryBtn onClick={next} disabled={!ready} data-testid="onb-discovery-continue">
            {ready ? <>See what I learned <ArrowRight className="h-4 w-4" /></> : <><Loader2 className="h-4 w-4 animate-spin" /> Setting up…</>}
          </PrimaryBtn>
        </div>
      </div>
    </StepShell>
  );
}
