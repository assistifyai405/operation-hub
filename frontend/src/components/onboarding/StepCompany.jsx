import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Building2, Globe, Loader2, Wand2, ArrowRight, ArrowLeft } from "lucide-react";
import { onboardingApi } from "@/lib/api";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { StepShell, Field, inputCls, PrimaryBtn, GhostBtn } from "./onboardingShared";

const EMPLOYEE_KEYS = [
  { id: "Just me", key: "justMe" },
  { id: "2–10", key: "2_10" },
  { id: "11–50", key: "11_50" },
  { id: "51–200", key: "51_200" },
  { id: "200+", key: "200plus" },
];

export function StepCompany({ data, setData, next, back }) {
  const { t } = useTranslation();
  const c = data.company || {};
  const [analyzing, setAnalyzing] = useState(false);
  const set = (k, v) => setData((d) => ({ ...d, company: { ...d.company, [k]: v } }));

  const analyze = async () => {
    if (!c.website) { toast.error(t("onboarding.websiteRequired")); return; }
    setAnalyzing(true);
    try {
      const r = await onboardingApi.analyzeWebsite(c.website);
      if (r.ok) {
        setData((d) => ({ ...d, company: {
          ...d.company,
          company_name: d.company.company_name || r.fields.company_name,
          industry: d.company.industry || r.fields.industry,
          main_services: d.company.main_services || r.fields.main_services,
          target_customers: d.company.target_customers || r.fields.target_customers,
        }}));
        toast.success(t("onboarding.analyzeSuccess"));
      } else {
        toast.message(r.reason || t("common.error"));
      }
    } catch (e) { toast.error(e.message); } finally { setAnalyzing(false); }
  };

  const cont = () => {
    if (!(c.company_name || "").trim()) { toast.error(t("onboarding.companyRequired")); return; }
    next();
  };

  return (
    <StepShell>
      <div data-testid="onb-step-company">
        <div className="mb-6 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-600/15 text-brand-400" aria-hidden="true"><Building2 className="h-5 w-5" /></span>
          <div>
            <h2 className="text-2xl font-bold text-zinc-50">{t("onboarding.companyTitle")}</h2>
            <p className="text-sm text-zinc-500">{t("onboarding.companyBody")}</p>
          </div>
        </div>

        <Field label={t("onboarding.website")} testid="onb-website-field">
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <Globe className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" aria-hidden="true" />
              <input value={c.website || ""} onChange={(e) => set("website", e.target.value)} data-testid="onb-website-input" className={`${inputCls} pl-9`} placeholder="acme.com" />
            </div>
            <button type="button" onClick={analyze} disabled={analyzing} data-testid="onb-analyze-btn" className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-brand-500/40 bg-brand-500/10 px-3 py-2 text-sm font-medium text-brand-200 transition-all hover:bg-brand-500/20 disabled:opacity-50">
              {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />} {t("onboarding.analyze")}
            </button>
          </div>
        </Field>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label={t("onboarding.yourName")} testid="onb-contact-name-field">
            <input value={c.contact_name || ""} onChange={(e) => set("contact_name", e.target.value)} data-testid="onb-contact-name" className={inputCls} placeholder="Jordan Reyes" />
          </Field>
          <Field label={t("onboarding.companyName")} testid="onb-company-name-field">
            <input value={c.company_name || ""} onChange={(e) => set("company_name", e.target.value)} data-testid="onb-company-name" className={inputCls} placeholder="Acme Studio" />
          </Field>
          <Field label={t("onboarding.industry")}>
            <input value={c.industry || ""} onChange={(e) => set("industry", e.target.value)} data-testid="onb-industry" className={inputCls} placeholder="Design agency" />
          </Field>
          <Field label={t("onboarding.companySize")}>
            <Select value={c.employees || ""} onValueChange={(v) => set("employees", v)}>
              <SelectTrigger data-testid="onb-employees" className="border-white/10 bg-zinc-900 py-2.5"><SelectValue placeholder={t("onboarding.select")} /></SelectTrigger>
              <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">
                {EMPLOYEE_KEYS.map((x) => (
                  <SelectItem key={x.id} value={x.id}>{t(`onboarding.employees.${x.key}`)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
          <GhostBtn onClick={back} data-testid="onb-company-back"><ArrowLeft className="h-4 w-4" /> {t("onboarding.back")}</GhostBtn>
          <PrimaryBtn onClick={cont} data-testid="onb-company-continue">{t("onboarding.continue")} <ArrowRight className="h-4 w-4" /></PrimaryBtn>
        </div>
      </div>
    </StepShell>
  );
}
