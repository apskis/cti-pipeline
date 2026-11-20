import clsx from "clsx";
import {
  FileText,
  Filter,
  type LucideIcon,
  Rss,
  Search,
  Send,
  ShieldCheck,
  SpellCheck,
} from "lucide-react";
import { useState } from "react";

import type { Stage, StageStatus } from "../api/types";
import { COORDINATOR, stageAgent } from "../lib/agents";
import StatusPill, { STATUS_ICONS, STATUS_STYLES, STATUS_WORDS } from "./StatusPill";

const ICONS: Record<string, LucideIcon> = {
  feeds: Rss,
  scan: Search,
  triage: Filter,
  build: FileText,
  review: SpellCheck,
  check: ShieldCheck,
  deliver: Send,
};

// One line a demo audience can read without knowing the pipeline.
const PLAIN: Record<string, string> = {
  feeds: "Security news and advisories collected",
  scan: "Claude reads, searches and ranks what matters",
  triage: "New items get bulletin and hunt IDs",
  build: "Documents written from each ID",
  review: "A second read checks claims against sources",
  check: "Every document checked for breakage",
  deliver: "Ready to send",
};

// Past this a note (a list of failed feeds, say) is cut to three lines with a way to open it,
// so one noisy stage cannot stretch the whole row.
const LONG_NOTE = 90;

const StageNote = ({ note }: { note: string }) => {
  const [open, setOpen] = useState(false);
  const long = note.length > LONG_NOTE;
  return (
    <>
      <p className={clsx("mt-1 text-xs break-words text-muted", long && !open && "line-clamp-3")}>{note}</p>
      {long && (
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
          className="mt-1 text-xs text-accent underline underline-offset-2 hover:text-ink"
        >
          {open ? "Show less" : "Show all"}
        </button>
      )}
    </>
  );
};

/** The round status mark above a card, and the line that joins it to the next one. */
const StatusMark = ({ status, last }: { status: StageStatus; last: boolean }) => {
  const Icon = STATUS_ICONS[status];
  return (
    <div aria-hidden className="mb-2 flex items-center gap-2">
      <span className={clsx("inline-flex size-6 shrink-0 items-center justify-center rounded-full", STATUS_STYLES[status])}>
        <Icon size={13} strokeWidth={2.5} />
      </span>
      {!last && <span className="h-px flex-1 bg-line" />}
    </div>
  );
};

const StageCard = ({ stage, index }: { stage: Stage; index: number }) => {
  const Icon = ICONS[stage.key] ?? FileText;
  const agent = stageAgent(stage.key);
  return (
    <div
      className={clsx(
        "flex h-full flex-col rounded-xl border bg-surface p-3",
        stage.status === "warn" || stage.status === "fail" ? "border-warn-ink/40" : "border-line",
      )}
    >
      <p className="font-mono text-xs text-faint">
        {String(index + 1).padStart(2, "0")} · {stage.label}
      </p>
      {agent && (
        <p
          className={clsx(
            "mt-1 flex items-center gap-1.5 text-xs font-medium",
            agent === COORDINATOR ? "text-muted" : "text-accent",
          )}
        >
          <Icon aria-hidden size={13} />
          The {agent}
        </p>
      )}
      {PLAIN[stage.key] && <p className="mt-1 text-xs text-faint">{PLAIN[stage.key]}</p>}
      <p className="mt-2 font-medium">{stage.value}</p>
      <div className="mt-auto pt-3">
        <StatusPill status={stage.status} />
        <StageNote note={stage.note} />
      </div>
    </div>
  );
};

const ORDER: StageStatus[] = ["ok", "warn", "fail", "unknown"];

/** "2 OK · 1 Check · 4 Unknown": the run's health before reading any card. */
export const StatusTally = ({ stages }: { stages: Stage[] }) => (
  <div className="flex flex-wrap gap-1.5">
    {ORDER.map((status) => {
      const n = stages.filter((s) => s.status === status).length;
      return n === 0 ? null : (
        <span key={status} className={clsx("rounded-md px-2 py-0.5 text-xs font-medium", STATUS_STYLES[status])}>
          {n} {STATUS_WORDS[status]}
        </span>
      );
    })}
  </div>
);

interface PipelineFlowProps {
  stages: Stage[];
  /** One row across at wide screens. Off where the flow sits in a narrower pane. */
  row?: boolean;
}

const PipelineFlow = ({ stages, row = true }: PipelineFlowProps) => {
  if (stages.length === 0) {
    return <p className="text-sm text-muted">No scan run found in the cost logs yet.</p>;
  }
  return (
    <ol className={clsx("grid grid-cols-2 gap-3 md:grid-cols-3", row && "xl:flex xl:items-stretch")}>
      {stages.map((stage, i) => (
        <li
          key={stage.key}
          className={clsx("flex flex-col", row && "xl:min-w-0 xl:flex-1")}
          aria-label={`${stage.label}: ${stage.value}, ${stage.status}`}
        >
          <StatusMark status={stage.status} last={i === stages.length - 1} />
          <div className="flex-1">
            <StageCard stage={stage} index={i} />
          </div>
        </li>
      ))}
    </ol>
  );
};

export default PipelineFlow;
