import { useRuns, useSummary } from "../api/client";
import LoadState from "../components/LoadState";
import PipelineFlow from "../components/PipelineFlow";
import RunHistoryChart from "../components/RunHistoryChart";
import StatTile from "../components/StatTile";
import { formatCount, formatDay, formatMoney } from "../lib/format";

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="mt-8">
    <h2 className="mb-3 text-sm font-medium text-muted">{title}</h2>
    {children}
  </section>
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
