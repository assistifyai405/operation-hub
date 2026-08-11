/**
 * @jest-environment node
 */
import {
  readHelpProgress,
  writeHelpProgress,
  markTutorial,
  markTour,
  isTutorialCompleted,
  isTourCompleted,
} from "./persistence";

describe("help persistence", () => {
  const store = {};
  beforeEach(() => {
    Object.keys(store).forEach((k) => delete store[k]);
    global.localStorage = {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
    };
  });

  test("marks tutorial completed with version", () => {
    markTutorial("user1", "crm", "completed", "1");
    expect(isTutorialCompleted("user1", "crm", "1")).toBe(true);
    expect(isTutorialCompleted("user1", "crm", "2")).toBe(false);
    expect(readHelpProgress("user1", "crm").tutorialStatus).toBe("completed");
  });

  test("marks tour skipped and completed separately", () => {
    markTour("user1", "crm", "skipped", "1");
    expect(isTourCompleted("user1", "crm", "1")).toBe(false);
    markTour("user1", "crm", "completed", "1");
    expect(isTourCompleted("user1", "crm", "1")).toBe(true);
  });

  test("writeHelpProgress merges patches without business data fields", () => {
    writeHelpProgress("user1", "crm", { tutorialStatus: "completed", tutorialVersion: "1" });
    const next = writeHelpProgress("user1", "crm", { tourStatus: "completed", tourVersion: "1" });
    expect(next.tutorialStatus).toBe("completed");
    expect(next.tourStatus).toBe("completed");
    expect(next.email).toBeUndefined();
    expect(next.leadTitle).toBeUndefined();
  });
});
