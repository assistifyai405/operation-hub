export function productTourStorageKey(userId) {
  return `assistify_product_tour_${userId || "anon"}`;
}

function eligibleKey(userId) {
  return `assistify_product_tour_eligible_${userId || "anon"}`;
}

export function isProductTourDone(userId) {
  try {
    return localStorage.getItem(productTourStorageKey(userId)) === "done";
  } catch {
    return false;
  }
}

export function markProductTourDone(userId) {
  try {
    localStorage.setItem(productTourStorageKey(userId), "done");
    localStorage.removeItem(eligibleKey(userId));
  } catch {
    /* ignore */
  }
}

/** Call after onboarding completes so the tour only appears for real first-run users. */
export function markProductTourEligible(userId) {
  try {
    if (isProductTourDone(userId)) return;
    localStorage.setItem(eligibleKey(userId), "1");
  } catch {
    /* ignore */
  }
}

export function isProductTourEligible(userId) {
  try {
    return localStorage.getItem(eligibleKey(userId)) === "1" && !isProductTourDone(userId);
  } catch {
    return false;
  }
}
