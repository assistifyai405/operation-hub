import { Plus, Users2, Calendar } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { projects } from "@/data/mock";

const columns = ["In Progress", "Review", "Completed", "Blocked"];
const dot = {
  "In Progress": "bg-violet-400",
  Review: "bg-cyan-400",
  Completed: "bg-emerald-400",
  Blocked: "bg-red-400",
};

export default function Projects() {
  return (
    <div className="space-y-5" data-testid="projects-page">
      <div className="flex items-center justify-between">
        <p className="text-sm text-zinc-400">Track {projects.length} projects across their lifecycle.</p>
        <button data-testid="new-project-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">
          <Plus className="h-4 w-4" /> New Project
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {columns.map((col) => {
          const items = projects.filter((p) => p.status === col);
          return (
            <div key={col} className="space-y-3">
              <div className="flex items-center gap-2 px-1">
                <span className={`h-2 w-2 rounded-full ${dot[col]}`} />
                <h3 className="text-sm font-semibold text-zinc-200">{col}</h3>
                <span className="ml-auto text-xs text-zinc-500">{items.length}</span>
              </div>
              <div className="space-y-3">
                {items.map((p) => (
                  <div key={p.id} className="rounded-xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-violet-500/40" data-testid={`project-card-${p.id}`}>
                    <p className="text-sm font-semibold text-zinc-100">{p.name}</p>
                    <p className="mt-0.5 text-xs text-zinc-500">{p.client}</p>
                    <div className="mt-3">
                      <div className="mb-1 flex justify-between text-xs text-zinc-400">
                        <span>Progress</span><span>{p.progress}%</span>
                      </div>
                      <Progress value={p.progress} className="h-1.5 bg-zinc-800 [&>div]:bg-violet-500" />
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
                      <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />{p.due}</span>
                      <span className="flex items-center gap-1"><Users2 className="h-3 w-3" />{p.members}</span>
                    </div>
                  </div>
                ))}
                {items.length === 0 && <p className="rounded-xl border border-dashed border-white/10 p-4 text-center text-xs text-zinc-600">No projects</p>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
