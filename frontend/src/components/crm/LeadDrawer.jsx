import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  X, Trash2, FolderPlus, FileText, ScrollText, Receipt, Mail, Wand2, Users,
  CalendarClock, Languages, ArrowRight, Save,
} from "lucide-react";
import { crmApi } from "@/lib/api";
import { AiIcon } from "@/components/ai/aiHelpers";
import { STAGES, STAGE_META, useEnsureProjectNav } from "@/components/crm/crmShared";
import { AISalesBrief } from "@/components/crm/AISalesBrief";
import { useLocale } from "@/context/LocaleContext";
import { formatRelativeTime } from "@/i18n/format";

const ONE_CLICK = [
  { key: "proposal", icon: FileText, suffix: "?tab=proposal" },
  { key: "contract", icon: ScrollText, suffix: "?tab=contract" },
  { key: "invoice", icon: Receipt, suffix: "?tab=invoice" },
  { key: "improve", icon: Wand2, suffix: "?tab=proposal&assist=improve" },
  { key: "followup", icon: Mail, suffix: "?tab=proposal&assist=email" },
  { key: "meeting", icon: CalendarClock, suffix: "?tab=proposal&assist=summarize" },
  { key: "translate", icon: Languages, suffix: "?tab=proposal&assist=translate" },
];

