import type { Cve } from "../api/types";

export interface CveFilter {
  query: string;
  exploitedOnly: boolean;
  kevOnly: boolean;
}

/** Newest first, then highest CVSS: what the VM team would read first. */
export function filterCves(cves: Cve[], { query, exploitedOnly, kevOnly }: CveFilter): Cve[] {
  const needle = query.trim().toLowerCase();
  return cves
    .filter((c) => !exploitedOnly || c.exploited)
    .filter((c) => !kevOnly || c.kev_added !== null)
    .filter(
      (c) =>
        !needle ||
        [c.id, c.vendor, c.product, c.vuln_type, c.bulletin_id ?? "", c.hunt_id ?? ""]
          .join(" ")
          .toLowerCase()
          .includes(needle),
    )
    .sort(
      (a, b) =>
        (b.date_added ?? "").localeCompare(a.date_added ?? "") ||
        (b.cvss_score ?? -1) - (a.cvss_score ?? -1),
    );
}

/** Today as "YYYY-MM-DD" in UTC, the form the register's dates take. */
export const todayUtc = (now = new Date()): string => now.toISOString().slice(0, 10);

/** A KEV due date before today has passed; on the day itself it has not. */
export const kevPassed = (due: string, today: string): boolean => due < today;
