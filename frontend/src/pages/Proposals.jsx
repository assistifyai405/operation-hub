import { Plus, FileText, MoreHorizontal } from "lucide-react";
import { proposals } from "@/data/mock";
import EmptyState from "@/components/EmptyState";
import HelpTip from "@/components/HelpTip";

const statusStyle = {
  Sent: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  Draft: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  Accepted: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Rejected: "bg-red-500/10 text-red-400 border-red-500/20",
};

export default function Proposals() {
  return (
    <div className="space-y-5" data-testid="proposals-page">
      <div className="flex items-center justify-between">
        <p className="flex items-center gap-2 text-sm text-zinc-400">
          {proposals.length} proposals · manage your pipeline.
          <HelpTip testid="proposals-help" text="Track your proposal pipeline. To generate a polished, client-ready proposal with AI, open a project and use the Proposal tab in the Project Workspace." />
        </p>
        <button data-testid="new-proposal-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">
          <Plus className="h-4 w-4" /> New Proposal
        </button>
      </div>

      {proposals.length === 0 ? (
        <EmptyState icon={FileText} title="No proposals yet" description="Win more work with AI-generated proposals. Open a project and generate one in seconds." actionLabel="New Proposal" testid="proposals-empty" />
      ) : (
      <div className="space-y-3">
        {proposals.map((p) => (
          <div key={p.id} className="flex items-center gap-4 rounded-xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-violet-500/40" data-testid={`proposal-${p.id}`}>
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-violet-600/15 text-violet-400">
              <FileText className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-zinc-100">{p.title}</p>
              <p className="text-xs text-zinc-500">{p.client} · {p.date}</p>
            </div>
            <span className="hidden text-sm font-semibold text-zinc-200 sm:block">{p.amount}</span>
            <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusStyle[p.status]}`}>{p.status}</span>
            <button className="text-zinc-500 hover:text-zinc-200"><MoreHorizontal className="h-4 w-4" /></button>
          </div>
        ))}
      </div>
      )}
    </div>
  );
}
