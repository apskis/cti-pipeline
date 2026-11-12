import clsx from "clsx";
import { ArrowLeft } from "lucide-react";

import { useRuns } from "../api/client";
import LoadState from "../components/LoadState";
import RunDetail from "../components/RunDetail";
import StatusPill from "../components/StatusPill";
import { joinAgents, runAgents } from "../lib/agents";
import { componentLabel } from "../lib/components";
import { formatMoney, formatWhen } from "../lib/format";
import { runHref } from "../lib/route";

const RunsPage = ({ selected }: { selected: string | null }) => {
  const runs = useRuns();
  if (!runs.data) {
    return <LoadState error={runs.error} onRetry={() => void runs.refetch()} />;
  }

  return (
    <div className="grid gap-6 md:grid-cols-[20rem_minmax(0,1fr)]">
      {/* On a phone the list and the detail take turns; side by side from tablet width. */}
      <section aria-label="Runs" className={clsx(selected && "hidden md:block")}>
        <p className="text-xs text-muted">{runs.data.length} runs, newest first</p>
        <ul className="mt-2 max-h-[70vh] overflow-y-auto rounded-xl border border-line bg-surface">
          {runs.data.map((r) => (
            <li key={r.id} className="border-b border-line last:border-b-0">
              <a
                href={runHref(r.id)}
                aria-current={r.id === selected ? "page" : undefined}
                className={clsx(
                  "block px-3 py-2 hover:bg-raised",
                  r.id === selected && "bg-raised",
                )}
              >
                <span className="flex items-center justify-between gap-2 text-xs text-muted">
                  <span>{formatWhen(r.started)}</span>
                  {!r.ok && <StatusPill status="fail" label="Failed" />}
                </span>
                <span className="mt-0.5 flex justify-between gap-2 text-sm">
                  <span>
                    {componentLabel(r.component)}
                    {r.kind !== "scan" && <span className="text-muted"> · rebuild</span>}
                  </span>
                  <span className="text-muted">{formatMoney(r.cost_usd)}</span>
                </span>
                <span className="mt-0.5 block text-xs text-faint first-letter:uppercase">
                  {joinAgents(runAgents(r.component, r.sessions.map((s) => s.label)))}
                </span>
              </a>
            </li>
          ))}
          {runs.data.length === 0 && (
            <li className="px-3 py-6 text-center text-sm text-muted">
              No runs in the cost logs yet.
            </li>
          )}
        </ul>
      </section>

      <section
        aria-label="Run detail"
        className={clsx(
          "min-w-0 rounded-xl border border-line bg-surface p-4 md:p-6",
          !selected && "hidden md:block",
        )}
      >
        {selected && (
          <a
            href={runHref(null)}
            className="mb-3 inline-flex items-center gap-1 text-sm text-muted md:hidden"
          >
            <ArrowLeft aria-hidden size={16} />
            All runs
          </a>
        )}
        <RunDetail id={selected} />
      </section>
    </div>
  );
};

export default RunsPage;
