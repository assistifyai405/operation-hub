import PageIntro from "@/components/PageIntro";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
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
import { LoadError } from "@/components/LoadError";
import { useLocale } from "@/context/LocaleContext";
import { formatDate } from "@/i18n/format";

const priorityStyle = {
  High: "bg-red-500/10 text-red-400 border-red-500/20",
  Medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  Low: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
};
const dotColor = { High: "bg-red-400", Medium: "bg-amber-400", Low: "bg-zinc-500" };
const empty = { title: "", project_id: "none", priority: "Medium", due: "", done: false };

function TaskForm({ open, setOpen, initial, projects, onSaved }) {
  const { t } = useTranslation();
  const [form, setForm] = useState(empty);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const editing = Boolean(initial?.id);

  useEffect(() => {
    if (open) { setForm(initial ? { ...initial, project_id: initial.project_id || "none" } : empty); setErrors({}); }
  }, [open, initial]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (saving) return;
    if (!form.title.trim()) { setErrors({ title: t("tasks.validation.titleRequired") }); return; }
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
      toast.success(t(editing ? "tasks.toasts.updated" : "tasks.toasts.created"));
      setOpen(false); onSaved();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="border-white/10 bg-zinc-950 text-zinc-100 sm:max-w-md" data-testid="task-dialog">
        <DialogHeader><DialogTitle>{t(editing ? "tasks.form.editTitle" : "tasks.form.newTitle")}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("tasks.form.title")} *</label>
            <input value={form.title} onChange={(e) => set("title", e.target.value)} data-testid="task-title-input"
              className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" placeholder={t("tasks.form.titlePlaceholder")} />
            {errors.title && <p className="mt-1 text-xs text-red-400" data-testid="task-title-error">{errors.title}</p>}
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("tasks.form.project")}</label>
            <Select value={form.project_id} onValueChange={(v) => set("project_id", v)}>
              <SelectTrigger data-testid="task-project-trigger" className="border-white/10 bg-zinc-900"><SelectValue placeholder={t("tasks.noProject")} /></SelectTrigger>
              <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
                <SelectItem value="none">{t("tasks.noProject")}</SelectItem>
                {asArray(projects).map((p) => <SelectItem key={p.id} value={p.id} data-testid={`task-project-${p.id}`}>{p.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("tasks.form.priority")}</label>
              <Select value={form.priority} onValueChange={(v) => set("priority", v)}>
                <SelectTrigger data-testid="task-priority-trigger" className="border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
                <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
                  {["High", "Medium", "Low"].map((s) => <SelectItem key={s} value={s} data-testid={`task-priority-${s}`}>{t(`priorities.${s}`)}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("tasks.form.dueDate")}</label>
              <input type="date" value={form.due} onChange={(e) => set("due", e.target.value)} data-testid="task-due-input"
                className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" />
            </div>
          </div>
        </div>
        <DialogFooter>
          <button onClick={() => setOpen(false)} className="rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-300 transition-all hover:text-white">{t("common.cancel")}</button>
          <button onClick={submit} disabled={saving} data-testid="task-save-btn" className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-50">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}{t(editing ? "common.save" : "common.create")}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Tasks() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const [tasks, setTasks] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const load = () => {
    setLoading(true);
    setLoadError(null);
    Promise.all([tasksApi.list(), projectsApi.list()])
      .then(([t, p]) => { setTasks(asArray(t)); setProjects(asArray(p)); })
      .catch((e) => { toast.error(e.message); setTasks([]); setProjects([]); setLoadError(e.message || t("tasks.loadError")); })
      .finally(() => setLoading(false));
  };
  useEffect(load, [t]);

  const openNew = () => { setEditing(null); setDialogOpen(true); };
  const openEdit = (t) => { setEditing(t); setDialogOpen(true); };

  const toggle = async (t) => {
    setTasks((cur) => cur.map((x) => (x.id === t.id ? { ...x, done: !x.done } : x)));
    try {
      await tasksApi.update(t.id, { title: t.title, project_id: t.project_id, priority: t.priority, due: t.due, done: !t.done });
    } catch (e) { toast.error(e.message); load(); }
  };

  const confirmDelete = async () => {
    try { await tasksApi.remove(deleteTarget.id); toast.success(t("tasks.toasts.deleted")); setDeleteTarget(null); load(); }
    catch (e) { toast.error(e.message); }
  };

  const taskList = asArray(tasks);
  const projectList = asArray(projects);
  const filtered = taskList.filter((t) => filter === "all" || (filter === "active" ? !t.done : t.done));
  const fmtDue = (d) => d ? formatDate(d, locale, { month: "short", day: "numeric", year: undefined }) : "";

  return (
    <div className="space-y-5" data-testid="tasks-page">
      <PageIntro title={t("pages.tasks.title")} description={t("pages.tasks.description")} />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-1 rounded-lg border border-white/10 bg-zinc-950 p-1">
          {["all", "active", "done"].map((f) => (
            <button key={f} onClick={() => setFilter(f)} data-testid={`filter-${f}`}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-all ${filter === f ? "bg-brand-600 text-white" : "text-zinc-400 hover:text-zinc-200"}`}>{t(`tasks.filters.${f}`)}</button>
          ))}
        </div>
        <button onClick={openNew} data-testid="add-task-btn" className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-500 glow-brand">
          <Plus className="h-4 w-4" /> {t("tasks.add")}
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-500" aria-label={t("tasks.loading")}><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : loadError ? (
        <LoadError message={loadError} onRetry={load} testid="tasks-load-error" />
      ) : taskList.length === 0 ? (
        <EmptyState
          icon={CheckSquare}
          title={t("tasks.empty.title")}
          description={t("tasks.empty.description")}
          why={t("tasks.empty.why")}
          actionLabel={t("tasks.empty.action")}
          onAction={openNew}
          testid="tasks-empty"
        />
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-white/10 py-16 text-center text-sm text-zinc-500" data-testid="tasks-filter-empty">{t("tasks.empty.filtered", { filter: t(`tasks.filters.${filter}`).toLowerCase() })}</div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-white/10 bg-zinc-950">
          {filtered.map((task) => (
            <div key={task.id} className="group flex items-center gap-4 border-b border-white/5 px-5 py-3.5 transition-colors last:border-0 hover:bg-zinc-900/40" data-testid={`task-${task.id}`}>
              <Checkbox checked={task.done} onCheckedChange={() => toggle(task)} data-testid={`task-check-${task.id}`} className="border-white/20 data-[state=checked]:border-brand-500 data-[state=checked]:bg-brand-600" />
              <div className="min-w-0 flex-1">
                <p className={`text-sm ${task.done ? "text-zinc-500 line-through" : "text-zinc-100"}`}>{task.title}</p>
                <p className="text-xs text-zinc-500">{task.project_name || t("tasks.noProject")}{task.client_name ? ` · ${task.client_name}` : ""}</p>
              </div>
              <span className={`hidden shrink-0 items-center gap-1.5 sm:flex`}><span className={`h-2 w-2 rounded-full ${dotColor[task.priority]}`} /></span>
              <span className={`hidden shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium sm:inline-flex ${priorityStyle[task.priority]}`}>{t(`priorities.${task.priority}`)}</span>
              {task.due && <span className="hidden shrink-0 text-xs text-zinc-500 md:block">{fmtDue(task.due)}</span>}
              <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                <button onClick={() => openEdit(task)} data-testid={`edit-task-${task.id}`} className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-brand-400"><Pencil className="h-4 w-4" /></button>
                <button onClick={() => setDeleteTarget(task)} data-testid={`delete-task-${task.id}`} className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-red-400"><Trash2 className="h-4 w-4" /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      <TaskForm open={dialogOpen} setOpen={setDialogOpen} initial={editing} projects={projectList} onSaved={load} />

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent className="border-white/10 bg-zinc-950 text-zinc-100">
          <AlertDialogHeader>
            <AlertDialogTitle>{t("tasks.delete.title")}</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">{t("tasks.delete.description", { title: deleteTarget?.title })}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-white/10 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 hover:text-white">{t("common.cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} data-testid="confirm-delete-task" className="bg-red-600 text-white hover:bg-red-500">{t("common.delete")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
