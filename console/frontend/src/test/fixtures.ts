import type { Deliverable, DeliverableDocument, Run, Session, Summary } from "../api/types";

const session = (label: string, started: string, cost: number): Session => ({
  label,
  started,
  ended: started,
  duration_s: 60,
  cost_usd: cost,
  turns: 5,
  ok: true,
});

export const RUNS: Run[] = [
  {
    id: "bulletin-scan-1",
    component: "bulletin-scan",
    mode: "weekly",
    kind: "scan",
    started: "2026-11-10T14:00:00+00:00",
    ended: "2026-11-10T15:00:00+00:00",
    duration_s: 1200,
    cost_usd: 9,
    ok: true,
    sessions: [
      session("scan", "2026-11-10T14:00:00+00:00", 8.5),
      session("build-1", "2026-11-10T14:30:00+00:00", 0.5),
    ],
  },
  {
    id: "reporting-1",
    component: "reporting",
    mode: "weekly",
    kind: "scan",
    started: "2026-11-10T16:00:00+00:00",
    ended: "2026-11-10T16:10:00+00:00",
    duration_s: 600,
    cost_usd: 4.36,
    ok: true,
    sessions: [session("scan", "2026-11-10T16:00:00+00:00", 4.36)],
  },
  {
    id: "bulletin-scan-0",
    component: "bulletin-scan",
    mode: "weekly",
    kind: "scan",
    started: "2026-10-10T01:00:00+00:00",
    ended: "2026-10-10T01:20:00+00:00",
    duration_s: 1200,
    cost_usd: 7.66,
    ok: true,
    sessions: [session("scan", "2026-10-10T01:00:00+00:00", 7.66)],
  },
];

export const SUMMARY: Summary = {
  generated_at: "2026-11-10T22:00:00+00:00",
  counts: { bulletin: 151, hunt: 54, awareness: 19 },
  cves_tracked: 67,
  total_cost_usd: 49.07,
  run_days: 4,
  last_scan: RUNS[0] ?? null,
  stages: [
    { key: "feeds", label: "Feeds", value: "189 items, 9 of 10 up", status: "warn", note: "Failed: HHS HC3" },
    { key: "scan", label: "Scan", value: "19 min, 0 searches", status: "warn", note: "From the scan report" },
    { key: "triage", label: "Triage", value: "35 new IDs", status: "ok", note: "23 bulletins and 12 hunts" },
    { key: "build", label: "Build", value: "23 passes", status: "ok", note: "Builder passes" },
    { key: "check", label: "Check", value: "224 docs, 0 broken", status: "ok", note: "No broken documents" },
    { key: "deliver", label: "Deliver", value: "38 new", status: "unknown", note: "First seen today" },
  ],
};

const deliverable = (id: string, kind: string, title: string, status: Deliverable["status"]) => ({
  id,
  kind,
  title,
  path: `bulletin-scan/${id}.docx`,
  first_seen: "2026-11-10",
  modified: "2026-11-10T20:00:00",
  status,
  problem: status === "broken" ? "8 one letter paragraphs" : null,
});

export const DELIVERABLES: Deliverable[] = [
  deliverable("CTI26-137", "bulletin", "IBM Aspera Faspex RCE", "ok"),
  deliverable("CTI26-136", "bulletin", "Broken Example", "broken"),
  deliverable("TH26-54", "hunt", "Turla Exchange Email Harvesting", "ok"),
];

export const DOCUMENT: DeliverableDocument = {
  ...deliverable("CTI26-137", "bulletin", "IBM Aspera Faspex RCE", "ok"),
  html: '<h3>Why This Matters</h3><p>Patch now.</p><script>window.hacked = true</script>',
  warnings: 0,
};
