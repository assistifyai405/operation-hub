import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Sparkles, Users, FolderKanban, Wand2, ArrowRight, ArrowLeft, Check,
  Loader2, X, FileText, FileSignature, Receipt, Rocket,
} from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { clientsApi, projectsApi, onboardingApi } from "@/lib/api";
import { toast } from "sonner";

const inputCls = "w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40";
const STATUSES = ["In Progress", "Review", "Completed", "Blocked"];

const aiActions = [
  { icon: Wand2, label: "AI Project Planner", desc: "Generate a full project plan from your context." },
  { icon: FileText, label: "AI Proposal", desc: "Turn the plan into a client-ready proposal." },
  { icon: FileSignature, label: "AI Contract", desc: "Draft a service agreement in one click." },
  { icon: Receipt, label: "AI Invoice", desc: "Create a professional invoice with VAT." },
];

export default function OnboardingWizard({ open, onDone }) {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [client, setClient] = useState({ name: "", contact: "", email: "", phone: "" });
  const [project, setProject] = useState({ name: "", description: "", status: "In Progress" });
  const [clientId, setClientId] = useState(null);
  const [projectId, setProjectId] = useState(null);

  const finish = async (goToProject) => {
    try { await onboardingApi.complete(); } catch (_) {}
    onDone();
    if (goToProject && projectId) navigate(`/projects/${projectId}`);
  };

  const saveClient = async () => {
    if (!client.name.trim()) { toast.error("Company name is required"); return; }
    setSaving(true);
    try {
      const c = await clientsApi.create({ name: client.name.trim(), contact: client.contact.trim(), email: client.email.trim(), phone: client.phone.trim() });
      setClientId(c.id);
      toast.success("Client created");
      setStep(2);
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  const saveProject = async () => {
    if (!project.name.trim()) { toast.error("Project name is required"); return; }
    setSaving(true);
    try {
      const p = await projectsApi.create({ name: project.name.trim(), description: project.description.trim(), status: project.status, client_id: clientId });
      setProjectId(p.id);
      toast.success("Project created");
      setStep(3);
    } catch (e) { toast.error(e.message); } finally { setSaving(false); }
  };

  const steps = [
    // Step 1 — Welcome
    <div key="welcome" className="text-center" data-testid="onboarding-step-welcome">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-600 glow-violet">
        <Sparkles className="h-8 w-8 text-white" />
      </div>
      <h2 className="mt-5 text-2xl font-bold tracking-tight text-zinc-50">Welcome to Assistify OS</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-zinc-400">
        Your AI business operating system. In the next 3 minutes you'll set up your first client and project — then let AI draft your plan, proposal, contract and invoice.
      </p>
      <div className="mx-auto mt-6 grid max-w-md grid-cols-1 gap-2 text-left sm:grid-cols-3">
        {[{ i: Users, t: "Add a client" }, { i: FolderKanban, t: "Create a project" }, { i: Wand2, t: "Generate with AI" }].map((s, idx) => (
          <div key={idx} className="rounded-xl border border-white/10 bg-zinc-900/60 p-3">
            <s.i className="h-5 w-5 text-violet-400" />
            <p className="mt-2 text-xs font-medium text-zinc-300">{s.t}</p>
          </div>
        ))}
      </div>
    </div>,

    // Step 2 — Client
    <div key="client" data-testid="onboarding-step-client">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-600/15 text-violet-400"><Users className="h-5 w-5" /></div>
        <div><h2 className="text-lg font-bold text-zinc-50">Create your first client</h2><p className="text-xs text-zinc-500">Who are you doing this work for?</p></div>
      </div>
      <div className="mt-5 space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-400">Company *</label>
          <input value={client.name} onChange={(e) => setClient({ ...client, name: e.target.value })} data-testid="onb-client-company" className={inputCls} placeholder="Northwind Labs" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-zinc-400">Contact name</label>
            <input value={client.contact} onChange={(e) => setClient({ ...client, contact: e.target.value })} data-testid="onb-client-name" className={inputCls} placeholder="Ava Mitchell" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-zinc-400">Phone</label>
            <input value={client.phone} onChange={(e) => setClient({ ...client, phone: e.target.value })} data-testid="onb-client-phone" className={inputCls} placeholder="+1 555 010 1234" />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-400">Email</label>
          <input value={client.email} onChange={(e) => setClient({ ...client, email: e.target.value })} data-testid="onb-client-email" className={inputCls} placeholder="ava@northwind.co" />
        </div>
      </div>
    </div>,

    // Step 3 — Project
    <div key="project" data-testid="onboarding-step-project">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-600/15 text-violet-400"><FolderKanban className="h-5 w-5" /></div>
        <div><h2 className="text-lg font-bold text-zinc-50">Create your first project</h2><p className="text-xs text-zinc-500">The work you'll deliver for this client.</p></div>
      </div>
      <div className="mt-5 space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-400">Project name *</label>
          <input value={project.name} onChange={(e) => setProject({ ...project, name: e.target.value })} data-testid="onb-project-name" className={inputCls} placeholder="Brand Redesign" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-400">Description</label>
          <textarea value={project.description} onChange={(e) => setProject({ ...project, description: e.target.value })} data-testid="onb-project-desc" rows={3} className={`${inputCls} resize-none`} placeholder="A complete rebrand including logo, website and guidelines." />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-400">Status</label>
          <Select value={project.status} onValueChange={(v) => setProject({ ...project, status: v })}>
            <SelectTrigger data-testid="onb-project-status" className="border-white/10 bg-zinc-900"><SelectValue /></SelectTrigger>
            <SelectContent className="border-white/10 bg-zinc-900 text-zinc-100">
              {STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>,

    // Step 4 — Generate with AI
    <div key="generate" data-testid="onboarding-step-generate">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-violet-600/15 text-violet-400"><Rocket className="h-5 w-5" /></div>
        <div><h2 className="text-lg font-bold text-zinc-50">You're set — now let AI do the heavy lifting</h2><p className="text-xs text-zinc-500">Open your project and use these one-click generators.</p></div>
      </div>
      <div className="mt-5 space-y-2">
        {aiActions.map((a) => (
          <div key={a.label} className="flex items-start gap-3 rounded-xl border border-white/10 bg-zinc-900/60 p-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-violet-600/15 text-violet-400"><a.icon className="h-4 w-4" /></div>
            <div><p className="text-sm font-medium text-zinc-100">{a.label}</p><p className="text-xs text-zinc-500">{a.desc}</p></div>
          </div>
        ))}
      </div>
    </div>,
  ];

  const primary = () => {
    if (step === 0) return <button onClick={() => setStep(1)} data-testid="onboarding-next" className="flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">Let's go <ArrowRight className="h-4 w-4" /></button>;
    if (step === 1) return <button onClick={saveClient} disabled={saving} data-testid="onboarding-save-client" className="flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-60 glow-violet">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Create client <ArrowRight className="h-4 w-4" /></>}</button>;
    if (step === 2) return <button onClick={saveProject} disabled={saving} data-testid="onboarding-save-project" className="flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 disabled:opacity-60 glow-violet">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Create project <ArrowRight className="h-4 w-4" /></>}</button>;
    return <button onClick={() => finish(true)} data-testid="onboarding-finish" className="flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-violet-500 glow-violet">Open my project <ArrowRight className="h-4 w-4" /></button>;
  };

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent className="max-w-lg overflow-hidden border-white/10 bg-zinc-950 p-0 text-zinc-100 [&>button]:hidden" data-testid="onboarding-wizard">
        <DialogTitle className="sr-only">Onboarding</DialogTitle>
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-3">
          <div className="flex items-center gap-1.5">
            {[0, 1, 2, 3].map((i) => (
              <span key={i} className={`h-1.5 rounded-full transition-all ${i === step ? "w-6 bg-violet-500" : i < step ? "w-3 bg-violet-500/50" : "w-3 bg-zinc-700"}`} />
            ))}
          </div>
          <button onClick={() => finish(false)} data-testid="onboarding-skip" className="flex items-center gap-1 text-xs font-medium text-zinc-500 transition-colors hover:text-zinc-300">
            Skip <X className="h-3.5 w-3.5" />
          </button>
        </div>
        <div className="px-6 py-6">{steps[step]}</div>
        <div className="flex items-center justify-between border-t border-white/10 px-6 py-4">
          {step > 0 && step < 3 ? (
            <button onClick={() => setStep(step - 1)} data-testid="onboarding-back" className="flex items-center gap-1.5 text-sm text-zinc-400 transition-colors hover:text-zinc-200"><ArrowLeft className="h-4 w-4" /> Back</button>
          ) : <span className="flex items-center gap-1.5 text-xs text-zinc-600"><Check className="h-3.5 w-3.5 text-violet-400" /> Step {step + 1} of 4</span>}
          {primary()}
        </div>
      </DialogContent>
    </Dialog>
  );
}
