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

export interface Deliverable {
  id: string;
  kind: string;
  title: string;
  path: string;
  first_seen: string;
  modified: string;
  status: DeliverableStatus;
  problem: string | null;
}

/** A deliverable with its body as HTML. Untrusted: sanitize before rendering. */
export interface DeliverableDocument extends Deliverable {
  html: string;
  warnings: number;
}
