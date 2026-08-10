/**
 * @jest-environment node
 */
import {
  isProductTourDone,
  markProductTourDone,
  markProductTourEligible,
  isProductTourEligible,
  productTourStorageKey,
} from "./productTour";

describe("product tour persistence", () => {
  const store = {};
  beforeEach(() => {
    Object.keys(store).forEach((k) => delete store[k]);
    global.localStorage = {
      getItem: (k) => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: (k) => { delete store[k]; },
    };
  });

  test("defaults to not done", () => {
    expect(isProductTourDone("user-1")).toBe(false);
    expect(productTourStorageKey("user-1")).toBe("assistify_product_tour_user-1");
  });

  test("only first-run eligible users see the tour", () => {
    expect(isProductTourEligible("user-1")).toBe(false);
    markProductTourEligible("user-1");
    expect(isProductTourEligible("user-1")).toBe(true);
    markProductTourDone("user-1");
    expect(isProductTourEligible("user-1")).toBe(false);
    expect(isProductTourDone("user-1")).toBe(true);
  });
});
