import clsx from "clsx";
import {
  ChevronRight,
  FileText,
  Filter,
  type LucideIcon,
  Rss,
  Search,
  Send,
  ShieldCheck,
} from "lucide-react";
import { Fragment } from "react";

import type { Stage } from "../api/types";
import { COORDINATOR, stageAgent } from "../lib/agents";
import StatusPill from "./StatusPill";

const ICONS: Record<string, LucideIcon> = {
  feeds: Rss,
  scan: Search,
  triage: Filter,
  build: FileText,
  check: ShieldCheck,
  deliver: Send,
};

// One line a demo audience can read without knowing the pipeline.
const PLAIN: Record<string, string> = {
  feeds: "Security news and advisories collected",
  scan: "Claude reads, searches and ranks what matters",
  triage: "New items get bulletin and hunt IDs",
  build: "Documents written from each ID",
  check: "Every document checked for breakage",
  deliver: "Ready to send",
};

const StageCard = ({ stage }: { stage: Stage }) => {
  const Icon = ICONS[stage.key] ?? FileText;
  const agent = stageAgent(stage.key);
  return (
    <div className="flex h-full flex-col rounded-xl border border-line bg-surface p-3">
      <p className="flex items-center gap-1.5 text-sm text-muted">
        <Icon aria-hidden="true" size={16} />
        {stage.label}
      </p>
      {agent && (
        <p
          className={clsx(
            "mt-1 text-xs font-medium",
            agent === COORDINATOR ? "text-muted" : "text-accent",
          )}
        >
          The {agent}
        </p>
      )}
      <p className="mt-1 text-xs text-faint">{PLAIN[stage.key]}</p>
      <p className="mt-2 font-medium">{stage.value}</p>
      <div className="mt-auto pt-2">
        <StatusPill status={stage.status} />
        <p className="mt-1 text-xs text-muted" title={stage.note}>
          {stage.note}
        </p>
      </div>
    </div>
  );
};

interface PipelineFlowProps {
  stages: Stage[];
  /** One row of six at wide screens. Off where the flow sits in a narrower pane. */
  row?: boolean;
}

const PipelineFlow = ({ stages, row = true }: PipelineFlowProps) => {
  if (stages.length === 0) {
    return <p className="text-sm text-muted">No scan run found in the cost logs yet.</p>;
  }
  return (
    <ol
      className={clsx("grid grid-cols-2 gap-2 md:grid-cols-3", row && "xl:flex xl:items-stretch")}
    >
      {stages.map((stage, i) => (
        <Fragment key={stage.key}>
          <li
            className={clsx(row && "xl:flex-1")}
            aria-label={`${stage.label}: ${stage.value}, ${stage.status}`}
          >
            <StageCard stage={stage} />
          </li>
          {i < stages.length - 1 && (
            <li
              aria-hidden="true"
              className={clsx("hidden items-center text-faint", row && "xl:flex")}
            >
              <ChevronRight size={18} />
            </li>
          )}
        </Fragment>
      ))}
    </ol>
  );
};

export default PipelineFlow;
