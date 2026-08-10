import { Plus } from "lucide-react";

export default function EmptyState({ icon: Icon, title, description, why, actionLabel, onAction, testid }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-zinc-950/40 px-4 py-16 text-center sm:py-20" data-testid={testid}>
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-600/15 text-violet-400" aria-hidden="true">
        <Icon className="h-7 w-7" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-zinc-100">{title}</h3>
      {description && <p className="mt-1 max-w-md text-sm text-zinc-500">{description}</p>}
      {why && <p className="mt-2 max-w-md text-xs text-zinc-600">{why}</p>}
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          data-testid={`${testid}-action`}
          className="mt-5 flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50 glow-violet"
        >
          <Plus className="h-4 w-4" aria-hidden="true" /> {actionLabel}
        </button>
      )}
    </div>
  );
}
