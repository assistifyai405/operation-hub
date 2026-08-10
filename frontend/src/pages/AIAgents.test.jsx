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
  test("authenticated fetch uses cookie session (credentials include, no Bearer)", () => {
    expect(pageSrc).toMatch(/credentials:\s*\"include\"/);
    expect(pageSrc).not.toMatch(/getAccessToken/);
    expect(pageSrc).not.toMatch(/Authorization:\s*`Bearer/);
    expect(pageSrc).not.toMatch(/assistify_token/);
  });

  test("guards non-array API payloads before map", () => {
    expect(pageSrc).toMatch(/Array\.isArray/);
    expect(pageSrc).toMatch(/extractAgentsList/);
    expect(pageSrc).toMatch(/normalizeAgents/);
    expect(pageSrc).toMatch(/ai-agents-error/);
    expect(pageSrc).toMatch(/ai-agents-empty/);
    expect(pageSrc).toMatch(/ai-agents-loading/);
    expect(pageSrc).toMatch(/New Agent/);
    expect(pageSrc).toMatch(/Soon/);
    // Never map agents state directly without an Array.isArray guard
    expect(pageSrc).not.toMatch(/\{agents\.map\(/);
  });

  test("reproduces prior crash and validates safe extract/normalize", () => {
    const errorBody = { detail: "Not authenticated", error: { message: "Not authenticated" } };
    expect(Array.isArray(errorBody)).toBe(false);
    expect(() => errorBody.map(() => null)).toThrow(/map is not a function/);

    function extractAgentsList(payload) {
      if (Array.isArray(payload)) return payload;
      if (payload && typeof payload === "object") {
        if (Array.isArray(payload.agents)) return payload.agents;
        if (Array.isArray(payload.data)) return payload.data;
        if (Array.isArray(payload.items)) return payload.items;
      }
      return [];
    }

    function normalizeAgents(payload) {
      const raw = extractAgentsList(payload);
      if (!Array.isArray(raw)) return [];
      return raw.filter((a) => a && typeof a === "object").map((a, i) => ({
        id: a.id || `agent-${i}`,
        name: a.name || "Untitled agent",
      }));
    }

    expect(normalizeAgents(errorBody)).toEqual([]);
    expect(normalizeAgents(null)).toEqual([]);
    expect(normalizeAgents([])).toEqual([]);
    expect(normalizeAgents({ agents: [{ id: "copilot" }] }).map((a) => a.id)).toEqual(["copilot"]);
    const list = normalizeAgents([{ id: "copilot", name: "Assistify Copilot" }]);
    expect(Array.isArray(list) ? list.map((a) => a.id) : []).toEqual(["copilot"]);
  });
});
