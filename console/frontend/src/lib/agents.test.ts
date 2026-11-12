import { describe, expect, it } from "vitest";

import {
  componentAgent,
  joinAgents,
  kindAgents,
  runAgents,
  sessionName,
  stageAgent,
} from "./agents";
import { AGENTS, HANDOFFS } from "./showcase";

describe("agent names", () => {
  it("names builder sessions as Writer passes and others by component", () => {
    expect(sessionName("bulletin-scan", "scan")).toBe("Analyst");
    expect(sessionName("bulletin-scan", "build-2")).toBe("Writer, pass 2");
    expect(sessionName("reporting", "scan")).toBe("Reporter");
  });

  it("lists the agents in a run once each, in order", () => {
    const agents = runAgents("bulletin-scan", ["scan", "build-1", "build-2"]);
    expect(agents).toEqual(["Analyst", "Writer"]);
    expect(joinAgents(agents)).toBe("the Analyst and the Writer");
    expect(joinAgents(["Writer"])).toBe("the Writer");
  });

  it("says who does each stage and who made each kind", () => {
    expect(stageAgent("scan")).toBe("Analyst");
    expect(stageAgent("build")).toBe("Writer");
    expect(stageAgent("deliver")).toBe("Coordinator");
    expect(kindAgents("weekly")).toBe("Written by the Reporter");
    expect(kindAgents("hunt")).toBe("Picked by the Analyst, written by the Writer");
  });

  it("uses the same names as the How it's built tab", () => {
    const personas = new Set([...AGENTS.map((a) => a.persona), ...HANDOFFS.map((h) => h.actor)]);
    for (const c of ["bulletin-scan", "reporting", "perimeter-scan", "threat-hunting", "documentation-sync", "program-console"]) {
      expect(personas).toContain(componentAgent(c));
    }
    for (const key of ["feeds", "scan", "triage", "build", "check", "deliver"]) {
      expect(personas).toContain(stageAgent(key));
    }
  });
});
