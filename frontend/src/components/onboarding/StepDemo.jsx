/**
 * Quarantined demo onboarding step (Sprint 28).
 * Not used by the current Onboarding flow. Does NOT auto-seed sample data.
 * Kept only so accidental rewires cannot silently invent a demo workspace.
 */
import { ArrowRight, ArrowLeft } from "lucide-react";
import { StepShell, PrimaryBtn, GhostBtn } from "./onboardingShared";

export function StepDemo({ next, back }) {
  return (
    <StepShell>
      <div data-testid="onb-step-demo">
        <h2 className="text-2xl font-bold text-zinc-50">Sample data is disabled</h2>
        <p className="mt-2 text-sm text-zinc-400">
          Assistify no longer seeds fake clients, pipeline, or revenue during onboarding.
          Add your own clients and projects from the dashboard instead.
        </p>
        <div className="mt-8 flex items-center justify-between">
          <GhostBtn onClick={back}><ArrowLeft className="h-4 w-4" /> Back</GhostBtn>
          <PrimaryBtn onClick={next} data-testid="onb-demo-continue">Continue <ArrowRight className="h-4 w-4" /></PrimaryBtn>
        </div>
      </div>
    </StepShell>
  );
}