export function LeadDrawer({ leadId, onClose, onChanged, navigate }) {
  const { t } = useTranslation();
  const { locale } = useLocale();
  const [lead, setLead] = useState(null);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const ensureNav = useEnsureProjectNav();

  useEffect(() => {
    if (!leadId) return;
    crmApi.getLead(leadId).then((l) => { setLead(l); setForm({ ...l, tags: (l.tags || []).join(", ") }); }).catch(() => toast.error(t("crm.leadDrawer.toasts.loadError")));
  }, [leadId, t]);

  const setF = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      const body = {
        title: form.title, client_id: form.client_id || null, project_id: form.project_id || null,
        stage: form.stage, value: Number(form.value) || 0,
        probability: form.probability === "" || form.probability == null ? null : Number(form.probability),
        expected_close: form.expected_close || "", owner: form.owner || "", contact_name: form.contact_name || "",
        email: form.email || "", phone: form.phone || "", source: form.source || "", notes: form.notes || "",
        tags: String(form.tags || "").split(",").map((t) => t.trim()).filter(Boolean),
      };
      const updated = await crmApi.updateLead(leadId, body);
      setLead(updated); toast.success(t("crm.leadDrawer.toasts.saved")); onChanged?.();
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  const del = async () => {
    if (!window.confirm(t("crm.leadDrawer.deleteConfirm"))) return;
    await crmApi.deleteLead(leadId); toast.success(t("crm.leadDrawer.toasts.deleted")); onChanged?.(); onClose();
  };

  const oneClick = async (item) => {
    try {
      if (item.key === "summary" && lead.client_id) { navigate(`/crm/${lead.client_id}`); return; }
      toast.message(t(item.key === "improve" || item.key === "followup" ? "crm.leadDrawer.toasts.openingAssistant" : "crm.leadDrawer.toasts.openingWorkspace"));
      await ensureNav(lead, item.suffix);
    } catch (e) { toast.error(e.message); }
  };

  const convert = async () => {
    try { const r = await crmApi.convert(leadId); toast.success(t("crm.leadDrawer.toasts.projectLinked")); onChanged?.(); navigate(`/projects/${r.project_id}`); }
    catch (e) { toast.error(e.message); }
  };

  if (!form) return null;
  const meta = STAGE_META[form.stage] || STAGE_META.New;

  return (
    <div className="fixed inset-0 z-[70] flex justify-end" data-testid="lead-drawer">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-xl flex-col border-l border-white/10 bg-zinc-950 shadow-2xl animate-slide-in-right">
        <div className="flex items-start justify-between gap-3 border-b border-white/10 p-5">
          <div className="min-w-0">
            <div className="mb-1.5 flex items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 rounded-full bg-white/5 px-2.5 py-0.5 text-xs font-medium ${meta.text}`}><span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} /> {t(`pipeline.stages.${form.stage}`, { defaultValue: form.stage })}</span>
              <span className="text-xs text-zinc-500">{t("crm.leadDrawer.scoreConfidence", { score: lead?.score, confidence: lead?.ai_confidence })}</span>
            </div>
            <input value={form.title} onChange={(e) => setF("title", e.target.value)} data-testid="lead-title-input"
              className="w-full bg-transparent text-xl font-bold text-zinc-50 focus:outline-none" />
            <p className="mt-0.5 text-sm text-zinc-500">{lead?.client_name || form.contact_name || t("crm.leadDrawer.noCompany")}</p>
          </div>
          <div className="flex items-center gap-1">
            <button onClick={del} data-testid="lead-delete" aria-label={t("crm.leadDrawer.delete")} className="rounded-lg p-2 text-zinc-500 hover:bg-white/5 hover:text-red-400"><Trash2 className="h-4 w-4" /></button>
            <button onClick={onClose} data-testid="lead-drawer-close" aria-label={t("common.close")} className="rounded-lg p-2 text-zinc-400 hover:bg-white/5 hover:text-white"><X className="h-5 w-5" /></button>
          </div>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto p-5">
          {/* Editable fields */}
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("crm.leadDrawer.fields.stage")}><select value={form.stage} onChange={(e) => setF("stage", e.target.value)} data-testid="lead-stage-select" className={inputCls}>{STAGES.map((s) => <option key={s} value={s}>{t(`pipeline.stages.${s}`, { defaultValue: s })}</option>)}</select></Field>
            <Field label={t("crm.leadDrawer.fields.value")}><input type="number" value={form.value} onChange={(e) => setF("value", e.target.value)} data-testid="lead-value-input" className={inputCls} /></Field>
            <Field label={t("crm.leadDrawer.fields.probability")}><input type="number" value={form.probability ?? ""} onChange={(e) => setF("probability", e.target.value)} placeholder={t("crm.leadDrawer.fields.auto")} className={inputCls} /></Field>
            <Field label={t("crm.leadDrawer.fields.expectedClose")}><input type="date" value={(form.expected_close || "").slice(0, 10)} onChange={(e) => setF("expected_close", e.target.value)} className={inputCls} /></Field>
            <Field label={t("crm.leadDrawer.fields.owner")}><input value={form.owner || ""} onChange={(e) => setF("owner", e.target.value)} className={inputCls} /></Field>
            <Field label={t("crm.leadDrawer.fields.tags")}><input value={form.tags} onChange={(e) => setF("tags", e.target.value)} placeholder={t("crm.leadDrawer.fields.tagsPlaceholder")} className={inputCls} /></Field>
          </div>
          <Field label={t("crm.leadDrawer.fields.notes")}><textarea value={form.notes || ""} onChange={(e) => setF("notes", e.target.value)} rows={2} className={inputCls} /></Field>
          <div className="flex gap-2">
            <button onClick={save} disabled={saving} data-testid="lead-save" className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3.5 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-60"><Save className="h-4 w-4" /> {t("common.save")}</button>
            {!form.project_id && <button onClick={convert} data-testid="lead-convert" className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3.5 py-2 text-sm font-medium text-zinc-200 hover:text-white"><FolderPlus className="h-4 w-4" /> {t("crm.leadDrawer.convertProject")}</button>}
            {form.project_id && <button onClick={() => navigate(`/projects/${form.project_id}`)} className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-zinc-900 px-3.5 py-2 text-sm font-medium text-zinc-200 hover:text-white"><ArrowRight className="h-4 w-4" /> {t("crm.leadDrawer.openProject")}</button>}
          </div>

          {/* One-click AI */}
          <Section title={t("crm.leadDrawer.oneClick.title")}>
            <div className="grid grid-cols-2 gap-2" data-testid="lead-one-click">
              {ONE_CLICK.map((a) => (
                <button key={a.key} onClick={() => oneClick(a)} data-testid={`lead-action-${a.key}`}
                  className="group flex items-center gap-2 rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-left text-xs font-medium text-zinc-200 transition-all hover:border-brand-500/40 hover:bg-brand-500/[0.05]">
                  <a.icon className="h-3.5 w-3.5 text-brand-300" /> {t(`crm.leadDrawer.oneClick.${a.key}`)}
                </button>
              ))}
              {lead?.client_id && (
                <button onClick={() => navigate(`/crm/${lead.client_id}`)} data-testid="lead-action-summary"
                  className="group flex items-center gap-2 rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-left text-xs font-medium text-zinc-200 transition-all hover:border-brand-500/40 hover:bg-brand-500/[0.05]">
                  <Users className="h-3.5 w-3.5 text-brand-300" /> {t("crm.leadDrawer.oneClick.summarizeCustomer")}
                </button>
              )}
            </div>
          </Section>

          {/* AI Sales brief */}
          <Section title={t("crm.leadDrawer.salesAssistant")}><AISalesBrief leadId={leadId} /></Section>

          {/* Follow-ups */}
          {lead?.followups?.length > 0 && (
            <Section title={t("crm.leadDrawer.recommendedFollowups")}>
              <div className="space-y-2" data-testid="lead-followups">
                {lead.followups.map((f, i) => (
                  <div key={i} className="flex items-start gap-2.5 rounded-lg border border-white/10 bg-zinc-900/40 p-3">
                    <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-600/15 text-brand-300"><Mail className="h-3.5 w-3.5" /></span>
                    <div><p className="text-sm font-medium text-zinc-200">{f.label}</p><p className="text-xs text-zinc-500">{f.why}</p></div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Timeline */}
          {lead?.timeline?.length > 0 && (
            <Section title={t("crm.leadDrawer.timeline")}>
              <div className="space-y-3" data-testid="lead-timeline">
                {lead.timeline.map((e, i) => (
                  <div key={i} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-600/15 text-brand-300"><AiIcon name={e.icon} className="h-3 w-3" /></span>
                      {i < lead.timeline.length - 1 && <span className="mt-1 h-full w-px flex-1 bg-white/10" />}
                    </div>
                    <div className="pb-1"><p className="text-sm text-zinc-200">{e.title}</p><p className="text-xs text-zinc-600">{formatRelativeTime(e.when, locale, t)}</p></div>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}

const inputCls = "w-full rounded-lg border border-white/10 bg-zinc-900 px-2.5 py-1.5 text-sm text-zinc-100 focus:border-brand-500/50 focus:outline-none";
const Field = ({ label, children }) => (<label className="block"><span className="mb-1 block text-[11px] text-zinc-500">{label}</span>{children}</label>);
const Section = ({ title, children }) => (<div><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">{title}</p>{children}</div>);
