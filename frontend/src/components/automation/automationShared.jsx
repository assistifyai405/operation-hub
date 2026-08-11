export const MODE_META = {
  suggest: { label: "Suggest only", short: "Suggest", desc: "Detects and recommends — never prepares or runs.", chip: "bg-sky-500/15 text-sky-300 border-sky-500/30" },
  prepare: { label: "Prepare for approval", short: "Prepare", desc: "Prepares drafts; you confirm before anything runs.", chip: "bg-brand-500/15 text-brand-300 border-brand-500/30" },
  auto: { label: "Fully automatic", short: "Automatic", desc: "Safe internal actions run automatically; risky actions still need approval.", chip: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
};

export const RISK_META = {
  low: { label: "Low risk", chip: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30", dot: "bg-emerald-500" },
  medium: { label: "Needs review", chip: "bg-amber-500/15 text-amber-300 border-amber-500/30", dot: "bg-amber-500" },
  high: { label: "High risk", chip: "bg-red-500/15 text-red-300 border-red-500/30", dot: "bg-red-500" },
};

export const KIND_META = {
  internal: { label: "Internal", chip: "bg-zinc-700/40 text-zinc-300 border-white/10" },
  external: { label: "Client-facing", chip: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  generative: { label: "AI draft", chip: "bg-brand-500/15 text-brand-300 border-brand-500/30" },
  destructive: { label: "Destructive", chip: "bg-red-500/15 text-red-300 border-red-500/30" },
};

export const PAUSE_OPTIONS = [
  { v: "1h", label: "For 1 hour" },
  { v: "tomorrow", label: "Until tomorrow" },
  { v: "1w", label: "For 1 week" },
  { v: "forever", label: "Indefinitely" },
];
