import clsx from "clsx";
import { ArrowLeft } from "lucide-react";
import { useMemo, useState } from "react";

import { useDeliverables } from "../api/client";
import type { DeliverableStatus } from "../api/types";
import DocStatus from "../components/DocStatus";
import LoadState from "../components/LoadState";
import ReportReader from "../components/ReportReader";
import { filterDeliverables, type StatusFilter } from "../lib/filter";
import { formatDay } from "../lib/format";
import { KIND_LABELS, kindLabel } from "../lib/kinds";
import { reportHref } from "../lib/route";

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "Any status" },
  { value: "ok", label: "OK" },
  { value: "broken", label: "Broken" },
  { value: "unchecked", label: "Not checked" },
];

const fieldClass = "rounded-md border border-line bg-surface px-2 py-1.5 text-sm";

const isStatus = (value: string): value is StatusFilter =>
  STATUS_OPTIONS.some((o) => o.value === value);

const ReportsPage = ({ selected }: { selected: string | null }) => {
  const deliverables = useDeliverables();
  const [kind, setKind] = useState("bulletin");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");

  const items = deliverables.data;
  const kinds = useMemo(() => {
    const present = new Set((items ?? []).map((d) => d.kind));
    const known = Object.keys(KIND_LABELS).filter((k) => present.has(k));
    const other = [...present].filter((k) => !(k in KIND_LABELS)).sort();
    return [...known, ...other];
  }, [items]);
  const shown = useMemo(
    () => filterDeliverables(items ?? [], kind, status, query),
    [items, kind, status, query],
  );

  if (!items) {
    return <LoadState error={deliverables.error} onRetry={() => void deliverables.refetch()} />;
  }

  const showStatus = (s: DeliverableStatus) => s === "broken";

  return (
    <div className="grid gap-6 md:grid-cols-[20rem_minmax(0,1fr)]">
      {/* On a phone the list and the reader take turns; side by side from tablet width. */}
      <section aria-label="Reports" className={clsx(selected && "hidden md:block")}>
        <div className="flex flex-col gap-2">
          <label className="sr-only" htmlFor="report-search">
            Search reports
          </label>
          <input
            id="report-search"
            type="search"
            placeholder="Search by ID or title"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className={fieldClass}
          />
          <div className="flex gap-2">
            <label className="sr-only" htmlFor="report-kind">
              Kind
            </label>
            <select
              id="report-kind"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
              className={clsx(fieldClass, "min-w-0 flex-1")}
            >
              <option value="all">Every kind</option>
              {kinds.map((k) => (
                <option key={k} value={k}>
                  {kindLabel(k)}
                </option>
              ))}
            </select>
            <label className="sr-only" htmlFor="report-status">
              Status
            </label>
            <select
              id="report-status"
              value={status}
              onChange={(e) => isStatus(e.target.value) && setStatus(e.target.value)}
              className={clsx(fieldClass, "min-w-0 flex-1")}
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <p className="text-xs text-muted" aria-live="polite">
            {shown.length} of {items.length} reports
          </p>
        </div>
        <ul className="mt-2 max-h-[70vh] overflow-y-auto rounded-xl border border-line bg-surface">
          {shown.map((d) => (
            <li key={d.id} className="border-b border-line last:border-b-0">
              <a
                href={reportHref(d.id)}
                aria-current={d.id === selected ? "page" : undefined}
                className={clsx("block px-3 py-2 hover:bg-raised", d.id === selected && "bg-raised")}
              >
                <span className="flex items-center justify-between gap-2 text-xs text-muted">
                  <span>
                    {d.id} · {formatDay(d.first_seen)}
                  </span>
                  {showStatus(d.status) && <DocStatus status={d.status} />}
                </span>
                <span className="mt-0.5 block text-sm">{d.title}</span>
              </a>
            </li>
          ))}
          {shown.length === 0 && (
            <li className="px-3 py-6 text-center text-sm text-muted">
              {items.length === 0 ? "No reports under out/ yet." : "No report matches."}
            </li>
          )}
        </ul>
      </section>

      <section
        aria-label="Reader"
        className={clsx(
          "min-w-0 rounded-xl border border-line bg-surface p-4 md:p-6",
          !selected && "hidden md:block",
        )}
      >
        {selected && (
          <a
            href={reportHref(null)}
            className="mb-3 inline-flex items-center gap-1 text-sm text-muted md:hidden"
          >
            <ArrowLeft aria-hidden size={16} />
            All reports
          </a>
        )}
        <ReportReader id={selected} />
      </section>
    </div>
  );
};

export default ReportsPage;
