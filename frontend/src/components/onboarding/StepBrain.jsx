import { useState } from "react";
import { toast } from "sonner";
import { Brain, ArrowRight, ArrowLeft, Pencil, Check } from "lucide-react";
import { onboardingApi } from "@/lib/api";
import { StepShell, PrimaryBtn, GhostBtn, inputCls } from "./onboardingShared";

const FIELDS = [
  ["company_summary", "Company summary", true],
  ["industry", "Industry", false],
  ["communication_style", "Communication style", false],
  ["proposal_style", "Proposal style", false],
  ["brand_voice", "Brand voice", false],
  ["writing_style", "Writing style", false],
];

export function StepBrain({ data, setData, next, back }) {
  const p = data.profile || {};
  const [editing, setEditing] = useState(false);
  const [local, setLocal] = useState(() => ({ ...p, services: Array.isArray(p.services) ? p.services.join(", ") : (p.services || "") }));

  const save = async () => {
    const sections = { ...local, services: String(local.services || "").split(",").map((s) => s.trim()).filter(Boolean) };
    try { await onboardingApi.updateProfile(sections); setData((d) => ({ ...d, profile: sections })); setEditing(false); toast.success("Profile updated"); }
    catch (e) { toast.error(e.message); }
  };

  const cont = async () => {
    if (editing) await save();
    next();
  };

  const services = Array.isArray(p.services) ? p.services : String(p.services || "").split(",").map((s) => s.trim()).filter(Boolean);

  return (
    <StepShell>
      <div data-testid="onb-step-brain">
        <div className="mb-5 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-600/15 text-brand-400"><Brain className="h-5 w-5" /></span>
            <div>
              <h2 className="text-2xl font-bold text-zinc-50">Your Knowledge Brain is ready</h2>
              <p className="text-sm text-zinc-500">Here's what Assistify learned. Edit anything — it's yours.</p>
            </div>
          </div>
          {!editing && <GhostBtn onClick={() => { setLocal({ ...p, services: services.join(", ") }); setEditing(true); }} data-testid="onb-brain-edit"><Pencil className="h-3.5 w-3.5" /> Edit</GhostBtn>}
        </div>

        <div className="space-y-3" data-testid="onb-brain-profile">
          {FIELDS.map(([key, label, big]) => (
            <div key={key} className="rounded-xl border border-white/10 bg-zinc-950 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-300">{label}</p>
              {editing ? (
                big
                  ? <textarea value={local[key] || ""} onChange={(e) => setLocal({ ...local, [key]: e.target.value })} rows={2} className={`${inputCls} mt-1.5 resize-none`} data-testid={`onb-brain-${key}`} />
                  : <input value={local[key] || ""} onChange={(e) => setLocal({ ...local, [key]: e.target.value })} className={`${inputCls} mt-1.5`} data-testid={`onb-brain-${key}`} />
              ) : (
                <p className="mt-1 text-sm text-zinc-300">{p[key] || "—"}</p>
              )}
            </div>
          ))}
          <div className="rounded-xl border border-white/10 bg-zinc-950 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-300">Services</p>
            {editing ? (
              <input value={local.services || ""} onChange={(e) => setLocal({ ...local, services: e.target.value })} className={`${inputCls} mt-1.5`} data-testid="onb-brain-services" placeholder="comma separated" />
            ) : (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {services.length ? services.map((s) => <span key={s} className="rounded-full border border-white/10 bg-zinc-900 px-2.5 py-1 text-xs text-zinc-300">{s}</span>) : <span className="text-sm text-zinc-500">—</span>}
              </div>
            )}
          </div>
        </div>

        <div className="mt-8 flex items-center justify-between">
          <GhostBtn onClick={back}><ArrowLeft className="h-4 w-4" /> Back</GhostBtn>
          <div className="flex items-center gap-2">
            {editing && <PrimaryBtn onClick={save} data-testid="onb-brain-save"><Check className="h-4 w-4" /> Save</PrimaryBtn>}
            <PrimaryBtn onClick={cont} data-testid="onb-brain-continue">Looks good <ArrowRight className="h-4 w-4" /></PrimaryBtn>
          </div>
        </div>
      </div>
    </StepShell>
  );
}
