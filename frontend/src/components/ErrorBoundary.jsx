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
    // Optional Sentry when DSN configured via window
    try {
      if (window.Sentry && window.Sentry.captureException) {
        window.Sentry.captureException(error, { extra: info });
      }
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line no-console
    console.error("UI error boundary", error);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-zinc-950 px-6 text-center text-zinc-200" data-testid="error-boundary">
          <h1 className="text-lg font-semibold">Something went wrong</h1>
          <p className="max-w-md text-sm text-zinc-400">An unexpected error occurred. You can reload the page or return home.</p>
          <div className="flex gap-2">
            <button type="button" className="rounded-lg bg-violet-600 px-3 py-2 text-sm" onClick={() => window.location.reload()}>Reload</button>
            <a href="/dashboard" className="rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-300">Dashboard</a>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
