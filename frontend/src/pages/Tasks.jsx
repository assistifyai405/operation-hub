import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, CheckSquare, Loader2 } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { tasksApi, projectsApi } from "@/lib/api";
import { asArray } from "@/lib/safe";
import EmptyState from "@/components/EmptyState";

const priorityStyle = {
  High: "bg-red-500/10 text-red-400 border-red-500/20",
  Medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  Low: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
};
const dotColor = { High: "bg-red-400", Medium: "bg-amber-400", Low: "bg-zinc-500" };
const empty = { title: "", project_id: "none", priority: "Medium", due: "", done: false };

function TaskForm({ open, setOpen, initial, projects, onSaved }) {
  const [form, setForm] = useState(empty);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const editing = Boolean(initial?.id);

  useEffect(() => {
    if (open) { setForm(initial ? { ...initial, project_id: initial.project_id || "none" } : empty); setErrors({}); }
  }, [open, initial]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.title.trim()) { setErrors({ title: "Task title is required" }); return; }
    setSaving(true);
    const payload = {
      title: form.title.trim(),
      project_id: form.project_id === "none" ? null : form.project_id,
      priority: form.priority, due: form.due, done: form.done,
    };
    try {
      if (editing) await tasksApi.update(initial.id, payload);
      else {
        await tasksApi.create(payload);
        const { events } = await import("@/lib/analytics");
        events.taskCreated({ source: "tasks_page" });
      }
      toast.success(editing ? "Task updated" : "Task created");
      setOpen(false); onSaved();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="border-white/10 bg-zinc-950 text-zinc-100 sm:max-w-md" data-testid="task-dialog">
        <DialogHeader><DialogTitle>{editing ? "Edit Task" : "New Task"}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Task title *</label>
            <input value={form.title} onChange={(e) => set("title", e.target.value)} data-testid="task-title-input"
              className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" placeholder="Finalize proposal" />
            {errors.title && <p className="mt-1 text-xs text-red-400" data-testid="task-title-error">{errors.title}</p>}
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Project</label>
            <Select value={form.project_id} onValueChange={(v) => set("project_id", v)}>
              <SelectTrigger data-testid="task-project-trigger" className="border-white/10 bg-zinc-900"><SelectValue placeholder="No project" /></SelectTrigger>
              <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
                <SelectItem value="none">No project</SelectItem>
                {asArray(projects).map((p) => <SelectItem key={p.id} value={p.id} data-testid={`task-project-${p.id}`}>{p.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">Priority</label>
              <Select value={form.priority} onValueChange={(v) => set("priority", v)}>
                <SelectTrigger data-testid="task-priority-trigger" className="border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
                <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
                  {["High", "Medium", "Low"].map((s) => <SelectItem key={s} value={s} data-testid={`task-priority-${s}`}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">Due date</label>
              <input type="date" value={form.due} onChange={(e) => set("due", e.target.value)} data-testid="task-due-input"
                className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
            </div>
          </div>
        </div>
        <DialogFooter>
          <button onClick={() => setOpen(false)} className="rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-300 transition-all hover:text-white">Cancel</button>
          <button onClick={submit} disabled={saving} data-testid="task-save-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-50">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}{editing ? "Save" : "Create"}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Tasks() {
  const [tasks, setTasks] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = () => {
    setLoading(true);
    Promise.all([tasksApi.list(), projectsApi.list()])
      .then(([t, p]) => { setTasks(asArray(t)); setProjects(asArray(p)); })
      .catch((e) => { toast.error(e.message); setTasks([]); setProjects([]); }).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const openNew = () => { setEditing(null); setDialogOpen(true); };
  const openEdit = (t) => { setEditing(t); setDialogOpen(true); };

  const toggle = async (t) => {
    setTasks((cur) => cur.map((x) => (x.id === t.id ? { ...x, done: !x.done } : x)));
    try {
      await tasksApi.update(t.id, { title: t.title, project_id: t.project_id, priority: t.priority, due: t.due, done: !t.done });
    } catch (e) { toast.error(e.message); load(); }
  };

  const confirmDelete = async () => {
    try { await tasksApi.remove(deleteTarget.id); toast.success("Task deleted"); setDeleteTarget(null); load(); }
    catch (e) { toast.error(e.message); }
  };

  const taskList = asArray(tasks);
  const projectList = asArray(projects);
  const filtered = taskList.filter((t) => filter === "all" || (filter === "active" ? !t.done : t.done));
  const fmtDue = (d) => d ? new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "";

  return (
    <div className="space-y-5" data-testid="tasks-page">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-1 rounded-lg border border-white/10 bg-zinc-950 p-1">
          {["all", "active", "done"].map((f) => (
            <button key={f} onClick={() => setFilter(f)} data-testid={`filter-${f}`}
              className={`rounded-md px-3 py-1.5 text-sm font-medium capitalize transition-all ${filter === f ? "bg-violet-600 text-white" : "text-zinc-400 hover:text-zinc-200"}`}>{f}</button>
          ))}
        </div>
        <button onClick={openNew} data-testid="add-task-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">
          <Plus className="h-4 w-4" /> Add Task
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : taskList.length === 0 ? (
        <EmptyState
          icon={CheckSquare}
          title="No tasks yet"
          description="Tasks are the concrete next steps on your projects — due dates, priorities, and progress."
          why="Add a task so Assistify can surface overdue work and keep priorities clear."
          actionLabel="Create your first task"
          onAction={openNew}
          testid="tasks-empty"
        />
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-white/10 py-16 text-center text-sm text-zinc-500" data-testid="tasks-filter-empty">No {filter} tasks.</div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-white/10 bg-zinc-950">
          {filtered.map((t) => (
            <div key={t.id} className="group flex items-center gap-4 border-b border-white/5 px-5 py-3.5 transition-colors last:border-0 hover:bg-zinc-900/40" data-testid={`task-${t.id}`}>
              <Checkbox checked={t.done} onCheckedChange={() => toggle(t)} data-testid={`task-check-${t.id}`} className="border-white/20 data-[state=checked]:border-violet-500 data-[state=checked]:bg-violet-600" />
              <div className="min-w-0 flex-1">
                <p className={`text-sm ${t.done ? "text-zinc-500 line-through" : "text-zinc-100"}`}>{t.title}</p>
                <p className="text-xs text-zinc-500">{t.project_name || "No project"}{t.client_name ? ` · ${t.client_name}` : ""}</p>
              </div>
              <span className={`hidden shrink-0 items-center gap-1.5 sm:flex`}><span className={`h-2 w-2 rounded-full ${dotColor[t.priority]}`} /></span>
              <span className={`hidden shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium sm:inline-flex ${priorityStyle[t.priority]}`}>{t.priority}</span>
              {t.due && <span className="hidden shrink-0 text-xs text-zinc-500 md:block">{fmtDue(t.due)}</span>}
              <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                <button onClick={() => openEdit(t)} data-testid={`edit-task-${t.id}`} className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-violet-400"><Pencil className="h-4 w-4" /></button>
                <button onClick={() => setDeleteTarget(t)} data-testid={`delete-task-${t.id}`} className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-red-400"><Trash2 className="h-4 w-4" /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      <TaskForm open={dialogOpen} setOpen={setDialogOpen} initial={editing} projects={projectList} onSaved={load} />

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent className="border-white/10 bg-zinc-950 text-zinc-100">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete task?</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">This will permanently remove "{deleteTarget?.title}". This cannot be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-white/10 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 hover:text-white">Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} data-testid="confirm-delete-task" className="bg-red-600 text-white hover:bg-red-500">Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
