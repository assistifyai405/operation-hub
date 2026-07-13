import { useState } from "react";
import { toast } from "sonner";
import { Rocket, FileText, ArrowLeft, Loader2, ArrowRight } from "lucide-react";
import { clientsApi, projectsApi } from "@/lib/api";
import { StepShell, PrimaryBtn, GhostBtn } from "./onboardingShared";

export function StepFirst({ data, setData, next, back }) {
  const [creating, setCreating] = useState(false);
  const c = data.company || {};

  const createProposal = async () => {
    setCreating(true);
    try {
      const client = await clientsApi.create({
        name: c.target_customers ? `${c.target_customers.split(",")[0].trim()} (sample client)` : "Your first client",
        contact: "", email: "", phone: "",
      });
      const project = await projectsApi.create({
        name: c.main_services ? `${c.main_services.split(",")[0].trim()} engagement` : "First project",
        description: c.company_summary || `A new engagement for ${c.company_name || "your business"}.`,
        status: "In Progress", client_id: client.id,
      });
      setData((d) => ({ ...d, firstProjectId: project.id }));
      toast.success("Project created — let's write your proposal");
      next();
    } catch (e) { toast.error(e.message); setCreating(false); }
  };

  return (
    <StepShell>
      <div className="text-center" data-testid="onb-step-first">
        <span className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-600 glow-violet"><Rocket className="h-8 w-8 text-white" /></span>
        <h2 className="mt-5 text-2xl font-bold text-zinc-50">Let's create real value in 60 seconds</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-zinc-500">Assistify will spin up your first real project and open the AI Proposal Generator — pre-loaded with everything it just learned about your business.</p>

        <div className="mx-auto mt-8 max-w-sm">
          <PrimaryBtn onClick={createProposal} disabled={creating} data-testid="onb-create-proposal" className="w-full justify-center">
            {creating ? <><Loader2 className="h-4 w-4 animate-spin" /> Creating…</> : <><FileText className="h-4 w-4" /> Create my first proposal</>}
          </PrimaryBtn>
          <button onClick={next} data-testid="onb-first-skip" className="mt-3 text-xs font-medium text-zinc-500 transition-colors hover:text-zinc-300">I'll explore first</button>
        </div>

        <div className="mt-8 flex items-center justify-start">
          <GhostBtn onClick={back}><ArrowLeft className="h-4 w-4" /> Back</GhostBtn>
        </div>
      </div>
    </StepShell>
  );
}
