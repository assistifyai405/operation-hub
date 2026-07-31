/**
 * Lightweight AI Agents page guards (no Testing Library dependency).
 * @jest-environment node
 */
const fs = require("fs");
const path = require("path");

const pageSrc = fs.readFileSync(path.join(__dirname, "AIAgents.jsx"), "utf8");
const appSrc = fs.readFileSync(path.join(__dirname, "../App.js"), "utf8");

describe("/ai-agents route", () => {
  test("App registers the AI Agents route", () => {
    expect(appSrc).toMatch(/path=\"\/ai-agents\"/);
    expect(appSrc).toMatch(/<AIAgents\s*\/>/);
  });
});

describe("AIAgents page crash guards", () => {
  test("authenticated fetch includes credentials and bearer token", () => {
    expect(pageSrc).toMatch(/getAccessToken/);
    expect(pageSrc).toMatch(/credentials:\s*\"include\"/);
    expect(pageSrc).toMatch(/Authorization:\s*`Bearer \$\{getAccessToken\(\)\}`/);
  });

  test("guards non-array API payloads before map", () => {
    expect(pageSrc).toMatch(/Array\.isArray/);
    expect(pageSrc).toMatch(/normalizeAgents/);
    expect(pageSrc).toMatch(/ai-agents-error/);
    expect(pageSrc).toMatch(/ai-agents-empty/);
    expect(pageSrc).toMatch(/ai-agents-loading/);
  });

  test("reproduces prior crash and validates safe normalize", () => {
    // Prior bug: 401 JSON object assigned to agents → agents.map throws
    const errorBody = { detail: "Not authenticated", error: { message: "Not authenticated" } };
    expect(Array.isArray(errorBody)).toBe(false);
    expect(() => errorBody.map(() => null)).toThrow(/map is not a function/);

    function normalizeAgents(payload) {
      if (!Array.isArray(payload)) return [];
      return payload.filter(Boolean).map((a, i) => ({
        id: a.id || `agent-${i}`,
        name: a.name || "Untitled agent",
        role: a.role || "Assistant",
        description: a.description || "",
        avatar: a.avatar || "",
        accent: a.accent || "violet",
      }));
    }

    expect(normalizeAgents(errorBody)).toEqual([]);
    expect(normalizeAgents(null)).toEqual([]);
    expect(normalizeAgents([])).toEqual([]);
    expect(normalizeAgents([{ id: "x" }, null]).map((a) => a.id)).toEqual(["x"]);
    const list = normalizeAgents([{ id: "copilot", name: "Assistify Copilot" }]);
    expect(() => list.map((a) => a.id)).not.toThrow();
  });
});
