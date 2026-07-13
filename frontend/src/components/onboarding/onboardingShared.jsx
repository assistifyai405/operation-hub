import { motion } from "framer-motion";
import { Check } from "lucide-react";

export const STEP_LABELS = ["Welcome", "Company", "AI setup", "Knowledge Brain", "Automations", "Workspace", "First win", "Done"];

export function ProgressRail({ step }) {
  return (
    <div className="flex items-center gap-1.5" data-testid="onboarding-progress">
      {STEP_LABELS.map((l, i) => (
        <div key={l} className="flex items-center gap-1.5">
          <span
            className={`h-1.5 rounded-full transition-all duration-500 ${i === step ? "w-8 bg-violet-500" : i < step ? "w-4 bg-violet-500/60" : "w-4 bg-zinc-800"}`}
            title={l}
          />
        </div>
      ))}
    </div>
  );
}

export function StepShell({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="mx-auto w-full max-w-2xl"
    >
      {children}
    </motion.div>
  );
}

export function Field({ label, children, hint, testid }) {
  return (
    <div data-testid={testid}>
      <label className="mb-1 block text-xs font-medium text-zinc-400">{label}</label>
      {children}
      {hint && <p className="mt-1 text-[11px] text-zinc-600">{hint}</p>}
    </div>
  );
}

export const inputCls = "w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-100 outline-none transition-colors focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40";

export function PrimaryBtn({ children, ...props }) {
  return (
    <button {...props} className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-6 py-3 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-50 glow-violet">
      {children}
    </button>
  );
}

export function GhostBtn({ children, ...props }) {
  return (
    <button {...props} className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-5 py-3 text-sm font-medium text-zinc-300 transition-all hover:bg-zinc-900 hover:text-zinc-100">
      {children}
    </button>
  );
}

export function CheckLine({ done, children, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay }}
      className="flex items-center gap-3 rounded-lg px-1 py-1.5"
    >
      <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full transition-all ${done ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-800 text-zinc-600"}`}>
        {done ? <Check className="h-3.5 w-3.5" /> : <span className="h-2 w-2 animate-pulse rounded-full bg-violet-500" />}
      </span>
      <span className={`text-sm ${done ? "text-zinc-200" : "text-zinc-500"}`}>{children}</span>
    </motion.div>
  );
}
