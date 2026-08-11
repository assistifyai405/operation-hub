import PageIntro from "@/components/PageIntro";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
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
import { asArray } from "@/lib/safe";
import EmptyState from "@/components/EmptyState";
import { LoadError } from "@/components/LoadError";
import { useLocale } from "@/context/LocaleContext";
import { formatDate } from "@/i18n/format";

const columns = ["In Progress", "Review", "Completed", "Blocked"];
const dot = { "In Progress": "bg-brand-400", Review: "bg-cyan-400", Completed: "bg-emerald-400", Blocked: "bg-red-400" };
const empty = { name: "", client_id: "none", status: "In Progress", progress: 0, due: "", members: 1, description: "", notes: "" };

function ProjectForm({ open, setOpen, initial, clients, onSaved }) {
  const { t } = useTranslation();
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
    if (saving) return;
    if (!form.name.trim()) { setErrors({ name: t("projects.validation.nameRequired") }); return; }
    setSaving(true);
    const payload = {
      name: form.name.trim(),
      client_id: form.client_id === "none" ? null : form.client_id,
      status: form.status,
      progress: Math.max(0, Math.min(100, Number(form.progress) || 0)),
      due: form.due, members: Number(form.members) || 1,
      description: form.description || "", notes: form.notes || "",
    };
    try {
      if (editing) await projectsApi.update(initial.id, payload);
      else {
        await projectsApi.create(payload);
        const { events } = await import("@/lib/analytics");
        events.projectCreated({ source: "projects_page" });
      }
      toast.success(t(editing ? "projects.toasts.updated" : "projects.toasts.created"));
      setOpen(false); onSaved();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="border-white/10 bg-zinc-950 text-zinc-100 sm:max-w-md" data-testid="project-dialog">
        <DialogHeader><DialogTitle>{t(editing ? "projects.form.editTitle" : "projects.form.newTitle")}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("projects.form.name")} *</label>
            <input value={form.name} onChange={(e) => set("name", e.target.value)} data-testid="project-name-input"
              className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" placeholder={t("projects.form.namePlaceholder")} />
            {errors.name && <p className="mt-1 text-xs text-red-400" data-testid="project-name-error">{errors.name}</p>}
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("projects.form.client")}</label>
            <Select value={form.client_id} onValueChange={(v) => set("client_id", v)}>
              <SelectTrigger data-testid="project-client-trigger" className="border-white/10 bg-zinc-900"><SelectValue placeholder={t("projects.noClient")} /></SelectTrigger>
              <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
                <SelectItem value="none">{t("projects.noClient")}</SelectItem>
                {asArray(clients).map((c) => <SelectItem key={c.id} value={c.id} data-testid={`project-client-${c.id}`}>{c.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("common.status")}</label>
              <Select value={form.status} onValueChange={(v) => set("status", v)}>
                <SelectTrigger data-testid="project-status-trigger" className="border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
                <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
                  {columns.map((s) => <SelectItem key={s} value={s} data-testid={`project-status-${s}`}>{t(`statuses.${s}`)}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("projects.form.members")}</label>
              <input type="number" min="1" value={form.members} onChange={(e) => set("members", e.target.value)} data-testid="project-members-input"
                className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("projects.form.progress", { progress: form.progress })}</label>
              <input type="range" min="0" max="100" value={form.progress} onChange={(e) => set("progress", e.target.value)} data-testid="project-progress-input" className="mt-3 w-full accent-brand-600" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("projects.form.dueDate")}</label>
              <input type="date" value={form.due} onChange={(e) => set("due", e.target.value)} data-testid="project-due-input"
                className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" />
            </div>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">{t("projects.form.description")}</label>
            <textarea value={form.description} onChange={(e) => set("description", e.target.value)} data-testid="project-description-input" rows={3}
              className="w-full resize-none rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" placeholder={t("projects.form.descriptionPlaceholder")} />
          </div>
        </div>
        <DialogFooter>
          <button onClick={() => setOpen(false)} className="rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-300 transition-all hover:text-white">{t("common.cancel")}</button>
          <button onClick={submit} disabled={saving} data-testid="project-save-btn" className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-50">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}{t(editing ? "common.save" : "common.create")}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Projects() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const load = () => {
    setLoading(true);
    setLoadError(null);
    Promise.all([projectsApi.list(), clientsApi.list()])
      .then(([p, c]) => { setProjects(asArray(p)); setClients(asArray(c)); })
      .catch((e) => { toast.error(e.message); setProjects([]); setClients([]); setLoadError(e.message || t("projects.loadError")); })
      .finally(() => setLoading(false));
  };
  useEffect(load, [t]);

  const openNew = () => { setEditing(null); setDialogOpen(true); };
  const openEdit = (p) => { setEditing(p); setDialogOpen(true); };
  const confirmDelete = async () => {
    try { await projectsApi.remove(deleteTarget.id); toast.success(t("projects.toasts.deleted")); setDeleteTarget(null); load(); }
    catch (e) { toast.error(e.message); }
  };

  const projectList = asArray(projects);
  const clientList = asArray(clients);
  const fmtDue = (d) => d ? formatDate(d, locale, { month: "short", day: "numeric", year: undefined }) : "—";

  return (
    <div className="space-y-5" data-testid="projects-page">
      <PageIntro title={t("pages.projects.title")} description={t("pages.projects.description")} helpModule="projects" />

      <div className="flex items-center justify-between">
        <p className="text-sm text-zinc-400">{t("projects.count", { count: projectList.length })}</p>
        <button onClick={openNew} data-testid="new-project-btn" className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-500 glow-brand">
          <Plus className="h-4 w-4" /> {t("projects.new")}
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-500" aria-label={t("projects.loading")}><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : loadError ? (
        <LoadError message={loadError} onRetry={load} testid="projects-load-error" />
      ) : projectList.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title={t("projects.empty.title")}
          description={t("projects.empty.description")}
          why={t("projects.empty.why")}
          actionLabel={t("projects.empty.action")}
          onAction={openNew}
          testid="projects-empty"
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {columns.map((col) => {
            const items = projectList.filter((p) => p.status === col);
            return (
              <div key={col} className="space-y-3" data-testid={`kanban-col-${col.toLowerCase().replace(/\s/g, "-")}`}>
                <div className="flex items-center gap-2 px-1">
                  <span className={`h-2 w-2 rounded-full ${dot[col]}`} />
                  <h3 className="text-sm font-semibold text-zinc-200">{t(`statuses.${col}`)}</h3>
                  <span className="ml-auto text-xs text-zinc-500">{items.length}</span>
                </div>
                <div className="space-y-3">
                  {items.map((p) => (
                    <div key={p.id} onClick={() => navigate(`/projects/${p.id}`)} className="group cursor-pointer rounded-xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-brand-500/40" data-testid={`project-card-${p.id}`}>
                      <div className="flex items-start justify-between">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-zinc-100">{p.name}</p>
                          <p className="mt-0.5 truncate text-xs text-zinc-500">{p.client_name || t("projects.noClient")}</p>
                        </div>
                        <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                          <button onClick={(e) => { e.stopPropagation(); openEdit(p); }} data-testid={`edit-project-${p.id}`} className="rounded-md p-1 text-zinc-500 hover:bg-zinc-800 hover:text-brand-400"><Pencil className="h-3.5 w-3.5" /></button>
                          <button onClick={(e) => { e.stopPropagation(); setDeleteTarget(p); }} data-testid={`delete-project-${p.id}`} className="rounded-md p-1 text-zinc-500 hover:bg-zinc-800 hover:text-red-400"><Trash2 className="h-3.5 w-3.5" /></button>
                        </div>
                      </div>
                      <div className="mt-3">
                        <div className="mb-1 flex justify-between text-xs text-zinc-400"><span>{t("projects.progress")}</span><span>{p.progress}%</span></div>
                        <Progress value={p.progress} className="h-1.5 bg-zinc-800 [&>div]:bg-brand-500" />
                      </div>
                      <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
                        <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />{fmtDue(p.due)}</span>
                        <span className="flex items-center gap-1"><Users2 className="h-3 w-3" />{p.members}</span>
                      </div>
                    </div>
                  ))}
                  {items.length === 0 && <p className="rounded-xl border border-dashed border-white/10 p-4 text-center text-xs text-zinc-600">{t("projects.noProjects")}</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <ProjectForm open={dialogOpen} setOpen={setDialogOpen} initial={editing} clients={clientList} onSaved={load} />

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent className="border-white/10 bg-zinc-950 text-zinc-100">
          <AlertDialogHeader>
            <AlertDialogTitle>{t("projects.delete.title")}</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">{t("projects.delete.description", { name: deleteTarget?.name })}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-white/10 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 hover:text-white">{t("common.cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} data-testid="confirm-delete-project" className="bg-red-600 text-white hover:bg-red-500">{t("common.delete")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
