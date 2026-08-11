import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { getHelpModule } from "@/help/registry";
import { helpEvents } from "@/help/analytics";
import { markTour, markTutorial } from "@/help/persistence";

const HelpContext = createContext(null);

export function HelpProvider({ children }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [panelModule, setPanelModule] = useState(null);
  const [tutorialModule, setTutorialModule] = useState(null);
  const [tourModule, setTourModule] = useState(null);
  const [tourStepIndex, setTourStepIndex] = useState(0);

  const openHelp = useCallback((moduleId) => {
    const mod = getHelpModule(moduleId);
    if (!mod) return;
    setPanelModule(mod.id);
    helpEvents.opened(mod.contentId || mod.id);
  }, []);

  const closeHelp = useCallback(() => {
    setPanelModule(null);
  }, []);

  const startTutorial = useCallback((moduleId) => {
    const mod = getHelpModule(moduleId);
    if (!mod?.hasFullTutorial) return;
    const id = mod.contentId || mod.id;
    setTutorialModule(id);
    helpEvents.tutorialStarted(id);
  }, []);

  const closeTutorial = useCallback((status = "skipped") => {
    if (!tutorialModule) return;
    const mod = getHelpModule(tutorialModule);
    const id = mod?.contentId || tutorialModule;
    if (status === "completed") {
      markTutorial(user?.id, id, "completed", mod?.tutorialVersion || "1");
      helpEvents.tutorialCompleted(id);
    } else {
      markTutorial(user?.id, id, "skipped", mod?.tutorialVersion || "1");
      helpEvents.tutorialSkipped(id);
    }
    setTutorialModule(null);
  }, [tutorialModule, user?.id]);

  const startTour = useCallback((moduleId) => {
    const mod = getHelpModule(moduleId);
    if (!mod?.hasGuidedTour) return;
    const id = mod.contentId || mod.id;
    const target = mod.tourRoute || mod.route;
    setPanelModule(null);
    setTourModule(id);
    setTourStepIndex(0);
    helpEvents.guidedTourStarted(id);
    if (typeof window !== "undefined" && target && !window.location.pathname.startsWith(target)) {
      navigate(`${target}?guidedTour=${encodeURIComponent(id)}`);
    }
  }, [navigate]);

  const advanceTour = useCallback((delta = 1) => {
    setTourStepIndex((i) => Math.max(0, i + delta));
  }, []);

  const closeTour = useCallback((status = "skipped") => {
    if (!tourModule) return;
    const mod = getHelpModule(tourModule);
    const id = mod?.contentId || tourModule;
    if (status === "completed") {
      markTour(user?.id, id, "completed", mod?.tourVersion || "1");
      helpEvents.guidedTourCompleted(id);
    } else {
      markTour(user?.id, id, "skipped", mod?.tourVersion || "1");
      helpEvents.guidedTourSkipped(id);
    }
    setTourModule(null);
    setTourStepIndex(0);
  }, [tourModule, user?.id]);

  const restartTour = useCallback(() => {
    if (!tourModule) return;
    setTourStepIndex(0);
  }, [tourModule]);

  const value = useMemo(() => ({
    panelModule,
    tutorialModule,
    tourModule,
    tourStepIndex,
    openHelp,
    closeHelp,
    startTutorial,
    closeTutorial,
    startTour,
    advanceTour,
    closeTour,
    restartTour,
    setTourStepIndex,
  }), [
    panelModule,
    tutorialModule,
    tourModule,
    tourStepIndex,
    openHelp,
    closeHelp,
    startTutorial,
    closeTutorial,
    startTour,
    advanceTour,
    closeTour,
    restartTour,
  ]);

  return <HelpContext.Provider value={value}>{children}</HelpContext.Provider>;
}

export function useHelp() {
  const ctx = useContext(HelpContext);
  if (!ctx) {
    throw new Error("useHelp must be used within HelpProvider");
  }
  return ctx;
}

/** Safe hook when provider may be absent (tests). */
export function useHelpOptional() {
  return useContext(HelpContext);
}
