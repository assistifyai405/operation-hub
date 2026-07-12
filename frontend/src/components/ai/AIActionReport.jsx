import { useEffect, useState } from "react";
import {
  CheckCircle2, Check, Clock, Sparkles, Lightbulb, ShieldCheck,
  Eye, Pencil, Download, FileText, Send,
} from "lucide-react";
import { aiApi } from "@/lib/api";
import { fmtDuration } from "@/components/ai/aiHelpers";

const fmtSecs = (ms) => {
  if (!ms || ms < 0) return "just now";
  const s = ms / 1000;
  return s < 1 ? "under 1s" : `${s.toFixed(1)}s`;
};

function Skeleton() {
  return (
    <div className="space-y-4" data-testid="ai-report-skeleton">
      <div className="h-24 animate-pulse rounded-2xl bg-zinc-900" />
      <div className="grid gap-4 md:grid-cols-2">
        <div className="h-56 animate-pulse rounded-2xl bg-zinc-900" />
        <div className="h-56 animate-pulse rounded-2xl bg-zinc-900" />
      </div>
    </div>
  );
}

export function AIActionReport({ report, durationMs, actions = {} }) {
  const [lifetime, setLifetime] = useState(null);
  const [ready, setReady] = useState(false);
  const [ts] = useState(() => new Date());

  useEffect(() => {
    aiApi.timeSaved()
      .then((d) => setLifetime(d?.lifetime ?? null))
      .catch(() => setLifetime(null))
      .finally(() => setReady(true));
  }, []);

  if (!ready) return <Skeleton />;

  const conf = report.confidence || 95;
  const confColor = conf >= 95 ? "#34d399" : conf >= 90 ? "#a78bfa" : "#fbbf24";

  const btn = (key, Icon, label, primary) =>
    actions[key] ? (
      <button key={key} onClick={actions[key]} data-testid={`report-${key}`}
        className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold transition-all ${primary ? "bg-violet-600 text-white hover:bg-violet-500 glow-violet" : "border border-white/10 bg-zinc-900 text-zinc-200 hover:text-white"}`}>
        <Icon className="h-4 w-4" /> {label}
      </button>
    ) : null;

  return (
    <div className="animate-fade-up space-y-4" data-testid="ai-action-report">
      {/* 1. Success banner */}
      <div className="relative overflow-hidden rounded-2xl border border-emerald-500/25 bg-gradient-to-br from-emerald-500/10 via-zinc-950 to-zinc-950 p-5 sm:p-6">
        <div className="flex items-start gap-4">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-500/15">
            <CheckCircle2 className="h-6 w-6 text-emerald-400 ai-pop" />
          </span>
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-zinc-50" data-testid="report-success-title">Your {report.type_label} has been generated successfully.</h2>
            <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-400">
              <span className="inline-flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5 text-violet-400" /> {report.type_label}</span>
              <span className="inline-flex items-center gap-1.5"><Clock className="h-3.5 w-3.5" /> Generated in {fmtSecs(durationMs)}</span>
              <span>{ts.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* 2. What the AI did */}
        <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5" data-testid="report-checklist">
          <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-100"><Sparkles className="h-4 w-4 text-violet-400" /> What Assistify did</p>
          <div className="space-y-2">
            {report.steps.map((s, i) => (
              <div key={i} className="flex items-center gap-2.5 text-sm ai-pop" style={{ animationDelay: `${i * 70}ms` }}>
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-emerald-500/40 bg-emerald-500/15"><Check className="h-3 w-3 text-emerald-400" /></span>
                <span className="text-zinc-300">{s}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 3 + 4. Time saved & Confidence */}
        <div className="space-y-4">
          <div className="rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-600/10 to-zinc-950 p-5" data-testid="report-time-saved">
            <p className="flex items-center gap-1.5 text-xs text-zinc-500"><Clock className="h-3.5 w-3.5" /> Time saved</p>
            <p className="mt-1 text-sm text-zinc-300">You saved approximately</p>
            <p className="text-3xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-violet-300 to-cyan-300">{report.time_saved} minutes</p>
            {lifetime != null && <p className="mt-2 text-xs text-zinc-500">Lifetime time saved · <b className="text-zinc-300" data-testid="report-lifetime">{fmtDuration(lifetime)}</b></p>}
          </div>

          <div className="flex items-center gap-4 rounded-2xl border border-white/10 bg-zinc-950 p-5" data-testid="report-confidence">
            <div className="relative flex h-16 w-16 shrink-0 items-center justify-center rounded-full"
              style={{ background: `conic-gradient(${confColor} ${conf * 3.6}deg, rgba(255,255,255,0.08) 0deg)` }}>
              <div className="flex h-[52px] w-[52px] items-center justify-center rounded-full bg-zinc-950">
                <span className="text-base font-bold text-zinc-50" data-testid="report-confidence-value">{conf}%</span>
              </div>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-zinc-100">AI Confidence</p>
              <p className="mt-0.5 text-xs leading-snug text-zinc-400">{report.confidence_note}</p>
            </div>
          </div>
        </div>
      </div>

      {/* 5. Why */}
      <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5" data-testid="report-why">
        <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-100"><Lightbulb className="h-4 w-4 text-amber-400" /> Why Assistify made these decisions</p>
        <ul className="space-y-2">
          {report.why.map((w, i) => (
            <li key={i} className="flex gap-2.5 text-sm leading-snug text-zinc-300"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-violet-500" />{w}</li>
          ))}
        </ul>
      </div>

      {/* 7. Quality indicators */}
      <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5" data-testid="report-quality">
        <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-100"><ShieldCheck className="h-4 w-4 text-emerald-400" /> Quality indicators</p>
        <div className="flex flex-wrap gap-2">
          {report.quality.map((q, i) => (
            <span key={i} className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
              <Check className="h-3 w-3" /> {q}
            </span>
          ))}
        </div>
      </div>

      {/* 6. Suggested next steps */}
      <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-white/10 bg-zinc-950 p-4" data-testid="report-actions">
        <span className="mr-auto text-xs font-semibold uppercase tracking-wide text-zinc-500">Suggested next steps</span>
        {btn("onReview", Eye, "Review Document", true)}
        {btn("onEdit", Pencil, "Edit")}
        {btn("onDownloadPdf", Download, "Download PDF")}
        {btn("onExportWord", FileText, "Export Word")}
        {btn("onSend", Send, "Send to Client")}
      </div>
    </div>
  );
}
