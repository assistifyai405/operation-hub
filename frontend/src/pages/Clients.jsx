import PageIntro from "@/components/PageIntro";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Search, Plus, Mail, Pencil, Trash2, Users, Loader2 } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { clientsApi } from "@/lib/api";
import { asArray } from "@/lib/safe";
import EmptyState from "@/components/EmptyState";
import { LoadError } from "@/components/LoadError";

const statusStyle = {
  Active: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Lead: "bg-brand-500/10 text-brand-400 border-brand-500/20",
  Churned: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
};

const empty = { name: "", contact: "", email: "", value: "", status: "Active" };

function ClientForm({ open, setOpen, initial, onSaved }) {
  const [form, setForm] = useState(empty);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const editing = Boolean(initial?.id);

  useEffect(() => {
    if (open) {
      setForm(initial ? { ...initial, value: initial.value ?? "" } : empty);
      setErrors({});
    }
  }, [open, initial]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const validate = () => {
    const e = {};
    if (!form.name.trim()) e.name = "Company name is required";
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = "Enter a valid email";
    if (form.value !== "" && isNaN(Number(form.value))) e.value = "Value must be a number";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const submit = async () => {
    if (saving) return;
    if (!validate()) return;
    setSaving(true);
    const payload = {
      name: form.name.trim(), contact: form.contact.trim(), email: form.email.trim(),
      value: form.value === "" ? 0 : Number(form.value), status: form.status,
    };
    try {
      if (editing) await clientsApi.update(initial.id, payload);
      else {
        await clientsApi.create(payload);
        const { events } = await import("@/lib/analytics");
        events.clientCreated({ source: "clients_page" });
      }
      toast.success(editing ? "Client updated" : "Client created");
      setOpen(false);
      onSaved();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="border-white/10 bg-zinc-950 text-zinc-100 sm:max-w-md" data-testid="client-dialog">
        <DialogHeader><DialogTitle>{editing ? "Edit Client" : "New Client"}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Company name *</label>
            <input value={form.name} onChange={(e) => set("name", e.target.value)} data-testid="client-name-input"
              className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" placeholder="Company name" />
            {errors.name && <p className="mt-1 text-xs text-red-400" data-testid="client-name-error">{errors.name}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">Contact</label>
              <input value={form.contact} onChange={(e) => set("contact", e.target.value)} data-testid="client-contact-input"
                className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" placeholder="Contact name" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-zinc-400">Deal value ($)</label>
              <input value={form.value} onChange={(e) => set("value", e.target.value)} data-testid="client-value-input"
                className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" placeholder="0" />
              {errors.value && <p className="mt-1 text-xs text-red-400">{errors.value}</p>}
            </div>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Email</label>
            <input value={form.email} onChange={(e) => set("email", e.target.value)} data-testid="client-email-input"
              className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" placeholder="name@company.com" />
            {errors.email && <p className="mt-1 text-xs text-red-400" data-testid="client-email-error">{errors.email}</p>}
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">Status</label>
            <Select value={form.status} onValueChange={(v) => set("status", v)}>
              <SelectTrigger data-testid="client-status-trigger" className="border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
              <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
                {["Active", "Lead", "Churned"].map((s) => <SelectItem key={s} value={s} data-testid={`client-status-${s}`}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <button onClick={() => setOpen(false)} className="rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-300 transition-all hover:text-white">Cancel</button>
          <button onClick={submit} disabled={saving} data-testid="client-save-btn" className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-50">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}{editing ? "Save" : "Create"}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Clients() {
  const { t } = useTranslation();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const load = () => {
    setLoading(true);
    setLoadError(null);
    clientsApi.list()
      .then((data) => setClients(asArray(data)))
      .catch((e) => { toast.error(e.message); setClients([]); setLoadError(e.message || "Couldn't load clients"); })
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const openNew = () => { setEditing(null); setDialogOpen(true); };
  const openEdit = (c) => { setEditing(c); setDialogOpen(true); };
  const confirmDelete = async () => {
    try {
      await clientsApi.remove(deleteTarget.id);
      toast.success("Client deleted");
      setDeleteTarget(null);
      load();
    } catch (e) { toast.error(e.message); }
  };

  const list = asArray(clients);
  const filtered = list.filter((c) => c.name.toLowerCase().includes(query.toLowerCase()) || (c.contact || "").toLowerCase().includes(query.toLowerCase()));
  const fmt = (v) => `$${Number(v || 0).toLocaleString()}`;

  return (
    <div className="space-y-5" data-testid="clients-page">
      <PageIntro title={t("pages.clients.title")} description={t("pages.clients.description")} />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-zinc-400">{list.length} client{list.length !== 1 && "s"} in your workspace.</p>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search clients" data-testid="clients-search"
              className="rounded-lg border border-white/10 bg-zinc-950 py-2 pl-9 pr-3 text-sm text-zinc-200 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" />
          </div>
          <button onClick={openNew} data-testid="add-client-btn" className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-500 glow-brand">
            <Plus className="h-4 w-4" /> Add Client
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-500" aria-label="Loading clients"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : loadError ? (
        <LoadError message={loadError} onRetry={load} testid="clients-load-error" />
      ) : list.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No clients yet"
          description="Clients are the companies and people you work with — linked to projects, tasks, and opportunities."
          why="Add one real client to unlock CRM views, pipeline deals, and AI summaries grounded in your data."
          actionLabel="Create your first client"
          onAction={openNew}
          testid="clients-empty"
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-white/10 bg-zinc-950">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-white/10 bg-zinc-900/40 text-zinc-400">
              <tr>
                <th className="px-5 py-3 font-medium">Client</th>
                <th className="px-5 py-3 font-medium">Contact</th>
                <th className="hidden px-5 py-3 font-medium md:table-cell">Value</th>
                <th className="hidden px-5 py-3 font-medium sm:table-cell">Projects</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id} className="border-b border-white/5 transition-colors hover:bg-zinc-900/40" data-testid={`client-row-${c.id}`}>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <Avatar className="h-9 w-9 border border-white/10"><AvatarFallback className="bg-brand-600/20 text-brand-300">{c.name[0]}</AvatarFallback></Avatar>
                      <span className="font-medium text-zinc-100">{c.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <p className="text-zinc-200">{c.contact || "—"}</p>
                    {c.email && <p className="flex items-center gap-1 text-xs text-zinc-500"><Mail className="h-3 w-3" />{c.email}</p>}
                  </td>
                  <td className="hidden px-5 py-3 font-semibold text-brand-400 md:table-cell">{fmt(c.value)}</td>
                  <td className="hidden px-5 py-3 text-zinc-300 sm:table-cell">{c.projects}</td>
                  <td className="px-5 py-3"><span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusStyle[c.status]}`}>{c.status}</span></td>
                  <td className="px-5 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => openEdit(c)} data-testid={`edit-client-${c.id}`} className="rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-brand-400"><Pencil className="h-4 w-4" /></button>
                      <button onClick={() => setDeleteTarget(c)} data-testid={`delete-client-${c.id}`} className="rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-red-400"><Trash2 className="h-4 w-4" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ClientForm open={dialogOpen} setOpen={setDialogOpen} initial={editing} onSaved={load} />

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent className="border-white/10 bg-zinc-950 text-zinc-100">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete client?</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">This will permanently remove "{deleteTarget?.name}" and unlink its projects. This cannot be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-white/10 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 hover:text-white">Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} data-testid="confirm-delete-client" className="bg-red-600 text-white hover:bg-red-500">Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
