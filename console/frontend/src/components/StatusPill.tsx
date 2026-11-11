import clsx from "clsx";

import type { StageStatus } from "../api/types";

const STYLES: Record<StageStatus, string> = {
  ok: "bg-ok-bg text-ok-ink",
  warn: "bg-warn-bg text-warn-ink",
  fail: "bg-fail-bg text-fail-ink",
  unknown: "bg-unknown-bg text-unknown-ink",
};

// Words, not just colour, so the status reads without colour vision and on a projector.
const WORDS: Record<StageStatus, string> = {
  ok: "OK",
  warn: "Check",
  fail: "Problem",
  unknown: "Unknown",
};

interface StatusPillProps {
  status: StageStatus;
  label?: string;
}

const StatusPill = ({ status, label }: StatusPillProps) => (
  <span className={clsx("inline-block rounded-md px-2 py-0.5 text-xs font-medium", STYLES[status])}>
    {label ?? WORDS[status]}
  </span>
);

export default StatusPill;
