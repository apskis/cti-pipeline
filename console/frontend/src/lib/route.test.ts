import { describe, expect, it } from "vitest";

import { filterCves, kevPassed, todayUtc } from "./cves";
import { filterDeliverables } from "./filter";
import { parseRoute, reportHref, runHref } from "./route";
import { CVES, DELIVERABLES } from "../test/fixtures";

describe("parseRoute", () => {
  it("reads the page and the report ID from the hash", () => {
    expect(parseRoute("")).toEqual({ page: "overview" });
    expect(parseRoute("#/reports")).toEqual({ page: "reports", id: null });
    expect(parseRoute(reportHref("CTI26-137"))).toEqual({ page: "reports", id: "CTI26-137" });
    expect(parseRoute("#/nowhere")).toEqual({ page: "overview" });
    expect(parseRoute(runHref("bulletin-scan-20261110T145714"))).toEqual({
      page: "runs",
      id: "bulletin-scan-20261110T145714",
    });
    expect(parseRoute("#/cves")).toEqual({ page: "cves" });
  });
});

describe("filterDeliverables", () => {
  it("filters by kind, status and a search on ID or title", () => {
    const ids = (kind: string, status: "all" | "broken", q: string) =>
      filterDeliverables(DELIVERABLES, kind, status, q).map((d) => d.id);
    expect(ids("bulletin", "all", "")).toEqual(["CTI26-137", "CTI26-136"]);
    expect(ids("all", "broken", "")).toEqual(["CTI26-136"]);
    expect(ids("all", "all", "  turla ")).toEqual(["TH26-54"]);
  });
});

describe("filterCves", () => {
  it("sorts newest first then by CVSS, and filters", () => {
    const ids = (query: string, exploitedOnly = false, kevOnly = false) =>
      filterCves(CVES.cves, { query, exploitedOnly, kevOnly }).map((c) => c.id);
    expect(ids("")).toEqual(["CVE-2026-0001", "CVE-2026-0002", "CVE-2026-0003"]);
    expect(ids("", true)).toEqual(["CVE-2026-0001"]);
    expect(ids("", false, true)).toEqual(["CVE-2026-0001"]);
    expect(ids(" globex ")).toEqual(["CVE-2026-0003"]);
    expect(ids("cti26-137")).toEqual(["CVE-2026-0001"]);
  });
});

describe("kevPassed", () => {
  it("passes only after the due day", () => {
    expect(todayUtc(new Date("2026-11-10T23:30:00Z"))).toBe("2026-11-10");
    expect(kevPassed("2026-11-09", "2026-11-10")).toBe(true);
    expect(kevPassed("2026-11-10", "2026-11-10")).toBe(false);
  });
});
