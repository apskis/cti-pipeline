// Shapes returned by console/backend. Keep in step with its to_dict() methods.

export type StageStatus = "ok" | "warn" | "fail" | "unknown";

export interface Stage {
  key: string;
  label: string;
  value: string;
  status: StageStatus;
  note: string;
}

export interface Session {
  label: string;
  started: string;
  ended: string;
  duration_s: number;
  cost_usd: number;
  turns: number;
  ok: boolean;
}

export interface Run {
  id: string;
  component: string;
  mode: string;
  kind: "scan" | "build only";
  started: string;
  ended: string;
  duration_s: number;
  cost_usd: number;
  ok: boolean;
  sessions: Session[];
}

export interface Summary {
  generated_at: string;
  counts: Record<string, number>;
  cves_tracked: number | null;
  total_cost_usd: number;
  run_days: number;
  last_scan: Run | null;
  stages: Stage[];
}

export type DeliverableStatus = "ok" | "broken" | "unchecked";

export interface ReviewFinding {
  claim: string;
  problem: string;
  source: string;
}

/** The Reviewer's verdict on one document. Written by a model: render as text only. */
export interface Review {
  verdict: "pass" | "flag";
  summary: string;
  checked_at: string;
  findings: ReviewFinding[];
  /** The document changed after this review, so the verdict may be out of date. */
  stale: boolean;
}

export interface Deliverable {
  id: string;
  kind: string;
  title: string;
  path: string;
  first_seen: string;
  modified: string;
  status: DeliverableStatus;
  problem: string | null;
  review: Review | null;
}

/** A deliverable with its body as HTML. Untrusted: sanitize before rendering. */
export interface DeliverableDocument extends Deliverable {
  html: string;
  warnings: number;
  /** True when the backend can make a branded PDF with Word on this machine. */
  pdf: boolean;
}

export interface RunReport {
  name: string;
  /** Markdown rendered by the backend with raw HTML escaped. Still sanitize it. */
  html: string;
}

export interface RunDetail extends Run {
  stages: Stage[];
  written: Deliverable[];
  report: RunReport | null;
}

export interface Cve {
  id: string;
  vendor: string;
  product: string;
  vuln_type: string;
  cvss: string;
  cvss_score: number | null;
  kev_added: string | null;
  kev_due: string | null;
  exploitation: string;
  exploited: boolean;
  relevance: string;
  hunt_id: string | null;
  bulletin_id: string | null;
  date_added: string | null;
  remediation: string;
  observed: string;
}

export interface CveRegister {
  register: string | null;
  cves: Cve[];
}

export type Channel = "email" | "teams" | "slack" | "other";

/** What the edit form sends. */
export interface StakeholderInput {
  name: string;
  role: string;
  team: string;
  /** Other names the reports use for this team, such as "Security Operations" for SOC. */
  also_known_as: string[];
  email: string;
  channel: Channel;
  /** Deliverable kinds this person gets every one of, such as "bulletin". */
  receives: string[];
  interests: string[];
  notes: string;
}

export interface Stakeholder extends StakeholderInput {
  id: string;
}

export interface StakeholderList {
  /** False until the first save; the list then lives in config/stakeholders.json. */
  exists: boolean;
  has_example: boolean;
  stakeholders: Stakeholder[];
}

export interface TeamAsk {
  name: string;
  questions: string[];
  /** IDs of the stakeholders whose team or other names match. */
  stakeholders: string[];
}

export interface Audience {
  reports: Record<string, { spec: string; teams: TeamAsk[] }>;
  /** Teams the reports name that nobody on the list covers, most named first. */
  unmatched: { team: string; reports: string[] }[];
}

/** The seven document colours, six digit hex without #, as company.json holds them. */
export interface Palette {
  primary: string;
  accent: string;
  text: string;
  muted: string;
  rule: string;
  tint: string;
  zebra: string;
}

/** What the Branding tab can change. The slug and images are changed elsewhere. */
export interface BrandInput {
  name: string;
  legal_name: string;
  department: string;
  /** The program the console belongs to, such as "Cyber Threat Intelligence". */
  program: string;
  /** The contact line in report footers. */
  contact: string;
  palette: Palette;
}

/** The company's brand, from config/companies/<slug>/company.json. */
export interface Brand extends BrandInput {
  slug: string;
  /** Colour tokens for each theme, by name without the --color- prefix, as #rrggbb. */
  light: Record<string, string>;
  dark: Record<string, string>;
  /** Changes whenever the file or an image changes, so cached images can be dropped. */
  version: string;
}

export type BrandImage = "logo" | "banner" | "symbol";

export interface ContrastCheck {
  label: string;
  foreground: string;
  background: string;
  ratio: number;
  needed: number;
  ok: boolean;
}

/** The console colours a palette gives, and every contrast check, before saving. */
export interface BrandPreview {
  light: Record<string, string>;
  dark: Record<string, string>;
  checks: ContrastCheck[];
  ok: boolean;
}
