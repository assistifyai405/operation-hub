import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Users2, Calendar, Pencil, Trash2, FolderKanban, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { projectsApi, clientsApi } from "@/lib/api";
import EmptyState from "@/components/EmptyState";

const columns = ["In Progress", "Review", "Completed", "Blocked"];
const dot = { "In Progress": "bg-violet-400", Review: "bg-cyan-400", Completed: "bg-emerald-400", Blocked: "bg-red-400" };
const empty = { name: "", client_id: "none", status: "In Progress", progress: 0, due: "", members: 1 };

function ProjectForm({ open, setOpen, initial, clients, onSaved }) {
  const [form, setForm] = useState(empty);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const editing = Boolean(initial?.id);

  useEffect(() => {
    if (open) {
      setForm(initial ? { ...initial, client_id: initial.client_id || "none" } : empty);
      setErrors({});
    }
  }, [open, initial]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.name.trim()) { setErrors({ name: "Project name is required" }); return; }
    setSaving(true);
    const payload = {
      name: form.name.trim(),
      client_id: form.client_id === "none" ? null : form.client_id,
      status: form.status,
      progress: Math.max(0, Math.min(100, Number(form.progress) || 0)),
      due: form.due, members: Number(form.members) || 1,
    };
    try {
      if (editing) await projectsApi.update(initial.id, payload);
      else await projectsApi.create(payload);
      toast.success(editing ? "Project updated" : "Project created");
      setOpen(false); onSaved();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="border-white/10 bg-zinc-950 text-zinc-100 sm:max-w-md" data-testid="project-dialog">
        <DialogHeader><DialogTitle>{editing ? "Edit Project" : "New Project"}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Project name *</label>
            <input value={form.name} onChange={(e) => set("name", e.target.value)} data-testid="project-name-input"
              className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" placeholder="Brand Redesign" />
            {errors.name && <p className="mt-1 text-xs text-red-400" data-testid="project-name-error">{errors.name}</p>}
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Client</label>
            <Select value={form.client_id} onValueChange={(v) => set("client_id", v)}>
              <SelectTrigger data-testid="project-client-trigger" className="border-white/10 bg-zinc-900"><SelectValue placeholder="No client" /></SelectTrigger>
              <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
                <SelectItem value="none">No client</SelectItem>
                {clients.map((c) => <SelectItem key={c.id} value={c.id} data-testid={`project-client-${c.id}`}>{c.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">Status</label>
              <Select value={form.status} onValueChange={(v) => set("status", v)}>
                <SelectTrigger data-testid="project-status-trigger" className="border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
                <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
                  {columns.map((s) => <SelectItem key={s} value={s} data-testid={`project-status-${s}`}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">Members</label>
              <input type="number" min="1" value={form.members} onChange={(e) => set("members", e.target.value)} data-testid="project-members-input"
                className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">Progress ({form.progress}%)</label>
              <input type="range" min="0" max="100" value={form.progress} onChange={(e) => set("progress", e.target.value)} data-testid="project-progress-input" className="mt-3 w-full accent-violet-600" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">Due date</label>
              <input type="date" value={form.due} onChange={(e) => set("due", e.target.value)} data-testid="project-due-input"
                className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
            </div>
          </div>
        </div>
        <DialogFooter>
          <button onClick={() => setOpen(false)} className="rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-300 transition-all hover:text-white">Cancel</button>
          <button onClick={submit} disabled={saving} data-testid="project-save-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-50">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}{editing ? "Save" : "Create"}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Projects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = () => {
    setLoading(true);
    Promise.all([projectsApi.list(), clientsApi.list()])
      .then(([p, c]) => { setProjects(p); setClients(c); })
      .catch((e) => toast.error(e.message)).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const openNew = () => { setEditing(null); setDialogOpen(true); };
  const openEdit = (p) => { setEditing(p); setDialogOpen(true); };
  const confirmDelete = async () => {
    try { await projectsApi.remove(deleteTarget.id); toast.success("Project deleted"); setDeleteTarget(null); load(); }
    catch (e) { toast.error(e.message); }
  };

  const fmtDue = (d) => d ? new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "—";

  return (
    <div className="space-y-5" data-testid="projects-page">
      <div className="flex items-center justify-between">
        <p className="text-sm text-zinc-400">{projects.length} project{projects.length !== 1 && "s"} across their lifecycle.</p>
        <button onClick={openNew} data-testid="new-project-btn" className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">
          <Plus className="h-4 w-4" /> New Project
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : projects.length === 0 ? (
        <EmptyState icon={FolderKanban} title="No projects yet" description="Create your first project and link it to a client to start tracking work." actionLabel="New Project" onAction={openNew} testid="projects-empty" />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {columns.map((col) => {
            const items = projects.filter((p) => p.status === col);
            return (
              <div key={col} className="space-y-3" data-testid={`kanban-col-${col.toLowerCase().replace(/\s/g, "-")}`}>
                <div className="flex items-center gap-2 px-1">
                  <span className={`h-2 w-2 rounded-full ${dot[col]}`} />
                  <h3 className="text-sm font-semibold text-zinc-200">{col}</h3>
                  <span className="ml-auto text-xs text-zinc-500">{items.length}</span>
                </div>
                <div className="space-y-3">
                  {items.map((p) => (
                    <div key={p.id} onClick={() => navigate(`/projects/${p.id}`)} className="group cursor-pointer rounded-xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-violet-500/40" data-testid={`project-card-${p.id}`}>
                      <div className="flex items-start justify-between">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-zinc-100">{p.name}</p>
                          <p className="mt-0.5 truncate text-xs text-zinc-500">{p.client_name || "No client"}</p>
                        </div>
                        <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                          <button onClick={(e) => { e.stopPropagation(); openEdit(p); }} data-testid={`edit-project-${p.id}`} className="rounded-md p-1 text-zinc-500 hover:bg-zinc-800 hover:text-violet-400"><Pencil className="h-3.5 w-3.5" /></button>
                          <button onClick={(e) => { e.stopPropagation(); setDeleteTarget(p); }} data-testid={`delete-project-${p.id}`} className="rounded-md p-1 text-zinc-500 hover:bg-zinc-800 hover:text-red-400"><Trash2 className="h-3.5 w-3.5" /></button>
                        </div>
                      </div>
                      <div className="mt-3">
                        <div className="mb-1 flex justify-between text-xs text-zinc-400"><span>Progress</span><span>{p.progress}%</span></div>
                        <Progress value={p.progress} className="h-1.5 bg-zinc-800 [&>div]:bg-violet-500" />
                      </div>
                      <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
                        <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />{fmtDue(p.due)}</span>
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
      )}

      <ProjectForm open={dialogOpen} setOpen={setDialogOpen} initial={editing} clients={clients} onSaved={load} />

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent className="border-white/10 bg-zinc-950 text-zinc-100">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete project?</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">This will permanently remove "{deleteTarget?.name}" and unlink its tasks. This cannot be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-white/10 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 hover:text-white">Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} data-testid="confirm-delete-project" className="bg-red-600 text-white hover:bg-red-500">Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
