import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Info, Trash2, Loader2 } from "lucide-react";
import { onboardingApi } from "@/lib/api";

export default function DemoDataBanner() {
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [hidden, setHidden] = useState(false);

  useEffect(() => { onboardingApi.demoStatus().then(setStatus).catch(() => {}); }, []);

  if (!status?.has_demo || hidden) return null;

  const clear = async () => {
    if (!window.confirm("Remove all demo/sample data? This clears sample clients, projects, leads, documents, memories and automation history. Your real data stays.")) return;
    setBusy(true);
    try {
      await onboardingApi.clearDemo();
      toast.success("Demo data cleared");
      setHidden(true);
      setTimeout(() => window.location.reload(), 400);
    } catch (e) { toast.error(e.message); setBusy(false); }
  };

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-amber-500/25 bg-amber-500/10 px-4 py-3" data-testid="demo-data-banner">
      <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-300">Demo</span>
      <Info className="h-4 w-4 shrink-0 text-amber-400" />
      <p className="text-sm text-amber-100">Your workspace includes sample data so it never feels empty. Clear it whenever you're ready to work with your own.</p>
      <button onClick={clear} disabled={busy} data-testid="clear-demo-btn" className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-amber-500/40 px-3 py-1.5 text-xs font-medium text-amber-200 transition-all hover:bg-amber-500/15 disabled:opacity-50">
        {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />} Clear demo data
      </button>
    </div>
  );
}
