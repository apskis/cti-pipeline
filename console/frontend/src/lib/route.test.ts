import { describe, expect, it } from "vitest";

import { filterDeliverables } from "./filter";
import { parseRoute, reportHref } from "./route";
import { DELIVERABLES } from "../test/fixtures";

describe("parseRoute", () => {
  it("reads the page and the report ID from the hash", () => {
    expect(parseRoute("")).toEqual({ page: "overview" });
    expect(parseRoute("#/reports")).toEqual({ page: "reports", id: null });
    expect(parseRoute(reportHref("CTI26-137"))).toEqual({ page: "reports", id: "CTI26-137" });
    expect(parseRoute("#/nowhere")).toEqual({ page: "overview" });
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
