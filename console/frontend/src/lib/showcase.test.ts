import { describe, expect, it } from "vitest";

import { AGENTS, CLOUD_ROWS, FLOW, PRACTICES } from "./showcase";

// House rule for UI copy: no hyphens or dashes in prose, and only the GeneLabs brand.
const prose = [
  ...AGENTS.flatMap((a) => [a.name, a.role, a.cadence, a.model ?? "", a.why, a.statusNote, ...a.tools]),
  ...FLOW.flatMap((f) => [f.title, f.who, f.what]),
  ...PRACTICES.flatMap((p) => [p.title, p.body]),
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
});
