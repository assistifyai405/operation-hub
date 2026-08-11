export const MODE_META = {
  suggest: { labelKey: "automations.meta.modes.suggest.label", shortKey: "automations.meta.modes.suggest.short", descKey: "automations.meta.modes.suggest.description", chip: "bg-sky-500/15 text-sky-300 border-sky-500/30" },
  prepare: { labelKey: "automations.meta.modes.prepare.label", shortKey: "automations.meta.modes.prepare.short", descKey: "automations.meta.modes.prepare.description", chip: "bg-brand-500/15 text-brand-300 border-brand-500/30" },
  auto: { labelKey: "automations.meta.modes.auto.label", shortKey: "automations.meta.modes.auto.short", descKey: "automations.meta.modes.auto.description", chip: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
};

export const RISK_META = {
  low: { labelKey: "automations.meta.risks.low", chip: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30", dot: "bg-emerald-500" },
  medium: { labelKey: "automations.meta.risks.medium", chip: "bg-amber-500/15 text-amber-300 border-amber-500/30", dot: "bg-amber-500" },
  high: { labelKey: "automations.meta.risks.high", chip: "bg-red-500/15 text-red-300 border-red-500/30", dot: "bg-red-500" },
};

export const KIND_META = {
  internal: { labelKey: "automations.meta.kinds.internal", chip: "bg-zinc-700/40 text-zinc-300 border-white/10" },
  external: { labelKey: "automations.meta.kinds.external", chip: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  generative: { labelKey: "automations.meta.kinds.generative", chip: "bg-brand-500/15 text-brand-300 border-brand-500/30" },
  destructive: { labelKey: "automations.meta.kinds.destructive", chip: "bg-red-500/15 text-red-300 border-red-500/30" },
};

export const PAUSE_OPTIONS = [
  { v: "1h", labelKey: "automations.pauseOptions.1h" },
  { v: "tomorrow", labelKey: "automations.pauseOptions.tomorrow" },
  { v: "1w", labelKey: "automations.pauseOptions.1w" },
  { v: "forever", labelKey: "automations.pauseOptions.forever" },
];
