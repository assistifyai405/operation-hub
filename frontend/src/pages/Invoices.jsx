import PageIntro from "@/components/PageIntro";
import { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Receipt, Search, Loader2, ExternalLink, FolderOpen, ChevronLeft, ChevronRight, TrendingUp, Clock, FileStack } from "lucide-react";
import { toast } from "sonner";
import { libraryApi } from "@/lib/api";
import EmptyState from "@/components/EmptyState";
import HelpTip from "@/components/HelpTip";
import { statusBadge } from "@/components/LibraryDocsPage";
import { useLocale } from "@/context/LocaleContext";
import { formatCurrency, formatDate } from "@/i18n/format";

const TABS = ["All", "Draft", "Generated", "Sent", "Paid", "Overdue", "Cancelled", "Archived"];

export default function Invoices() {
  const { t } = useTranslation();
  const { locale } = useLocale();
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

  const totals = data.totals || { by_status: {}, revenue: 0, outstanding: 0, count: 0 };
  const stats = [
    { label: t("invoices.stats.paidRevenue"), value: formatCurrency(totals.revenue, locale), icon: TrendingUp, color: "text-emerald-400" },
    { label: t("invoices.stats.outstanding"), value: formatCurrency(totals.outstanding, locale), icon: Clock, color: "text-amber-400" },
    { label: t("invoices.stats.total"), value: totals.count, icon: FileStack, color: "text-brand-400" },
  ];

  return (
    <div className="space-y-5" data-testid="invoices-page">
      <PageIntro title={t("pages.invoices.title")} description={t("pages.invoices.description")} />

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
            const count = tab === "All" ? totals.count : (totals.by_status[tab]?.count || 0);
            return (
              <button key={tab} onClick={() => setStatus(tab)} data-testid={`invoice-tab-${tab.toLowerCase()}`}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${status === tab ? "bg-brand-600 text-white" : "border border-white/10 bg-zinc-950 text-zinc-400 hover:text-zinc-200"}`}>
                {t(`invoices.status.${tab}`)} <span className="opacity-60">{count}</span>
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("invoices.search")} data-testid="invoices-search"
              className="rounded-lg border border-white/10 bg-zinc-950 py-2 pl-9 pr-3 text-sm text-zinc-200 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" />
          </div>
          <HelpTip testid="invoices-help" text={t("invoices.help")} />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : data.items.length === 0 ? (
        <EmptyState icon={Receipt} title={q || status !== "All" ? t("invoices.empty.filteredTitle") : t("invoices.empty.title")}
          description={q || status !== "All" ? t("invoices.empty.filteredDescription") : t("invoices.empty.description")}
          actionLabel={q || status !== "All" ? undefined : t("invoices.empty.action")} onAction={() => navigate("/projects")} testid="invoices-empty" />
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-white/10">
            <table className="w-full text-sm">
              <thead className="bg-zinc-950 text-left text-xs text-zinc-500">
                <tr>
                  <th className="px-4 py-3 font-medium">{t("invoices.table.invoice")}</th>
                  <th className="hidden px-4 py-3 font-medium sm:table-cell">{t("invoices.table.client")}</th>
                  <th className="hidden px-4 py-3 font-medium md:table-cell">{t("invoices.table.date")}</th>
                  <th className="px-4 py-3 font-medium">{t("invoices.table.status")}</th>
                  <th className="px-4 py-3 text-right font-medium">{t("invoices.table.total")}</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {data.items.map((inv) => (
                  <tr key={inv.id} className="bg-zinc-950/50 transition-colors hover:bg-zinc-900/50" data-testid={`invoice-row-${inv.id}`}>
                    <td className="px-4 py-3">
                      <p className="font-medium text-zinc-100">{inv.invoice_number || inv.title}</p>
                      <p className="truncate text-xs text-zinc-500">{inv.project_name || t("invoices.noProject")}</p>
                    </td>
                    <td className="hidden px-4 py-3 text-zinc-400 sm:table-cell">{inv.client_name || "—"}</td>
                    <td className="hidden px-4 py-3 text-zinc-400 md:table-cell">{formatDate(inv.updated_at || inv.created_at, locale, { month: "short" })}</td>
                    <td className="px-4 py-3"><span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusBadge[inv.status] || statusBadge.Draft}`}>{t(`invoices.status.${inv.status}`, { defaultValue: inv.status })}</span></td>
                    <td className="px-4 py-3 text-right font-semibold text-zinc-100">{formatCurrency(inv.total, locale)}</td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => navigate(`/projects/${inv.project_id}?tab=invoice`)} data-testid={`invoice-open-${inv.id}`} className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white transition-all hover:bg-brand-500"><ExternalLink className="mr-1 inline h-3.5 w-3.5" />{t("common.open")}</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-3" data-testid="invoices-pagination">
              <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="flex items-center gap-1 rounded-lg border border-white/10 bg-zinc-950 px-3 py-1.5 text-sm text-zinc-300 disabled:opacity-40"><ChevronLeft className="h-4 w-4" /> {t("common.previous")}</button>
              <span className="text-sm text-zinc-500">{t("common.pageOf", { page, pages: data.pages })}</span>
              <button disabled={page >= data.pages} onClick={() => setPage(page + 1)} className="flex items-center gap-1 rounded-lg border border-white/10 bg-zinc-950 px-3 py-1.5 text-sm text-zinc-300 disabled:opacity-40">{t("common.next")} <ChevronRight className="h-4 w-4" /></button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
