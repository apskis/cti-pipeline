import type {
  Audience,
  Brand,
  BrandPreview,
  Cve,
  CveRegister,
  Deliverable,
  DeliverableDocument,
  Run,
  RunDetail,
  Session,
  Stakeholder,
  StakeholderList,
  Summary,
} from "../api/types";

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
  review: null,
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
  pdf: false,
};

export const RUN_DETAIL: RunDetail = {
  ...(RUNS[0] as Run),
  stages: SUMMARY.stages,
  written: [DELIVERABLES[0] as Deliverable],
  report: {
    name: "scan-2026-11-10.md",
    html: '<h1>CTI Daily Scan</h1><p>Run conditions.</p><img src="https://tracker.example/p.gif">',
  },
};

const cve = (id: string, overrides: Partial<Cve>): Cve => ({
  id,
  vendor: "Acme",
  product: "Widget",
  vuln_type: "RCE",
  cvss: "9.8 CRITICAL",
  cvss_score: 9.8,
  kev_added: null,
  kev_due: null,
  exploitation: "None known",
  exploited: false,
  relevance: "",
  hunt_id: null,
  bulletin_id: null,
  date_added: "2026-11-10",
  remediation: "Patch",
  observed: "CANNOT CONFIRM",
  ...overrides,
});

export const CVES: CveRegister = {
  register: "bulletin-scan/registers/CVE_Register_2026.xlsx",
  cves: [
    cve("CVE-2026-0003", {
      date_added: "2026-10-08",
      cvss_score: 7.5,
      vendor: "Globex",
    }),
    cve("CVE-2026-0001", {
      exploited: true,
      exploitation: "ITW (CISA KEV)",
      kev_added: "2026-11-09",
      kev_due: "2026-11-12",
      bulletin_id: "CTI26-137",
      hunt_id: "TH26-54",
    }),
    cve("CVE-2026-0002", { cvss_score: 5.5 }),
  ],
};

const person = (id: string, name: string, team: string, extra: Partial<Stakeholder> = {}): Stakeholder => ({
  id,
  name,
  role: "",
  team,
  also_known_as: [],
  email: `${name.split(" ")[0]?.toLowerCase()}@genelabs.example`,
  channel: "email",
  receives: [],
  interests: [],
  notes: "",
  ...extra,
});

export const STAKEHOLDERS: StakeholderList = {
  exists: true,
  has_example: true,
  stakeholders: [
    person("sh-00000001", "Jordan Reyes", "SOC", {
      role: "SOC lead",
      also_known_as: ["Security Operations"],
      receives: ["hunt"],
    }),
    person("sh-00000002", "Priya Nair", "Vulnerability Management", { receives: ["bulletin"] }),
    person("sh-00000003", "Dana Whitfield", "Leadership", { email: "" }),
  ],
};

export const NO_STAKEHOLDERS: StakeholderList = { exists: false, has_example: true, stakeholders: [] };

export const AUDIENCE: Audience = {
  reports: {
    "CTI26-137": {
      spec: "bulletin-scan/state/_work/CTI26-137-spec.json",
      teams: [
        { name: "SOC", questions: ["Would Falcon see it?"], stakeholders: ["sh-00000001"] },
        { name: "Lab Operations", questions: ["Which instruments?"], stakeholders: [] },
      ],
    },
  },
  unmatched: [{ team: "Lab Operations", reports: ["CTI26-137"] }],
};

export const BRAND: Brand = {
  slug: "genelabs",
  name: "GeneLabs",
  legal_name: "GeneLabs LLC",
  department: "Enterprise Information Security",
  program: "Cyber Threat Intelligence",
  contact: "secops@genelabs.com  |  ServiceNow",
  palette: {
    primary: "103B32",
    accent: "167D61",
    text: "202C29",
    muted: "676765",
    rule: "A2BFAE",
    tint: "EAF3EE",
    zebra: "F4F9F6",
  },
  light: { accent: "#167d61", brand: "#103b32" },
  dark: { accent: "#3fb48c" },
  version: "abc123def456",
};

export const BRAND_PREVIEW: BrandPreview = {
  light: { accent: "#167d61", brand: "#103b32" },
  dark: { accent: "#1ea883" },
  checks: [
    { label: "Body text on white", foreground: "#202c29", background: "#ffffff", ratio: 14.45, needed: 4.5, ok: true },
    { label: "Accent on white (links)", foreground: "#167d61", background: "#ffffff", ratio: 5.07, needed: 4.5, ok: true },
  ],
  ok: true,
};
