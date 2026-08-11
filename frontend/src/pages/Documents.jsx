import PageIntro from "@/components/PageIntro";
import { useEffect, useRef, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Upload, Search, FileText, FileImage, FileSpreadsheet, FileArchive, File,
  FolderOpen, Loader2, Trash2, Pencil, Download, ChevronLeft, ChevronRight,
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { documentsApi, libraryApi } from "@/lib/api";
import EmptyState from "@/components/EmptyState";
import HelpTip from "@/components/HelpTip";
import { formatDate } from "@/i18n/format";

const typeIcon = {
  PDF: { icon: FileText, color: "text-red-400 bg-red-500/10" },
  Image: { icon: FileImage, color: "text-pink-400 bg-pink-500/10" },
  Doc: { icon: FileText, color: "text-blue-400 bg-blue-500/10" },
  Sheet: { icon: FileSpreadsheet, color: "text-emerald-400 bg-emerald-500/10" },
  Archive: { icon: FileArchive, color: "text-amber-400 bg-amber-500/10" },
  Other: { icon: File, color: "text-zinc-400 bg-zinc-500/10" },
};
const TYPES = ["All", "PDF", "Image", "Doc", "Sheet", "Archive", "Other"];

export default function Documents() {
  const { t, i18n } = useTranslation();
  const fileRef = useRef(null);
  const [data, setData] = useState({ items: [], total: 0, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [q, setQ] = useState("");
  const [type, setType] = useState("All");
  const [page, setPage] = useState(1);
  const [renameTarget, setRenameTarget] = useState(null);
  const [renameVal, setRenameVal] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    libraryApi.documents({ q, type, page, page_size: 12 })
      .then(setData).catch((e) => toast.error(e.message)).finally(() => setLoading(false));
  }, [q, type, page]);

  useEffect(() => { const t = setTimeout(load, q ? 300 : 0); return () => clearTimeout(t); }, [load, q]);
  useEffect(() => { setPage(1); }, [q, type]);

  const onUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await documentsApi.upload(file);
      toast.success("Document uploaded");
      setPage(1); load();
    } catch (err) { toast.error(err.message); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const doRename = async () => {
    if (!renameVal.trim()) return;
    try { await documentsApi.rename(renameTarget.id, renameVal.trim()); toast.success("Renamed"); setRenameTarget(null); load(); }
    catch (e) { toast.error(e.message); }
  };
  const doDelete = async () => {
    try { await documentsApi.remove(deleteTarget.id); toast.success("Deleted"); setDeleteTarget(null); load(); }
    catch (e) { toast.error(e.message); }
  };

  return (
    <div className="space-y-5" data-testid="documents-page">
      <PageIntro title={t("pages.documents.title")} description={t("pages.documents.description")} helpModule="documents" />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="flex items-center gap-2 text-sm text-zinc-400">
          {data.total} file{data.total !== 1 && "s"} in your library.
          <HelpTip testid="documents-help" text="Upload and manage all your business files here. Files are stored securely and scoped to your organization." />
        </p>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search documents" data-testid="documents-search"
              className="rounded-lg border border-white/10 bg-zinc-950 py-2 pl-9 pr-3 text-sm text-zinc-200 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" />
          </div>
          <Select value={type} onValueChange={setType}>
            <SelectTrigger data-testid="documents-type-filter" className="w-32 border-white/10 bg-zinc-950"><SelectValue /></SelectTrigger>
            <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
              {TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
            </SelectContent>
          </Select>
          <input ref={fileRef} type="file" onChange={onUpload} className="hidden" data-testid="documents-file-input" />
          <button onClick={() => fileRef.current?.click()} disabled={uploading} data-testid="upload-btn"
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-brand-500 disabled:opacity-60 glow-brand">
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />} Upload
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={FolderOpen}
          title={q || type !== "All" ? "No matching documents" : "No documents yet"}
          description={q || type !== "All" ? "Try a different search or filter." : "Documents store contracts, briefs, and files alongside your clients and projects."}
          why={q || type !== "All" ? undefined : "Upload a file to keep source material in Assistify for you and AI context."}
          actionLabel={q || type !== "All" ? undefined : "Upload document"}
          onAction={q || type !== "All" ? undefined : () => fileRef.current?.click()}
          testid="documents-empty"
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {data.items.map((d) => {
              const t = typeIcon[d.type] || typeIcon.Other;
              const Icon = t.icon;
              return (
                <div key={d.id} className="group relative rounded-xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-brand-500/40" data-testid={`doc-${d.id}`}>
                  <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${t.color}`}><Icon className="h-6 w-6" /></div>
                  <p className="mt-3 truncate text-sm font-medium text-zinc-100" title={d.name}>{d.name}</p>
                  <p className="mt-0.5 truncate text-xs text-zinc-500">{d.project_name || "No project"}</p>
                  <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
                    <span>{d.size}</span><span>{formatDate(d.created_at, i18n.resolvedLanguage, { month: "short" })}</span>
                  </div>
                  <div className="mt-3 flex items-center gap-1 border-t border-white/5 pt-3 opacity-0 transition-opacity group-hover:opacity-100">
                    {d.storage_path && <a href={documentsApi.fileUrl(d.id)} target="_blank" rel="noreferrer" data-testid={`doc-view-${d.id}`} className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-brand-400"><Download className="h-4 w-4" /></a>}
                    <button onClick={() => { setRenameTarget(d); setRenameVal(d.name); }} data-testid={`doc-rename-${d.id}`} className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-brand-400"><Pencil className="h-4 w-4" /></button>
                    <button onClick={() => setDeleteTarget(d)} data-testid={`doc-delete-${d.id}`} className="ml-auto rounded-md p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-red-400"><Trash2 className="h-4 w-4" /></button>
                  </div>
                </div>
              );
            })}
          </div>
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-3" data-testid="documents-pagination">
              <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="flex items-center gap-1 rounded-lg border border-white/10 bg-zinc-950 px-3 py-1.5 text-sm text-zinc-300 disabled:opacity-40"><ChevronLeft className="h-4 w-4" /> Prev</button>
              <span className="text-sm text-zinc-500">Page {page} of {data.pages}</span>
              <button disabled={page >= data.pages} onClick={() => setPage(page + 1)} className="flex items-center gap-1 rounded-lg border border-white/10 bg-zinc-950 px-3 py-1.5 text-sm text-zinc-300 disabled:opacity-40">Next <ChevronRight className="h-4 w-4" /></button>
            </div>
          )}
        </>
      )}

      <Dialog open={Boolean(renameTarget)} onOpenChange={(o) => !o && setRenameTarget(null)}>
        <DialogContent className="border-white/10 bg-zinc-950 text-zinc-100 sm:max-w-sm">
          <DialogHeader><DialogTitle>Rename document</DialogTitle></DialogHeader>
          <input value={renameVal} onChange={(e) => setRenameVal(e.target.value)} data-testid="doc-rename-input"
            className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" />
          <DialogFooter>
            <button onClick={() => setRenameTarget(null)} className="rounded-lg border border-white/10 bg-zinc-900 px-4 py-2 text-sm text-zinc-300">Cancel</button>
            <button onClick={doRename} data-testid="doc-rename-save" className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500">Save</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <AlertDialogContent className="border-white/10 bg-zinc-950 text-zinc-100">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete document?</AlertDialogTitle>
            <AlertDialogDescription className="text-zinc-400">This will permanently remove "{deleteTarget?.name}".</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-white/10 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 hover:text-white">Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={doDelete} data-testid="confirm-delete-doc" className="bg-red-600 text-white hover:bg-red-500">Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
