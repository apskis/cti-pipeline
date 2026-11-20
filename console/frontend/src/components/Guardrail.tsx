import clsx from "clsx";
import { CircleCheck, CircleDashed, CircleX, LoaderCircle, ShieldAlert, ShieldCheck } from "lucide-react";

import type { GateResult, Guardrail } from "../api/types";
import { CHECKED_KINDS, GATES, STATUS_VIEW, headline, roundsLine } from "../lib/guardrails";
import StatusPill from "./StatusPill";

/** The pill on a Reports list row: Verified, Fixed itself, Checking or Needs you. */
export const GuardrailBadge = ({ guardrail }: { guardrail: Guardrail | null }) => {
  if (!guardrail) return null;
  const view = STATUS_VIEW[guardrail.status];
  return <StatusPill status={view.pill} label={view.label} />;
};

const GATE_ICON: Record<GateResult, typeof CircleCheck> = {
  pass: CircleCheck,
  flag: CircleX,
  unchecked: CircleDashed,
};

const GATE_WORD: Record<GateResult, string> = { pass: "passed", flag: "failed", unchecked: "not checked" };

const Gate = ({ label, result }: { label: string; result: GateResult }) => {
  const Icon = GATE_ICON[result];
  return (
    <li className="flex items-center gap-1.5">
      <Icon
        aria-hidden
        size={14}
        className={clsx(
          result === "pass" && "text-ok-ink",
          result === "flag" && "text-warn-ink",
          result === "unchecked" && "text-muted",
        )}
      />
      <span>{label}</span>
      <span className="sr-only">: {GATE_WORD[result]}</span>
    </li>
  );
};

/**
 * The self check outcome at the top of the reader: one headline, the gates, and only when
 * the AI could not clear it, the reasons. Built so a human can decide in seconds.
 */
const GuardrailPanel = ({ kind, guardrail }: { kind: string; guardrail: Guardrail | null }) => {
  if (!CHECKED_KINDS.has(kind)) return null;
  if (!guardrail) {
    return (
      <p className="mb-4 text-xs text-muted">Not through the AI self check yet. The next run checks it.</p>
    );
  }
  const needsYou = guardrail.status === "needs-human";
  const Icon = needsYou ? ShieldAlert : guardrail.status === "fixing" ? LoaderCircle : ShieldCheck;
  return (
    <section
      aria-label="AI self check"
      className={clsx(
        "mb-4 rounded-xl border p-4 text-sm",
        needsYou ? "border-warn-ink/30 bg-warn-bg text-warn-ink" : "border-ok-ink/30 bg-ok-bg/40",
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 font-medium">
          <Icon aria-hidden size={18} className={needsYou ? undefined : "text-ok-ink"} />
          {headline(guardrail)}
        </p>
        <span className="flex items-center gap-2 text-xs opacity-80">
          {roundsLine(guardrail)}
          <GuardrailBadge guardrail={guardrail} />
        </span>
      </div>
      {needsYou && guardrail.open_issues.length > 0 && (
        <ol className="mt-3 list-decimal space-y-1 pl-5">
          {guardrail.open_issues.map((issue, i) => (
            <li key={i}>{issue}</li>
          ))}
        </ol>
      )}
      <ul aria-label="Guardrails" className="mt-3 grid gap-1 text-xs sm:grid-cols-2">
        {GATES.map((g) => (
          <Gate key={g.key} label={g.label} result={guardrail.gates[g.key] ?? "unchecked"} />
        ))}
      </ul>
      {guardrail.lint_warnings > 0 && (
        <p className="mt-2 text-xs opacity-80">
          {guardrail.lint_warnings} wording {guardrail.lint_warnings === 1 ? "note" : "notes"} for
          the AI to weigh, none blocking.
        </p>
      )}
      {guardrail.stale && (
        <p className="mt-1 text-xs opacity-80">
          The document changed after this check. The next run checks it again.
        </p>
      )}
    </section>
  );
};

export default GuardrailPanel;
