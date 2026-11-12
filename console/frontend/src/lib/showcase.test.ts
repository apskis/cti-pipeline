import { describe, expect, it } from "vitest";

import { AGENTS, CLOUD_ROWS, FLOW, HANDOFFS, PRACTICES, ROADMAP } from "./showcase";

// House rule for UI copy: no hyphens or dashes in prose, and only the GeneLabs brand.
const prose = [
  ...HANDOFFS.flatMap((h) => [h.actor, h.model ?? "", h.does, h.leaves ?? ""]),
  ...AGENTS.flatMap((a) => [a.persona, a.name, a.role, a.cadence, a.model ?? "", a.why, a.statusNote, ...a.tools]),
  ...FLOW.flatMap((f) => [f.title, f.who, f.what]),
  ...PRACTICES.flatMap((p) => [p.title, p.body]),
  ...ROADMAP.flatMap((r) => [r.title, r.when, r.body]),
  ...CLOUD_ROWS.flatMap((r) => [r.need, r.aws, r.azure]),
];

describe("showcase copy", () => {
  it("uses no hyphens or dashes", () => {
    expect(prose.filter((text) => /[-‐-―]/.test(text))).toEqual([]);
  });

  it("marks exactly the scan and build steps as model work", () => {
    expect(FLOW.filter((f) => f.by === "model").map((f) => f.title)).toEqual([
      "Scan",
      "Build documents",
    ]);
  });

  it("has only the Coordinator acting without a model, and starts and ends with it", () => {
    expect(HANDOFFS.filter((h) => h.model === null).every((h) => h.actor === "Coordinator")).toBe(true);
    expect(HANDOFFS.at(0)?.actor).toBe("Coordinator");
    expect(HANDOFFS.at(-1)?.leaves).toBeNull();
  });
});
