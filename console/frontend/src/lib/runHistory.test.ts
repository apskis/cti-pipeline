import { describe, expect, it } from "vitest";

import { RUNS } from "../test/fixtures";
import { costByDay, usedSeries } from "./runHistory";

describe("costByDay", () => {
  it("splits each day's cost into scan, build and report, oldest day first", () => {
    const days = costByDay(RUNS);
    expect(days.map((d) => d.day)).toEqual(["2026-10-10", "2026-11-10"]);
    expect(days[1]?.cost).toEqual({ scan: 8.5, build: 0.5, report: 4.36, other: 0 });
  });

  it("returns nothing for no runs", () => {
    expect(costByDay([])).toEqual([]);
  });
});

describe("usedSeries", () => {
  it("leaves out series with no cost", () => {
    expect(usedSeries(costByDay(RUNS))).toEqual(["scan", "build", "report"]);
  });
});
