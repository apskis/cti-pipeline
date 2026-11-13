import type { Run, Session } from "../api/types";

export type Series = "scan" | "build" | "review" | "report" | "other";

export const SERIES_LABELS: Record<Series, string> = {
  scan: "Analyst (scan)",
  build: "Writer (documents)",
  review: "Reviewer (checks)",
  report: "Reporter (weekly report)",
  other: "Other agents",
};

export interface DayCost {
  day: string; // YYYY-MM-DD
  cost: Record<Series, number>;
}

function seriesOf(run: Run, session: Session): Series {
  if (run.component === "reporting") return "report";
  if (run.component !== "bulletin-scan") return "other";
  if (session.label.startsWith("build")) return "build";
  return session.label === "review" ? "review" : "scan";
}

/** Model cost per day, split by what the money was spent on. Oldest day first. */
export function costByDay(runs: Run[]): DayCost[] {
  const days = new Map<string, Record<Series, number>>();
  for (const run of runs) {
    for (const session of run.sessions) {
      const key = session.started.slice(0, 10);
      const cost = days.get(key) ?? { scan: 0, build: 0, review: 0, report: 0, other: 0 };
      cost[seriesOf(run, session)] += session.cost_usd;
      days.set(key, cost);
    }
  }
  return [...days.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, cost]) => ({ day, cost }));
}

/** Series that have any cost, so the legend never lists an empty one. */
export function usedSeries(days: DayCost[]): Series[] {
  return (Object.keys(SERIES_LABELS) as Series[]).filter((s) => days.some((d) => d.cost[s] > 0));
}
