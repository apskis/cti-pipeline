import clsx from "clsx";
import { AlertTriangle, Check, CircleHelp, type LucideIcon, X } from "lucide-react";

import type { StageStatus } from "../api/types";

export const STATUS_STYLES: Record<StageStatus, string> = {
  ok: "bg-ok-bg text-ok-ink",
  warn: "bg-warn-bg text-warn-ink",
  fail: "bg-fail-bg text-fail-ink",
  unknown: "bg-unknown-bg text-unknown-ink",
};

// Words, not just colour, so the status reads without colour vision and on a projector.
export const STATUS_WORDS: Record<StageStatus, string> = {
  ok: "OK",
  warn: "Check",
  fail: "Problem",
  unknown: "Unknown",
};

// A shape per status as well, for the same reason: a glance tells them apart in grey.
export const STATUS_ICONS: Record<StageStatus, LucideIcon> = {
  ok: Check,
  warn: AlertTriangle,
  fail: X,
  unknown: CircleHelp,
};

interface StatusPillProps {
  status: StageStatus;
  label?: string;
}

const StatusPill = ({ status, label }: StatusPillProps) => {
  const Icon = STATUS_ICONS[status];
  return (
    <span
      className={clsx("inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium", STATUS_STYLES[status])}
    >
      <Icon aria-hidden size={12} strokeWidth={2.5} />
      {label ?? STATUS_WORDS[status]}
    </span>
  );
};

export default StatusPill;
