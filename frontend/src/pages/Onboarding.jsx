import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { Sparkles, Loader2, LogOut } from "lucide-react";
import { onboardingApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { ProgressRail } from "@/components/onboarding/onboardingShared";
import { StepWelcome } from "@/components/onboarding/StepWelcome";
import { StepCompany } from "@/components/onboarding/StepCompany";
import { StepDiscovery } from "@/components/onboarding/StepDiscovery";
import { StepBrain } from "@/components/onboarding/StepBrain";
import { StepAutomations } from "@/components/onboarding/StepAutomations";
import { StepDemo } from "@/components/onboarding/StepDemo";
import { StepFirst } from "@/components/onboarding/StepFirst";
import { StepSuccess } from "@/components/onboarding/StepSuccess";

export default function Onboarding() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [step, setStep] = useState(0);
  const [data, setData] = useState({ company: { language: "en" } });
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    onboardingApi.getState()
      .then((s) => {
        if (s.step) setStep(Math.min(s.step, 7));
        if (s.data && Object.keys(s.data).length) setData((d) => ({ ...d, ...s.data }));
      })
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  const persist = useCallback((nextStep, nextData) => {
    onboardingApi.saveState({ step: nextStep, data: nextData || data }).catch(() => {});
  }, [data]);

  const goto = (s) => { setStep(s); persist(s, data); window.scrollTo({ top: 0 }); };
  const next = () => goto(Math.min(step + 1, 7));
  const back = () => goto(Math.max(step - 1, 0));

  const saveExit = async () => {
    await onboardingApi.saveState({ step, data }).catch(() => {});
    navigate("/dashboard");
  };

  const complete = useCallback(() => {
    onboardingApi.saveState({ step: 7, data, completed: true }).catch(() => {});
    onboardingApi.complete().catch(() => {});
    setUser((u) => (u ? { ...u, onboardingCompleted: true } : u));
  }, [data, setUser]);

  const finish = (path) => { complete(); navigate(path || "/dashboard"); };

  const stepProps = { data, setData, next, back };
  const steps = [
    <StepWelcome key="w" {...stepProps} />,
    <StepCompany key="c" {...stepProps} />,
    <StepDiscovery key="d" {...stepProps} />,
    <StepBrain key="b" {...stepProps} />,
    <StepAutomations key="a" {...stepProps} />,
    <StepDemo key="dm" {...stepProps} />,
    <StepFirst key="f" {...stepProps} />,
    <StepSuccess key="s" data={data} finish={finish} onComplete={complete} />,
  ];

  return (
    <div className="relative min-h-screen bg-black text-zinc-50" data-testid="onboarding-page">
      <div className="pointer-events-none absolute inset-0 opacity-40" style={{ backgroundImage: "radial-gradient(600px circle at 20% 0%, rgba(139,92,246,0.12), transparent 60%), radial-gradient(500px circle at 90% 20%, rgba(34,211,238,0.08), transparent 55%)" }} />
      <header className="relative z-10 flex items-center justify-between px-5 py-5 sm:px-10">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-violet-600 glow-violet"><Sparkles className="h-4 w-4 text-white" /></span>
          <span className="text-sm font-bold tracking-tight">Assistify <span className="text-violet-400">OS</span></span>
        </div>
        <ProgressRail step={step} />
        {step < 7 && (
          <button onClick={saveExit} data-testid="onboarding-save-exit" className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-500 transition-colors hover:text-zinc-300">
            <LogOut className="h-3.5 w-3.5" /> Save & exit
          </button>
        )}
        {step >= 7 && <span className="w-16" />}
      </header>

      <main className="relative z-10 flex min-h-[calc(100vh-88px)] items-center justify-center px-5 py-8 sm:px-10">
        {!loaded ? (
          <Loader2 className="h-7 w-7 animate-spin text-zinc-700" />
        ) : (
          <AnimatePresence mode="wait">{steps[step]}</AnimatePresence>
        )}
      </main>
    </div>
  );
}
