import { useState } from "react";
import { toast } from "sonner";
import { Building2, Globe, Loader2, Wand2, ArrowRight, ArrowLeft, Sparkles } from "lucide-react";
import { onboardingApi, settingsApi } from "@/lib/api";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { StepShell, Field, inputCls, PrimaryBtn, GhostBtn } from "./onboardingShared";

const EMPLOYEES = ["Just me", "2–10", "11–50", "51–200", "200+"];
const LANGS = [["en", "English"], ["es", "Spanish"], ["fr", "French"], ["de", "German"], ["nl", "Dutch"], ["pt", "Portuguese"]];

export function StepCompany({ data, setData, next, back }) {
  const c = data.company || {};
  const [analyzing, setAnalyzing] = useState(false);
  const set = (k, v) => setData((d) => ({ ...d, company: { ...d.company, [k]: v } }));

  const analyze = async () => {
    if (!c.website) { toast.error("Enter a website first"); return; }
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
        toast.success("We pre-filled what we found — review and tweak below.");
      } else {
        toast.message(r.reason || "Couldn't analyze that site — fill in the details below.");
      }
    } catch (e) { toast.error(e.message); } finally { setAnalyzing(false); }
  };

  const onLogo = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    try { const r = await settingsApi.uploadImage(f); set("logo", r.url); toast.success("Logo uploaded"); }
    catch (err) { toast.error(err.message); }
  };

  const cont = () => {
    if (!(c.company_name || "").trim()) { toast.error("Company name is required"); return; }
    next();
  };

  return (
    <StepShell>
      <div data-testid="onb-step-company">
        <div className="mb-6 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-600/15 text-violet-400"><Building2 className="h-5 w-5" /></span>
          <div>
            <h2 className="text-2xl font-bold text-zinc-50">Tell us about your business</h2>
            <p className="text-sm text-zinc-500">Your AI employee uses this to write like you.</p>
          </div>
        </div>

        <Field label="Website (optional — we'll auto-fill from it)" testid="onb-website-field">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Globe className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
              <input value={c.website || ""} onChange={(e) => set("website", e.target.value)} data-testid="onb-website-input" className={`${inputCls} pl-9`} placeholder="acme.com" />
            </div>
            <button onClick={analyze} disabled={analyzing} data-testid="onb-analyze-btn" className="inline-flex items-center gap-1.5 rounded-lg border border-violet-500/40 bg-violet-500/10 px-3 py-2 text-sm font-medium text-violet-200 transition-all hover:bg-violet-500/20 disabled:opacity-50">
              {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />} Analyze
            </button>
          </div>
        </Field>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label="Company name *" testid="onb-company-name-field">
            <input value={c.company_name || ""} onChange={(e) => set("company_name", e.target.value)} data-testid="onb-company-name" className={inputCls} placeholder="Acme Studio" />
          </Field>
          <Field label="Industry">
            <input value={c.industry || ""} onChange={(e) => set("industry", e.target.value)} data-testid="onb-industry" className={inputCls} placeholder="Design agency" />
          </Field>
          <Field label="Number of employees">
            <Select value={c.employees || ""} onValueChange={(v) => set("employees", v)}>
              <SelectTrigger data-testid="onb-employees" className="border-white/10 bg-zinc-900 py-2.5"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">{EMPLOYEES.map((x) => <SelectItem key={x} value={x}>{x}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
          <Field label="Country">
            <input value={c.country || ""} onChange={(e) => set("country", e.target.value)} data-testid="onb-country" className={inputCls} placeholder="United States" />
          </Field>
          <Field label="Main services" testid="onb-services-field">
            <input value={c.main_services || ""} onChange={(e) => set("main_services", e.target.value)} data-testid="onb-services" className={inputCls} placeholder="Branding, web design, marketing" />
          </Field>
          <Field label="Target customers">
            <input value={c.target_customers || ""} onChange={(e) => set("target_customers", e.target.value)} data-testid="onb-customers" className={inputCls} placeholder="B2B startups & SMEs" />
          </Field>
          <Field label="Preferred language">
            <Select value={c.language || "en"} onValueChange={(v) => set("language", v)}>
              <SelectTrigger data-testid="onb-language" className="border-white/10 bg-zinc-900 py-2.5"><SelectValue /></SelectTrigger>
              <SelectContent className="border-white/10 bg-zinc-950 text-zinc-200">{LANGS.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
          <Field label="Company logo (optional)">
            <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-white/10 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-400 hover:text-zinc-200">
              <Sparkles className="h-4 w-4 text-violet-400" /> {c.logo ? "Change logo" : "Upload logo"}
              <input type="file" accept="image/*" onChange={onLogo} data-testid="onb-logo" className="hidden" />
            </label>
          </Field>
        </div>

        <div className="mt-8 flex items-center justify-between">
          <GhostBtn onClick={back} data-testid="onb-company-back"><ArrowLeft className="h-4 w-4" /> Back</GhostBtn>
          <PrimaryBtn onClick={cont} data-testid="onb-company-continue">Continue <ArrowRight className="h-4 w-4" /></PrimaryBtn>
        </div>
      </div>
    </StepShell>
  );
}
