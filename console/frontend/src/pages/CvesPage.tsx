import clsx from "clsx";
import { useMemo, useState } from "react";

import { useCves } from "../api/client";
import type { Cve } from "../api/types";
import LoadState from "../components/LoadState";
import StatusPill from "../components/StatusPill";
import { filterCves, kevPassed, todayUtc } from "../lib/cves";
import { formatDay } from "../lib/format";
import { reportHref } from "../lib/route";

const Ref = ({ id }: { id: string | null }) =>
  id ? (
    <a
      href={reportHref(id)}
      className="whitespace-nowrap underline decoration-line underline-offset-2"
    >
      {id}
    </a>
  ) : (
    <span className="text-faint">None</span>
  );

const Row = ({ cve, today }: { cve: Cve; today: string }) => (
  <tr className="border-t border-line align-top">
    <td className="whitespace-nowrap px-3 py-2 font-medium">{cve.id}</td>
    <td className="px-3 py-2">
      <span className="block">{cve.vendor}</span>
      <span className="block text-xs text-muted">{cve.product}</span>
    </td>
    <td className="px-3 py-2 text-muted">{cve.vuln_type}</td>
    <td className="whitespace-nowrap px-3 py-2">
      {cve.cvss_score ?? <span className="text-faint">n/a</span>}
    </td>
    <td className="px-3 py-2" title={cve.exploitation}>
      {/* The register's own wording sits in the tooltip; the pill gives the yes or no. */}
      <StatusPill
        status={cve.exploited ? "fail" : "unknown"}
        label={cve.exploited ? "Exploited" : "Not seen"}
      />
      {cve.kev_due && (
        <span
          className={clsx(
            "mt-1 block whitespace-nowrap text-xs",
            kevPassed(cve.kev_due, today) ? "font-medium text-fail-ink" : "text-muted",
          )}
        >
          KEV due {formatDay(cve.kev_due)}
          {kevPassed(cve.kev_due, today) && ", passed"}
        </span>
      )}
    </td>
    <td className="px-3 py-2">
      <Ref id={cve.bulletin_id} />
    </td>
    <td className="px-3 py-2">
      <Ref id={cve.hunt_id} />
    </td>
    <td className="whitespace-nowrap px-3 py-2 text-muted">
      {cve.date_added ? formatDay(cve.date_added) : "Unknown"}
    </td>
  </tr>
);

const CvesPage = () => {
  const register = useCves();
  const [query, setQuery] = useState("");
  const [exploitedOnly, setExploitedOnly] = useState(false);
  const [kevOnly, setKevOnly] = useState(false);
  const all = register.data?.cves;
  const today = todayUtc();
  const shown = useMemo(
    () => filterCves(all ?? [], { query, exploitedOnly, kevOnly }),
    [all, query, exploitedOnly, kevOnly],
  );

  if (!register.data || !all) {
    return <LoadState error={register.error} onRetry={() => void register.refetch()} />;
  }
  if (register.data.register === null) {
    return <p className="py-16 text-center text-muted">No CVE register under out/ yet.</p>;
  }

  return (
    <section aria-labelledby="cves-title">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="cves-title" className="font-medium">
            CVE register
          </h2>
          <p className="text-xs text-muted">From {register.data.register}, read only</p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <label className="sr-only" htmlFor="cve-search">
            Search CVEs
          </label>
          <input
            id="cve-search"
            type="search"
            placeholder="CVE, vendor, product or ID"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-56 rounded-md border border-line bg-surface px-2 py-1.5 text-sm"
          />
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={exploitedOnly}
              onChange={(e) => setExploitedOnly(e.target.checked)}
            />
            Exploited only
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={kevOnly}
              onChange={(e) => setKevOnly(e.target.checked)}
            />
            On CISA KEV
          </label>
        </div>
      </div>
      <p className="mb-2 text-xs text-muted" aria-live="polite">
        {shown.length} of {all.length} CVEs, newest first
      </p>
      {/* Wide on purpose: the table scrolls inside its box, never the page. */}
      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full min-w-[56rem] text-sm">
          <thead className="bg-raised text-left text-xs text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">CVE</th>
              <th className="px-3 py-2 font-medium">Vendor and product</th>
              <th className="px-3 py-2 font-medium">Type</th>
              <th className="px-3 py-2 font-medium">CVSS</th>
              <th className="px-3 py-2 font-medium">Exploitation</th>
              <th className="px-3 py-2 font-medium">Bulletin</th>
              <th className="px-3 py-2 font-medium">Hunt</th>
              <th className="px-3 py-2 font-medium">Added</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((c) => (
              <Row key={c.id} cve={c} today={today} />
            ))}
            {shown.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-muted">
                  No CVE matches.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default CvesPage;
