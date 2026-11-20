import type { Deliverable, Guardrail, GuardrailCounts, GuardrailStatus, StageStatus } from "../api/types";

// The kinds the self check loop reads. A CVE brief is a table rendered by code from the register.
export const CHECKED_KINDS = new Set(["bulletin", "hunt", "awareness"]);

/** The guardrail gates in the order the panel lists them, with the words a reader sees. */
export const GATES: { key: string; label: string }[] = [
  { key: "sources", label: "Every claim has a source that says it" },
  { key: "cve_facts", label: "CVE details match NVD" },
  { key: "house_rules", label: "House rules" },
  { key: "consistency", label: "Agrees with itself" },
  { key: "reasoning", label: "Bias and reasoning check" },
  { key: "wording", label: "Confidence wording (checked in code)" },
];

interface StatusView {
  pill: StageStatus;
  label: string;
}

// Words, not just colour, so the state reads without colour vision.
export const STATUS_VIEW: Record<GuardrailStatus, StatusView> = {
  verified: { pill: "ok", label: "Verified" },
  "self-corrected": { pill: "ok", label: "Fixed itself" },
  fixing: { pill: "unknown", label: "Checking" },
  "needs-human": { pill: "warn", label: "Needs you" },
};

const plural = (n: number, one: string, many: string): string => `${n} ${n === 1 ? one : many}`;

const unchecked = (g: Guardrail): number =>
  GATES.filter((gate) => (g.gates[gate.key] ?? "unchecked") === "unchecked").length;

/** Never claim "every guardrail" when some were not run: say how many were skipped. */
const passed = (g: Guardrail): string => {
  const skipped = unchecked(g);
  return skipped === 0
    ? "passed every guardrail"
    : `passed every check it ran (${plural(skipped, "guardrail was", "guardrails were")} not checked)`;
};

/** One sentence that tells a reader, in seconds, whether to spend any more time here. */
export function headline(g: Guardrail): string {
  switch (g.status) {
    case "verified":
      return `Verified by the AI. It ${passed(g)} on the first check.`;
    case "self-corrected":
      return `The AI caught its own problems ${plural(g.corrections, "time", "times")}, fixed them, and then ${passed(g)}.`;
    case "fixing":
      return "The AI is still correcting this document. The next run finishes the check.";
    case "needs-human":
      return `The AI could not clear this after ${plural(g.rounds, "round", "rounds")}. The reasons are below.`;
  }
}

/** "3 rounds, 2 automatic fixes" */
export function roundsLine(g: Guardrail): string {
  const fixes = g.status === "needs-human" ? 0 : g.corrections;
  const parts = [plural(g.rounds, "check round", "check rounds")];
  if (fixes > 0) parts.push(plural(fixes, "automatic fix", "automatic fixes"));
  return parts.join(", ");
}

export const needsHuman = (items: Deliverable[]): Deliverable[] =>
  items.filter((d) => d.guardrail?.status === "needs-human");

/** "15 of 16 cleared with no human" for the overview. */
export function clearedLine(c: GuardrailCounts): string {
  const cleared = c.verified + c["self-corrected"];
  const total = cleared + c.fixing + c["needs-human"];
  return `${cleared} of ${total} cleared with no human`;
}
