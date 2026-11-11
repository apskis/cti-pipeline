import { useDeliverables, useRuns, useSummary } from "../api/client";
import type { Summary } from "../api/types";
import LoadState from "../components/LoadState";
import PipelineFlow from "../components/PipelineFlow";
import RunHistoryChart from "../components/RunHistoryChart";
import StatTile from "../components/StatTile";
import { pickFeatured } from "../lib/featured";
import { formatCount, formatDay, formatMoney } from "../lib/format";
import { reportHref } from "../lib/route";

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="mt-8">
    <h2 className="mb-3 text-sm font-medium text-muted">{title}</h2>
    {children}
  </section>
);

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
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {featured.map(({ label, blurb, item }) => (
        <li key={item.id}>
          <a
            href={reportHref(item.id)}
            className="flex h-full flex-col rounded-lg border border-line bg-surface p-4 hover:bg-raised"
          >
            <span className="text-xs text-muted">{label}</span>
            <span className="mt-1 text-sm font-medium">{item.title}</span>
            <span className="mt-1 text-xs text-muted">{blurb}</span>
            <span className="mt-auto pt-3 text-xs text-faint">
              {item.id} · {formatDay(item.first_seen)}
            </span>
          </a>
        </li>
      ))}
    </ul>
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
  const bulletins = s.counts.bulletin ?? 0;
  const hunts = s.counts.hunt ?? 0;

  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Bulletins" value={formatCount(bulletins)} />
        <StatTile label="Hunt packages" value={formatCount(hunts)} />
        <StatTile label="CVEs tracked" value={formatCount(s.cves_tracked)} />
        <StatTile
          label="Model cost"
          value={formatMoney(s.total_cost_usd)}
          detail={`${s.run_days} run days, at API prices, covered by the plan`}
        />
      </div>

      <Section title="Start here">
        <StartHere />
      </Section>

      <Section
        title={s.last_scan ? `How the last scan ran, ${formatDay(s.last_scan.started)}` : "How a run works"}
      >
        <PipelineFlow stages={s.stages} />
      </Section>

      <Section title="Run history: model cost per day">
        {runs.data ? (
          <RunHistoryChart runs={runs.data} />
        ) : (
          <p className="text-sm text-muted">{runs.error ? runs.error.message : "Loading runs."}</p>
        )}
      </Section>
    </>
  );
};

export default OverviewPage;
