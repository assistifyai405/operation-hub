/**
 * Persist help tutorial / guided-tour completion per user + module + version.
 * Never stores business content — only status flags.
 */

function key(userId, moduleId) {
  return `assistify_help_${userId || "anon"}_${moduleId}`;
}

export function readHelpProgress(userId, moduleId) {
  try {
    const raw = localStorage.getItem(key(userId, moduleId));
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function writeHelpProgress(userId, moduleId, patch) {
  try {
    const prev = readHelpProgress(userId, moduleId) || {};
    const next = {
      ...prev,
      ...patch,
      updatedAt: new Date().toISOString(),
    };
    localStorage.setItem(key(userId, moduleId), JSON.stringify(next));
    return next;
  } catch {
    return null;
  }
}

export function isTutorialCompleted(userId, moduleId, version) {
  const progress = readHelpProgress(userId, moduleId);
  if (!progress) return false;
  if (progress.tutorialStatus !== "completed") return false;
  if (version && progress.tutorialVersion && progress.tutorialVersion !== version) return false;
  return true;
}

export function isTourCompleted(userId, moduleId, version) {
  const progress = readHelpProgress(userId, moduleId);
  if (!progress) return false;
  if (progress.tourStatus !== "completed") return false;
  if (version && progress.tourVersion && progress.tourVersion !== version) return false;
  return true;
}

export function markTutorial(userId, moduleId, status, version) {
  return writeHelpProgress(userId, moduleId, {
    tutorialStatus: status,
    tutorialVersion: version,
  });
}

export function markTour(userId, moduleId, status, version) {
  return writeHelpProgress(userId, moduleId, {
    tourStatus: status,
    tourVersion: version,
  });
}
