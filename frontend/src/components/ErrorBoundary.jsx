import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    try {
      if (window.Sentry && window.Sentry.captureException) {
        window.Sentry.captureException(error, { extra: info });
      }
    } catch {
      /* ignore */
    }
    if (process.env.NODE_ENV === "development") {
      // eslint-disable-next-line no-console
      console.error("UI error boundary", error, info);
    }
  }

  handleRetry = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      const isDev = process.env.NODE_ENV === "development";
      return (
        <div
          className="flex min-h-screen flex-col items-center justify-center gap-4 bg-zinc-950 px-6 text-center text-zinc-200"
          data-testid="error-boundary"
          role="alert"
        >
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-600/15 text-violet-400" aria-hidden="true">
            <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.75">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
            </svg>
          </div>
          <h1 className="text-lg font-semibold text-zinc-50">Something went wrong</h1>
          <p className="max-w-md text-sm text-zinc-400">
            Assistify hit an unexpected problem. Your data is safe — reload the page or return to the dashboard to continue.
          </p>
          {isDev && this.state.error?.message && (
            <pre className="max-w-lg overflow-auto rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-left text-[11px] text-zinc-500" data-testid="error-boundary-dev">
              {String(this.state.error.message)}
            </pre>
          )}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <button
              type="button"
              data-testid="error-boundary-reload"
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50"
              onClick={() => window.location.reload()}
            >
              Reload page
            </button>
            <button
              type="button"
              data-testid="error-boundary-retry"
              className="rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50"
              onClick={this.handleRetry}
            >
              Try again
            </button>
            <a
              href="/dashboard"
              data-testid="error-boundary-home"
              className="rounded-lg border border-white/10 px-4 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50"
            >
              Go to dashboard
            </a>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
