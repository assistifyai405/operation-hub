import { useState } from "react";
import { Plus } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { tasks as seed } from "@/data/mock";

const priorityStyle = {
  High: "bg-red-500/10 text-red-400 border-red-500/20",
  Medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  Low: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
};

export default function Tasks() {
  const [tasks, setTasks] = useState(seed);
  const [filter, setFilter] = useState("all");

  const toggle = (id) => setTasks((t) => t.map((x) => (x.id === id ? { ...x, done: !x.done } : x)));
  const filtered = tasks.filter((t) => filter === "all" || (filter === "active" ? !t.done : t.done));

  return (
    <div className="space-y-5" data-testid="tasks-page">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-1 rounded-lg border border-white/10 bg-zinc-950 p-1">
          {["all", "active", "done"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              data-testid={`filter-${f}`}
              className={`rounded-md px-3 py-1.5 text-sm font-medium capitalize transition-all ${filter === f ? "bg-violet-600 text-white" : "text-zinc-400 hover:text-zinc-200"}`}
            >
              {f}
            </button>
          ))}
        </div>
        <button data-testid="add-task-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">
          <Plus className="h-4 w-4" /> Add Task
        </button>
      </div>

      <div className="overflow-hidden rounded-xl border border-white/10 bg-zinc-950">
        {filtered.map((t) => (
          <div key={t.id} className="flex items-center gap-4 border-b border-white/5 px-5 py-3.5 transition-colors last:border-0 hover:bg-zinc-900/40" data-testid={`task-${t.id}`}>
            <Checkbox checked={t.done} onCheckedChange={() => toggle(t.id)} data-testid={`task-check-${t.id}`} className="border-white/20 data-[state=checked]:border-violet-500 data-[state=checked]:bg-violet-600" />
            <div className="min-w-0 flex-1">
              <p className={`text-sm ${t.done ? "text-zinc-500 line-through" : "text-zinc-100"}`}>{t.title}</p>
              <p className="text-xs text-zinc-500">{t.project}</p>
            </div>
            <span className={`hidden shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium sm:inline-flex ${priorityStyle[t.priority]}`}>{t.priority}</span>
            <span className="shrink-0 text-xs text-zinc-500">{t.due}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
