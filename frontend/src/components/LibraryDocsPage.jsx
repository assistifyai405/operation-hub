import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Search, Loader2, ExternalLink, FolderOpen, ChevronLeft, ChevronRight, ArrowUpDown } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import EmptyState from "@/components/EmptyState";
import HelpTip from "@/components/HelpTip";
import PageIntro from "@/components/PageIntro";
import { formatDate } from "@/i18n/format";

export const statusBadge = {
  Draft: "border-zinc-500/30 bg-zinc-500/10 text-zinc-300",
  Generated: "border-brand-500/30 bg-brand-500/10 text-brand-300",
  Sent: "border-blue-500/30 bg-blue-500/10 text-blue-300",
  Signed: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  Accepted: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  Rejected: "border-red-500/30 bg-red-500/10 text-red-300",
  Paid: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  Overdue: "border-red-500/30 bg-red-500/10 text-red-300",
  Cancelled: "border-zinc-600/30 bg-zinc-600/10 text-zinc-400",
  Archived: "border-zinc-600/30 bg-zinc-600/10 text-zinc-400",
};

export default function LibraryDocsPage({ icon: Icon, kind, tabId, statuses, apiFn, help, testid, title, description }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [data, setData] = useState({ items: [], total: 0, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("All");
  const [sort, setSort] = useState("recent");
  const [page, setPage] = useState(1);

  const load = useCallback(() => {
    setLoading(true);
    apiFn({ q, status, sort, page, page_size: 12 }).then(setData).catch((e) => toast.error(e.message)).finally(() => setLoading(false));
  }, [q, status, sort, page, apiFn]);

  useEffect(() => { const t = setTimeout(load, q ? 300 : 0); return () => clearTimeout(t); }, [load, q]);
  useEffect(() => { setPage(1); }, [q, status, sort]);

  const open = (item, deep) => navigate(`/projects/${item.project_id}${deep ? `?tab=${tabId}` : ""}`);
  const kindLabel = (count = 2) => t(`library.kinds.${kind}`, { count });

  return (
    <div className="space-y-5" data-testid={`${testid}-page`}>
      {(title || description) && <PageIntro title={title} description={description} />}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="flex items-center gap-2 text-sm text-zinc-400">
          {t("library.organizationCount", { count: data.total, kind: kindLabel(data.total) })}
          <HelpTip testid={`${testid}-help`} text={help} />
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("library.searchPlaceholder", { kind: kindLabel() })} data-testid={`${testid}-search`}
              className="rounded-lg border border-white/10 bg-zinc-950 py-2 pl-9 pr-3 text-sm text-zinc-200 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/40" />
          </div>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger data-testid={`${testid}-status-filter`} className="w-32 border-white/10 bg-zinc-950"><SelectValue /></SelectTrigger>
            <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
              {["All", ...statuses].map((s) => <SelectItem key={s} value={s}>{t(`library.statuses.${s}`, { defaultValue: s })}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={sort} onValueChange={setSort}>
            <SelectTrigger data-testid={`${testid}-sort`} className="w-36 border-white/10 bg-zinc-950"><ArrowUpDown className="mr-1 h-3.5 w-3.5" /><SelectValue /></SelectTrigger>
            <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
              <SelectItem value="recent">{t("library.sort.recent")}</SelectItem>
              <SelectItem value="title">{t("library.sort.title")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-zinc-500"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : data.items.length === 0 ? (
        <EmptyState icon={Icon} title={q || status !== "All" ? t("library.empty.matchingTitle", { kind: kindLabel() }) : t("library.empty.noneTitle", { kind: kindLabel() })}
          description={q || status !== "All" ? t("library.empty.filtered") : t("library.empty.create", { kind: kindLabel(1) })}
          actionLabel={q || status !== "All" ? undefined : t("library.goToProjects")} onAction={() => navigate("/projects")} testid={`${testid}-empty`} />
      ) : (
        <>
          <div className="space-y-3">
            {data.items.map((item) => (
              <div key={item.id} className="flex flex-col gap-3 rounded-xl border border-white/10 bg-zinc-950 p-4 transition-all hover:border-brand-500/40 sm:flex-row sm:items-center" data-testid={`${testid}-item-${item.id}`}>
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-600/15 text-brand-400"><Icon className="h-5 w-5" /></div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-zinc-100">{item.title}</p>
                  <p className="truncate text-xs text-zinc-500">{item.client_name || t("library.noClient")} · {item.project_name || t("library.noProject")} · v{item.version || 1} · {formatDate(item.updated_at || item.created_at, i18n.resolvedLanguage, { month: "short" })}</p>
                </div>
                <span className={`inline-flex w-fit items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusBadge[item.status] || statusBadge.Draft}`}>{t(`library.statuses.${item.status}`, { defaultValue: item.status })}</span>
                <div className="flex items-center gap-2">
                  <button onClick={() => open(item, false)} data-testid={`${testid}-open-project-${item.id}`} className="rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-300 transition-all hover:border-brand-500/40"><FolderOpen className="mr-1 inline h-3.5 w-3.5" />{t("library.project")}</button>
                  <button onClick={() => open(item, true)} data-testid={`${testid}-open-${item.id}`} className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white transition-all hover:bg-brand-500"><ExternalLink className="mr-1 inline h-3.5 w-3.5" />{t("common.open")}</button>
                </div>
              </div>
            ))}
          </div>
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-3" data-testid={`${testid}-pagination`}>
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
