import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import { LayoutGrid, ArrowRight, ArrowLeft, Loader2, Users, FolderKanban, TrendingUp, Sparkles, Inbox } from "lucide-react";
import { onboardingApi } from "@/lib/api";
import { StepShell, PrimaryBtn, GhostBtn } from "./onboardingShared";

export function StepDemo({ next, back }) {
  const [counts, setCounts] = useState(null);
  const [loading, setLoading] = useState(true);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    onboardingApi.seedDemo().then((r) => setCounts(r.counts)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const cards = [
    { i: Users, label: "Clients", k: "clients", color: "text-violet-300" },
    { i: FolderKanban, label: "Projects", k: "projects", color: "text-cyan-300" },
    { i: TrendingUp, label: "Pipeline leads", k: "leads", color: "text-emerald-300" },
    { i: Sparkles, label: "AI actions", k: "ai_activities", color: "text-amber-300" },
    { i: Inbox, label: "Approvals ready", k: "approvals", color: "text-pink-300" },
  ];

  return (
    <StepShell>
      <div data-testid="onb-step-demo">
        <div className="mb-5 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-600/15 text-violet-400"><LayoutGrid className="h-5 w-5" /></span>
          <div>
            <h2 className="text-2xl font-bold text-zinc-50">Your workspace, already alive</h2>
            <p className="text-sm text-zinc-500">We added realistic sample data so you can explore right away.</p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-zinc-950 py-16 text-zinc-500" data-testid="onb-demo-loading">
            <Loader2 className="h-5 w-5 animate-spin" /> Generating your demo workspace…
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5" data-testid="onb-demo-counts">
              {cards.map((c, i) => (
                <motion.div key={c.k} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
                  className="rounded-2xl border border-white/10 bg-zinc-950 p-4 text-center">
                  <c.i className={`mx-auto h-5 w-5 ${c.color}`} />
                  <p className="mt-2 text-2xl font-bold text-zinc-50">{counts?.[c.k] ?? 0}</p>
                  <p className="text-[11px] text-zinc-500">{c.label}</p>
                </motion.div>
              ))}
            </div>
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-2.5 text-xs text-amber-200" data-testid="onb-demo-label">
              <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide">Demo</span>
              This is sample data, clearly labeled throughout the app. You can clear it anytime from the dashboard or Settings.
            </div>
          </>
        )}

        <div className="mt-8 flex items-center justify-between">
          <GhostBtn onClick={back}><ArrowLeft className="h-4 w-4" /> Back</GhostBtn>
          <PrimaryBtn onClick={next} disabled={loading} data-testid="onb-demo-continue">Continue <ArrowRight className="h-4 w-4" /></PrimaryBtn>
        </div>
      </div>
    </StepShell>
  );
}
