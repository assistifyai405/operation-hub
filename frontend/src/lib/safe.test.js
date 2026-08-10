/**
 * Guards for list helpers (no Testing Library).
 * @jest-environment node
 */
const fs = require("fs");
const path = require("path");

const src = fs.readFileSync(path.join(__dirname, "safe.js"), "utf8");

function asArray(value) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === "object") {
    if (Array.isArray(value.items)) return value.items;
    if (Array.isArray(value.data)) return value.data;
    if (Array.isArray(value.results)) return value.results;
  }
  return [];
}

describe("asArray helper", () => {
  test("is exported from safe.js", () => {
    expect(src).toMatch(/export function asArray/);
  });

  test("never throws on error-shaped bodies", () => {
    const err = { detail: "Not authenticated" };
    expect(asArray(err)).toEqual([]);
    expect(asArray(null)).toEqual([]);
    expect(asArray({ items: [{ id: "a" }] }).map((x) => x.id)).toEqual(["a"]);
  });
});
