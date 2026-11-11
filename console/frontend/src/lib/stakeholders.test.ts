import { describe, expect, it } from "vitest";

import { AUDIENCE, STAKEHOLDERS } from "../test/fixtures";
import { distributionList, recipientsFor, reportsFor, splitList } from "./stakeholders";

const [jordan, priya, dana] = STAKEHOLDERS.stakeholders;

describe("stakeholders", () => {
  it("finds the reports that name a person's team", () => {
    expect(reportsFor(jordan!, AUDIENCE).map((r) => r.id)).toEqual(["CTI26-137"]);
    expect(reportsFor(dana!, AUDIENCE)).toEqual([]);
  });

  it("lists a report's teams, gaps and people who get every report of its kind", () => {
    const r = recipientsFor("CTI26-137", "bulletin", AUDIENCE, STAKEHOLDERS.stakeholders);
    expect(r.teams.map((t) => [t.name, t.people.map((p) => p.name)])).toEqual([
      ["SOC", ["Jordan Reyes"]],
      ["Lab Operations", []],
    ]);
    expect(r.byKind.map((p) => p.name)).toEqual(["Priya Nair"]);
    expect(r.everyone.map((p) => p.id)).toEqual([jordan!.id, priya!.id]);
  });

  it("counts each person once and handles an unknown report", () => {
    const both = { ...jordan!, receives: ["bulletin"] };
    const r = recipientsFor("CTI26-137", "bulletin", AUDIENCE, [both]);
    expect(r.everyone).toHaveLength(1);
    expect(recipientsFor("CTI26-1", "hunt", AUDIENCE, [jordan!]).teams).toEqual([]);
  });

  it("builds a To line without people who have no email", () => {
    expect(distributionList([jordan!, dana!])).toBe("Jordan Reyes <jordan@genelabs.example>");
  });

  it("splits comma separated fields", () => {
    expect(splitList(" SOC, ,Security Operations ")).toEqual(["SOC", "Security Operations"]);
  });
});
