import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Receipt, Search, Loader2, ExternalLink, FolderOpen, ChevronLeft, ChevronRight, TrendingUp, Clock, FileStack } from "lucide-react";
import { toast } from "sonner";
import { libraryApi } from "@/lib/api";
import EmptyState from "@/components/EmptyState";
import HelpTip from "@/components/HelpTip";
import { statusBadge, fmtDate } from "@/components/LibraryDocsPage";

const TABS = ["All", "Draft", "Generated", "Sent", "Paid", "Overdue", "Cancelled", "Archived"];
const money = (n) => `$${(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function Invoices() {
  const navigate = useNavigate();
  const [data, setData] = useState({ items: [], total: 0, pages: 1, totals: { by_status: {}, revenue: 0, outstanding: 0, count: 0 } });
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("All");
  const [page, setPage] = useState(1);

  const load = useCallback(() => {
    setLoading(true);
    libraryApi.invoices({ q, status, page, page_size: 12 }).then(setData).catch((e) => toast.error(e.message)).finally(() => setLoading(false));
  }, [q, status, page]);

  useEffect(() => { const t = setTimeout(load, q ? 300 : 0); return () => clearTimeout(t); }, [load, q]);
  useEffect(() => { setPage(1); }, [q, status]);

  const t = data.totals || { by_status: {}, revenue: 0, outstanding: 0, count: 0 };
  const stats = [
    { label: "Revenue (Paid)", value: money(t.revenue), icon: TrendingUp, color: "text-emerald-400" },
    { label: "Outstanding", value: money(t.outstanding), icon: Clock, color: "text-amber-400" },
    { label: "Total invoices", value: t.count, icon: FileStack, color: "text-violet-400" },
  ];

  return (
    <div className="space-y-5" data-testid="invoices-page">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3" data-testid="invoices-totals">
        {stats.map((s) => (
          <div key={s.label} className="rounded-xl border border-white/10 bg-zinc-950 p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs text-zinc-500">{s.label}</p>
              <s.icon className={`h-4 w-4 ${s.color}`} />
            </div>
            <p className="mt-2 text-2xl font-bold text-zinc-50">{s.value}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-1.5" data-testid="invoice-status-tabs">
          {TABS.map((tab) => {
            const count = tab === "All" ? t.count : (t.by_status[tab]?.count || 0);
            return (
              <button key={tab} onClick={() => setStatus(tab)} data-testid={`invoice-tab-${tab.toLowerCase()}`}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${status === tab ? "bg-violet-600 text-white" : "border border-white/10 bg-zinc-950 text-zinc-400 hover:text-zinc-200"}`}>
                {tab} <span className="opacity-60">{count}</span>
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search invoices" data-testid="invoices-search"
              className="rounded-lg border border-white/10 bg-zinc-950 py-2 pl-9 pr-3 text-sm text-zinc-200 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40" />
          </div>
          <HelpTip testid="invoices-help" text="Every AI-generated invoice across your organization. Open one to edit, change status or export in the Project Workspace." />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : data.items.length === 0 ? (
        <EmptyState icon={Receipt} title={q || status !== "All" ? "Geen bijpassende facturen" : "Nog geen facturen"}
          description={q || status !== "All" ? "Probeer een andere zoekopdracht of filter." : "Open een project en gebruik de factuurgenerator om je klant te factureren."}
          actionLabel={q || status !== "All" ? undefined : "Naar Projecten"} onAction={() => navigate("/projects")} testid="invoices-empty" />
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-white/10">
            <table className="w-full text-sm">
              <thead className="bg-zinc-950 text-left text-xs text-zinc-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Invoice</th>
                  <th className="hidden px-4 py-3 font-medium sm:table-cell">Client</th>
                  <th className="hidden px-4 py-3 font-medium md:table-cell">Date</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 text-right font-medium">Total</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {data.items.map((inv) => (
                  <tr key={inv.id} className="bg-zinc-950/50 transition-colors hover:bg-zinc-900/50" data-testid={`invoice-row-${inv.id}`}>
                    <td className="px-4 py-3">
                      <p className="font-medium text-zinc-100">{inv.invoice_number || inv.title}</p>
                      <p className="truncate text-xs text-zinc-500">{inv.project_name || "No project"}</p>
                    </td>
                    <td className="hidden px-4 py-3 text-zinc-400 sm:table-cell">{inv.client_name || "—"}</td>
                    <td className="hidden px-4 py-3 text-zinc-400 md:table-cell">{fmtDate(inv.updated_at || inv.created_at)}</td>
                    <td className="px-4 py-3"><span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusBadge[inv.status] || statusBadge.Draft}`}>{inv.status}</span></td>
                    <td className="px-4 py-3 text-right font-semibold text-zinc-100">{money(inv.total)}</td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => navigate(`/projects/${inv.project_id}?tab=invoice`)} data-testid={`invoice-open-${inv.id}`} className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white transition-all hover:bg-violet-500"><ExternalLink className="mr-1 inline h-3.5 w-3.5" />Open</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-3" data-testid="invoices-pagination">
              <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="flex items-center gap-1 rounded-lg border border-white/10 bg-zinc-950 px-3 py-1.5 text-sm text-zinc-300 disabled:opacity-40"><ChevronLeft className="h-4 w-4" /> Prev</button>
              <span className="text-sm text-zinc-500">Page {page} of {data.pages}</span>
              <button disabled={page >= data.pages} onClick={() => setPage(page + 1)} className="flex items-center gap-1 rounded-lg border border-white/10 bg-zinc-950 px-3 py-1.5 text-sm text-zinc-300 disabled:opacity-40">Next <ChevronRight className="h-4 w-4" /></button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
