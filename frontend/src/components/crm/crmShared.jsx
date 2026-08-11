import { useNavigate } from "react-router-dom";
import { crmApi } from "@/lib/api";

export const STAGES = ["New", "Qualified", "Meeting Scheduled", "Proposal Sent", "Negotiating", "Won", "Lost"];

export const STAGE_META = {
  "New": { dot: "bg-cyan-400", text: "text-cyan-300", bar: "border-t-cyan-500/50" },
  "Qualified": { dot: "bg-blue-400", text: "text-blue-300", bar: "border-t-blue-500/50" },
  "Meeting Scheduled": { dot: "bg-brand-400", text: "text-brand-300", bar: "border-t-brand-500/50" },
  "Proposal Sent": { dot: "bg-amber-400", text: "text-amber-300", bar: "border-t-amber-500/50" },
  "Negotiating": { dot: "bg-orange-400", text: "text-orange-300", bar: "border-t-orange-500/50" },
  "Won": { dot: "bg-emerald-400", text: "text-emerald-300", bar: "border-t-emerald-500/50" },
  "Lost": { dot: "bg-zinc-500", text: "text-zinc-400", bar: "border-t-zinc-600/50" },
};

export const SCORE_COLOR = (s) => (s >= 70 ? "text-emerald-400 stroke-emerald-500" : s >= 45 ? "text-yellow-400 stroke-yellow-500" : s >= 25 ? "text-orange-400 stroke-orange-500" : "text-red-400 stroke-red-500");

export function fmtMoney(n) {
  const v = Number(n || 0);
  if (v >= 1000) return `$${(v / 1000).toFixed(v % 1000 === 0 ? 0 : 1)}k`;
  return `$${v}`;
}

export function fmtMoneyFull(n) {
  return `$${Number(n || 0).toLocaleString()}`;
}

// Ensures a lead has a linked project (converting if needed), then navigates.
export function useEnsureProjectNav() {
  const navigate = useNavigate();
  return async (lead, suffix = "") => {
    let pid = lead.project_id;
    if (!pid) {
      const res = await crmApi.convert(lead.id);
      pid = res.project_id;
    }
    navigate(`/projects/${pid}${suffix}`);
    return pid;
  };
}
