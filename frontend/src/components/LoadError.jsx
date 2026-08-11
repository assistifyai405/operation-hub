import { AlertTriangle, RefreshCw } from "lucide-react";

/**
 * Friendly API failure state — distinct from empty data.
 */
export function LoadError({
  title = "Couldn't load this page",
  message = "Something went wrong while loading. Check your connection and try again.",
  onRetry,
  testid = "load-error",
}) {
  return (
    <div
      className="flex flex-col items-center justify-center rounded-xl border border-dashed border-red-500/20 bg-zinc-950/40 px-4 py-16 text-center"
      data-testid={testid}
      role="alert"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-red-500/10 text-red-400" aria-hidden="true">
        <AlertTriangle className="h-6 w-6" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-zinc-100">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-zinc-500">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          data-testid={`${testid}-retry`}
          className="mt-5 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" /> Try again
        </button>
      )}
    </div>
  );
}
