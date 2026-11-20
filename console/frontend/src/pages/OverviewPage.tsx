import clsx from "clsx";
import {
  ArrowRight,
  CalendarDays,
  Coins,
  Crosshair,
  FileText,
  type LucideIcon,
  Newspaper,
  ShieldAlert,
} from "lucide-react";
import { useMemo } from "react";

import { useDeliverables, useRuns, useSummary } from "../api/client";
import type { Run, Summary } from "../api/types";
import LoadState from "../components/LoadState";
import PipelineFlow, { StatusTally } from "../components/PipelineFlow";
import RunHistoryChart from "../components/RunHistoryChart";
import StatTile from "../components/StatTile";
import { pickFeatured } from "../lib/featured";
import { formatCount, formatDay, formatMoney, formatShortDay } from "../lib/format";
import { reportHref } from "../lib/route";
import { costByDay } from "../lib/runHistory";

const Card = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <section className={clsx("rounded-xl border border-line bg-surface p-4 md:p-5", className)}>{children}</section>
);

const KIND_ICONS: Record<string, LucideIcon> = {
  bulletin: Newspaper,
  hunt: Crosshair,
  cve_brief: ShieldAlert,
  weekly: CalendarDays,
};

const StartHere = () => {
  const deliverables = useDeliverables();
  if (!deliverables.data) {
    return (
      <p className="text-sm text-muted">
        {deliverables.error ? deliverables.error.message : "Finding the latest reports."}
      </p>
    );
  }
  const featured = pickFeatured(deliverables.data);
  if (featured.length === 0) {
    return <p className="text-sm text-muted">No finished reports under out/ yet.</p>;
  }
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {featured.map(({ label, blurb, item }) => {
        const Icon = KIND_ICONS[item.kind] ?? FileText;
        return (
          <li key={item.id}>
            <a
              href={reportHref(item.id)}
              className="group flex h-full flex-col rounded-xl border border-line bg-surface p-4 hover:border-accent/60 hover:bg-raised"
            >
              <span className="flex items-center gap-1.5 text-xs text-muted">
                <Icon aria-hidden size={14} className="text-accent" />
                {label}
              </span>
              <span className="mt-2 font-semibold leading-snug">{item.title}</span>
              <span className="mt-1 text-xs text-muted">{blurb}</span>
              <span className="mt-auto flex items-center justify-between gap-2 pt-4 font-mono text-xs text-faint">
                {item.id} · {formatDay(item.first_seen)}
                <ArrowRight aria-hidden size={14} className="shrink-0 group-hover:text-accent" />
              </span>
            </a>
          </li>
        );
      })}
    </ul>
  );
};

/** The chart in a card that says what it covers and what it adds up to. */
interface CostCardProps {
  runs: Run[] | undefined;
  error: Error | null;
  /** The summary's total, so the card and the Model cost tile never show two figures. */
  total: number;
}

const CostCard = ({ runs, error, total }: CostCardProps) => {
  const days = useMemo(() => (runs ? costByDay(runs) : []), [runs]);
  const first = days[0];
  const last = days[days.length - 1];
  return (
    <Card className="flex h-full flex-col">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">Run history: model cost per day</h3>
          {first && last && (
            <p className="mt-0.5 text-xs text-faint">
              {formatShortDay(first.day)} to {formatShortDay(last.day)}, split by stage
            </p>
          )}
        </div>
        {days.length > 0 && <p className="font-mono text-lg font-semibold">{formatMoney(total)}</p>}
      </div>
      {runs ? (
        <RunHistoryChart runs={runs} />
      ) : (
        <p className="text-sm text-muted">{error ? error.message : "Loading runs."}</p>
      )}
    </Card>
  );
};

const isEmpty = (s: Summary): boolean =>
  s.last_scan === null && s.run_days === 0 && Object.values(s.counts).every((n) => n === 0);

/** First run on a fresh checkout: nothing to show yet, so say how to make something. */
const NothingYet = () => (
  <div className="mx-auto max-w-lg rounded-xl border border-line bg-surface p-6">
    <p className="font-medium">No pipeline output yet.</p>
    <p className="mt-2 text-sm text-muted">
      The console reads <code>out/</code> and <code>logs/</code> and both are empty. Run a scan
      with <code>.\scripts\run-local.ps1 bulletin-scan</code>, or point the console at existing
      output with <code>CTI_CONSOLE_OUT</code> and <code>CTI_CONSOLE_LOGS</code>.
    </p>
  </div>
);

const OverviewPage = () => {
  const summary = useSummary();
  const runs = useRuns();
  // Asked for here, not only in StartHere, so it loads alongside the summary instead of
  // waiting for the summary to arrive before StartHere mounts and asks.
  useDeliverables();
  const handleRetry = () => {
    void summary.refetch();
    void runs.refetch();
  };

  if (!summary.data) {
    return <LoadState error={summary.error} onRetry={handleRetry} />;
  }
  const s = summary.data;
  if (isEmpty(s)) {
    return <NothingYet />;
  }

  return (
    <>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Bulletins" value={formatCount(s.counts.bulletin ?? 0)} Icon={Newspaper} />
        <StatTile label="Hunt packages" value={formatCount(s.counts.hunt ?? 0)} Icon={Crosshair} />
        <StatTile label="CVEs tracked" value={formatCount(s.cves_tracked)} Icon={ShieldAlert} />
        <StatTile
          label="Model cost"
          value={formatMoney(s.total_cost_usd)}
          detail={`${s.run_days} run days, at API prices, covered by the plan`}
          Icon={Coins}
          highlight
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <section>
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h3 className="font-semibold">Start here</h3>
            <p className="text-xs text-faint">Latest of each document type</p>
          </div>
          <StartHere />
        </section>
        <CostCard runs={runs.data} error={runs.error} total={s.total_cost_usd} />
      </div>

      <Card className="mt-6">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="font-semibold">
              {s.last_scan ? `How the last scan ran, ${formatDay(s.last_scan.started)}` : "How a run works"}
            </h3>
            <p className="mt-0.5 text-xs text-faint">
              {s.stages.length} stages, from feeds to delivery
            </p>
          </div>
          <StatusTally stages={s.stages} />
        </div>
        <PipelineFlow stages={s.stages} />
      </Card>
    </>
  );
};

export default OverviewPage;
