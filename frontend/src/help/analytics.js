import { track } from "@/lib/analytics";

/** Help analytics — module id only; never user-entered business data. */
export const helpEvents = {
  opened: (module) => track("help_opened", { module }),
  tutorialStarted: (module) => track("tutorial_started", { module }),
  tutorialCompleted: (module) => track("tutorial_completed", { module }),
  tutorialSkipped: (module) => track("tutorial_skipped", { module }),
  guidedTourStarted: (module) => track("guided_tour_started", { module }),
  guidedTourCompleted: (module) => track("guided_tour_completed", { module }),
  guidedTourSkipped: (module) => track("guided_tour_skipped", { module }),
};
