import { motion } from "framer-motion";
import { HeartPulse } from "lucide-react";
import { Section, healthTone } from "./execShared";

function Ring({ score }) {
  const tone = healthTone(score);
  const r = 46, circ = 2 * Math.PI * r, off = circ - (score / 100) * circ;
  return (
    <div className="relative flex h-32 w-32 items-center justify-center" data-testid="health-ring">
      <svg className="h-32 w-32 -rotate-90" viewBox="0 0 110 110">
        <circle cx="55" cy="55" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="9" />
        <motion.circle cx="55" cy="55" r={r} fill="none" stroke={tone.bar} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={circ} initial={{ strokeDashoffset: circ }} animate={{ strokeDashoffset: off }} transition={{ duration: 1, ease: "easeOut" }} />
      </svg>
      <div className="absolute text-center">
        <p className={`text-3xl font-bold ${tone.text}`} data-testid="health-score">{score}</p>
        <p className="text-[10px] uppercase tracking-wide text-zinc-500">/ 100</p>
      </div>
    </div>
  );
}

export function HealthScore({ health }) {
  return (
    <Section title="Business Health Score" icon={HeartPulse} testid="health-section">
      <div className="rounded-2xl border border-white/10 bg-zinc-950 p-5">
        <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start">
          <div className="flex flex-col items-center">
            <Ring score={health.score} />
            <span className={`mt-2 rounded-full px-3 py-1 text-xs font-semibold ${healthTone(health.score).chip}`}>{health.grade}</span>
          </div>
          <div className="min-w-0 flex-1 space-y-2.5">
            {health.categories.map((c) => {
              const tone = healthTone(c.score);
              return (
                <div key={c.name} data-testid={`health-cat-${c.name.replace(/\s/g, "-")}`}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="font-medium text-zinc-200">{c.name}</span>
                    <span className={tone.text}>{c.score}/100</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-zinc-800">
                    <motion.div className="h-full rounded-full" style={{ background: tone.bar }} initial={{ width: 0 }} animate={{ width: `${c.score}%` }} transition={{ duration: 0.7 }} />
                  </div>
                  <p className="mt-1 text-[11px] text-zinc-500">{c.reasons?.[0]}</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Section>
  );
}
