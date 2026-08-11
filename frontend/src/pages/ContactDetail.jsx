import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft, Mail, Phone, Globe, Building2, MapPin, Sparkles, Loader2,
  FolderKanban, FileText, Receipt, Target, RefreshCw, ArrowRight, ShieldCheck, AlertTriangle,
} from "lucide-react";
import { crmApi } from "@/lib/api";
import { AiIcon } from "@/components/ai/aiHelpers";
import { fmtMoneyFull, STAGE_META } from "@/components/crm/crmShared";
import { LoadError } from "@/components/LoadError";
import { useLocale } from "@/context/LocaleContext";
import { formatRelativeTime } from "@/i18n/format";

export default function ContactDetail() {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const { id } = useParams();
  const navigate = useNavigate();
  const [c, setC] = useState(null);
  const [summary, setSummary] = useState(null);
  const [genning, setGenning] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const load = useCallback(() => {
    setLoadError(null);
    return crmApi.contact(id)
      .then((data) => { setC(data); setSummary(data.ai_summary || null); })
      .catch((e) => {
        setC(null);
        setLoadError(e.message || t("crm.detail.loadError"));
        toast.error(t("crm.detail.loadError"));
      });
  }, [id, t]);
  useEffect(() => { load(); }, [load]);

  const genSummary = async (refresh = false) => {
    setGenning(true);
    try { setSummary(await crmApi.contactSummary(id, refresh)); }
    catch (e) { toast.error(e.message); } finally { setGenning(false); }
  };

  if (loadError && !c) {
    return <LoadError message={loadError} onRetry={load} testid="contact-load-error" />;
  }
  if (!c) return <div className="flex items-center justify-center py-24 text-zinc-600" aria-label={t("crm.detail.loading")}><Loader2 className="h-7 w-7 animate-spin" /></div>;

  const info = [
    { icon: Mail, v: c.email }, { icon: Phone, v: c.phone }, { icon: Globe, v: c.website },
    { icon: Building2, v: c.industry && `${c.industry}${c.company_size ? ` · ${c.company_size}` : ""}` }, { icon: MapPin, v: c.address },
  ].filter((x) => x.v);

  return (
    <div className="space-y-5" data-testid="contact-detail-page">
      <button onClick={() => navigate("/crm")} className="inline-flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white"><ArrowLeft className="h-4 w-4" /> {t("crm.detail.back")}</button>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600/15 text-brand-300 text-lg font-bold">{c.name.slice(0, 2).toUpperCase()}</span>
          <div>
            <h1 className="text-2xl font-bold text-zinc-50" data-testid="contact-name">{c.name}</h1>
            <p className="text-sm text-zinc-500">{c.contact || "—"} · {t("crm.detail.openPipeline", { amount: fmtMoneyFull(c.pipeline_value, locale) })}</p>
            <div className="mt-1 flex flex-wrap gap-1.5">{(c.tags || []).map((t) => <span key={t} className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-zinc-400">{t}</span>)}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          {/* AI relationship summary */}
          <div className="rounded-2xl border border-brand-500/20 bg-brand-500/[0.05] p-4" data-testid="contact-ai-summary">
            <div className="mb-2 flex items-center justify-between">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-brand-300"><Sparkles className="h-3.5 w-3.5" /> {t("crm.detail.aiSummary")}</p>
              {summary && <button onClick={() => genSummary(true)} disabled={genning} data-testid="contact-refresh-summary" className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300">{genning ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />} {t("common.refresh")}</button>}
            </div>
            {!summary ? (
              <button onClick={() => genSummary(false)} disabled={genning} data-testid="contact-generate-summary"
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-brand-500/30 py-2.5 text-sm font-semibold text-brand-200 hover:bg-brand-500/10 disabled:opacity-60">
                {genning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} {genning ? t("crm.detail.analyzing") : t("crm.detail.generateSummary")}
              </button>
            ) : (
              <div className="space-y-2.5">
                <p className="text-sm text-zinc-200">{summary.summary}</p>
                {summary.strengths?.length > 0 && <div><p className="flex items-center gap-1 text-xs font-semibold text-emerald-400"><ShieldCheck className="h-3.5 w-3.5" /> {t("crm.detail.strengths")}</p><ul className="mt-1 space-y-0.5">{summary.strengths.map((s, i) => <li key={i} className="text-xs text-zinc-300">• {s}</li>)}</ul></div>}
                {summary.risks?.length > 0 && <div><p className="flex items-center gap-1 text-xs font-semibold text-amber-400"><AlertTriangle className="h-3.5 w-3.5" /> {t("crm.detail.risks")}</p><ul className="mt-1 space-y-0.5">{summary.risks.map((s, i) => <li key={i} className="text-xs text-zinc-300">• {s}</li>)}</ul></div>}
                {summary.next_best_action && <div className="rounded-lg bg-zinc-900/60 p-2.5"><p className="flex items-center gap-1 text-xs font-semibold text-brand-300"><ArrowRight className="h-3.5 w-3.5" /> {t("crm.detail.nextAction")}</p><p className="mt-0.5 text-sm text-zinc-200">{summary.next_best_action}</p></div>}
              </div>
            )}
          </div>

          {/* Linked entities */}
          <LinkRow icon={Target} title={t("crm.detail.deals")} items={(c.leads || []).map((l) => ({ label: l.title, meta: t(`pipeline.stages.${l.stage}`, { defaultValue: l.stage }), onClick: () => navigate("/pipeline") }))} empty={t("crm.detail.noDeals")} testid="contact-leads" />
          <LinkRow icon={FolderKanban} title={t("nav.projects")} items={(c.projects || []).map((p) => ({ label: p.name, meta: p.status, onClick: () => navigate(`/projects/${p.id}`) }))} empty={t("crm.detail.noProjects")} testid="contact-projects" />
          <LinkRow icon={FileText} title={t("nav.documents")} items={[
            ...(c.proposals || []).map((p) => ({ label: p.title || t("workspace.tabs.proposal"), meta: `${t("workspace.tabs.proposal")} · ${p.status}`, onClick: () => navigate(`/projects/${p.project_id}?tab=proposal`) })),
            ...(c.invoices || []).map((i) => ({ label: i.invoice_number || t("workspace.tabs.invoice"), meta: `${t("workspace.tabs.invoice")} · ${i.status}`, onClick: () => navigate(`/projects/${i.project_id}?tab=invoice`) })),
          ]} empty={t("crm.detail.noDocuments")} testid="contact-docs" />
        </div>

        {/* Right: info + timeline */}
        <div className="space-y-5">
          <div className="rounded-2xl border border-white/10 bg-zinc-950 p-4">
            <p className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">{t("crm.detail.details")}</p>
            <div className="space-y-2.5">
              {info.map((x, i) => <p key={i} className="flex items-center gap-2 text-sm text-zinc-300"><x.icon className="h-4 w-4 shrink-0 text-zinc-500" /> {x.v}</p>)}
              {c.owner && <p className="text-xs text-zinc-500">{t("crm.detail.owner")}: <span className="text-zinc-300">{c.owner}</span></p>}
              {c.notes && <p className="border-t border-white/10 pt-2.5 text-sm text-zinc-400">{c.notes}</p>}
            </div>
          </div>
          {c.timeline?.length > 0 && (
            <div className="rounded-2xl border border-white/10 bg-zinc-950 p-4" data-testid="contact-timeline">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-zinc-500">{t("crm.detail.timeline")}</p>
              <div className="space-y-3">
                {c.timeline.map((e, i) => (
                  <div key={i} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-600/15 text-brand-300"><AiIcon name={e.icon} className="h-3 w-3" /></span>
                      {i < c.timeline.length - 1 && <span className="mt-1 h-full w-px flex-1 bg-white/10" />}
                    </div>
                    <div className="pb-1"><p className="text-sm text-zinc-200">{e.title}</p><p className="text-xs text-zinc-600">{formatRelativeTime(e.when, locale, t)}</p></div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const LinkRow = ({ icon: Icon, title, items, empty, testid }) => (
  <div className="rounded-2xl border border-white/10 bg-zinc-950 p-4" data-testid={testid}>
    <p className="mb-2.5 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500"><Icon className="h-3.5 w-3.5 text-brand-400" /> {title} <span className="rounded-full bg-white/5 px-1.5 text-[10px]">{items.length}</span></p>
    {items.length === 0 ? <p className="text-xs text-zinc-600">{empty}</p> : (
      <div className="space-y-1.5">
        {items.map((it, i) => (
          <button key={i} onClick={it.onClick} className="flex w-full items-center justify-between gap-2 rounded-lg border border-white/10 bg-zinc-900/40 px-3 py-2 text-left transition-all hover:border-brand-500/30">
            <span className="truncate text-sm text-zinc-200">{it.label}</span>
            <span className="shrink-0 text-xs text-zinc-500">{it.meta}</span>
          </button>
        ))}
      </div>
    )}
  </div>
);
