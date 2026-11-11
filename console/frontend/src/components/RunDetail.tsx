import { useMemo } from "react";

import { useRunDetail } from "../api/client";
import type { RunDetail as RunDetailData } from "../api/types";
import { componentLabel } from "../lib/components";
import { formatDuration, formatMoney, formatWhen } from "../lib/format";
import { reportHref } from "../lib/route";
import { sanitizeReport } from "../lib/sanitize";
import PipelineFlow from "./PipelineFlow";
import StatusPill from "./StatusPill";

const Heading = ({ children }: { children: React.ReactNode }) => (
  <h3 className="mb-2 mt-6 text-sm font-medium text-muted">{children}</h3>
);

const Sessions = ({ run }: { run: RunDetailData }) => (
  <div className="overflow-x-auto rounded-lg border border-line">
    <table className="w-full text-sm">
      <thead className="bg-raised text-left text-xs text-muted">
        <tr>
          <th className="px-3 py-2 font-medium">Session</th>
          <th className="px-3 py-2 font-medium">Started</th>
          <th className="px-3 py-2 text-right font-medium">Time</th>
          <th className="px-3 py-2 text-right font-medium">Turns</th>
          <th className="px-3 py-2 text-right font-medium">Cost</th>
          <th className="px-3 py-2 font-medium">Result</th>
        </tr>
      </thead>
      <tbody>
        {run.sessions.map((s) => (
          <tr key={`${s.label}-${s.started}`} className="border-t border-line">
            <td className="px-3 py-1.5">{s.label}</td>
            <td className="whitespace-nowrap px-3 py-1.5">{formatWhen(s.started)}</td>
            <td className="px-3 py-1.5 text-right">{formatDuration(s.duration_s)}</td>
            <td className="px-3 py-1.5 text-right">{s.turns}</td>
            <td className="px-3 py-1.5 text-right">{formatMoney(s.cost_usd)}</td>
            <td className="px-3 py-1.5">
              <StatusPill status={s.ok ? "ok" : "fail"} label={s.ok ? "OK" : "Failed"} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const Written = ({ run }: { run: RunDetailData }) => {
  if (run.written.length === 0) {
    return (
      <p className="text-sm text-muted">
        No document still carries this run's save time. A later rebuild may have saved them again.
      </p>
    );
  }
  return (
    <ul className="grid gap-x-4 gap-y-1 text-sm sm:grid-cols-2">
      {run.written.map((d) => (
        <li key={d.id} className="min-w-0 truncate">
          <a href={reportHref(d.id)} className="underline decoration-line underline-offset-2">
            {d.id}
          </a>{" "}
          <span className="text-muted">{d.title}</span>
        </li>
      ))}
    </ul>
  );
};

/** One run: who ran, how long, what it cost, the stages, what it wrote and its report. */
const RunDetail = ({ id }: { id: string | null }) => {
  const detail = useRunDetail(id);
  const report = detail.data?.report;
  const html = useMemo(() => (report ? sanitizeReport(report.html) : ""), [report]);

  if (id === null) {
    return <p className="py-16 text-center text-muted">Pick a run from the list to see it here.</p>;
  }
  if (detail.error) {
    return (
      <p className="py-16 text-center text-muted" role="alert">
        Could not open that run. {detail.error.message}
      </p>
    );
  }
  if (!detail.data) {
    return (
      <p className="py-16 text-center text-muted" role="status">
        Opening the run.
      </p>
    );
  }

  const run = detail.data;
  return (
    <article aria-labelledby="run-title">
      <header className="border-b border-line pb-4">
        <p className="text-xs text-muted">
          {componentLabel(run.component)} · {run.kind === "scan" ? "Scan run" : "Rebuild only"}
          {run.mode && ` · ${run.mode}`}
        </p>
        <h2 id="run-title" className="mt-1 text-lg font-medium">
          {formatWhen(run.started)}
        </h2>
        <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <StatusPill
            status={run.ok ? "ok" : "fail"}
            label={run.ok ? "All sessions OK" : "A session failed"}
          />
          <span>{run.sessions.length} sessions</span>
          <span>{formatDuration(run.duration_s)} of model time</span>
          <span>{formatMoney(run.cost_usd)} at API prices</span>
        </p>
      </header>

      {run.stages.length > 0 && (
        <>
          <Heading>Stages</Heading>
          <PipelineFlow stages={run.stages} row={false} />
        </>
      )}

      <Heading>Sessions</Heading>
      <Sessions run={run} />

      <Heading>Documents saved during this run</Heading>
      <Written run={run} />

      <Heading>{report ? `Run report, ${report.name}` : "Run report"}</Heading>
      {report ? (
        /* Safe to inject: sanitizeReport keeps plain document markup only. */
        <div className="report" dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        <p className="text-sm text-muted">
          {run.kind === "scan"
            ? `${componentLabel(run.component)} leaves no run report the console can find.`
            : "A rebuild writes documents, not a run report."}
        </p>
      )}
    </article>
  );
};

export default RunDetail;
