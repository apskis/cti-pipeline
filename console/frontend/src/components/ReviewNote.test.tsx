import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Review } from "../api/types";
import { DELIVERABLES } from "../test/fixtures";
import { filterDeliverables } from "../lib/filter";
import ReviewNote, { unquote } from "./ReviewNote";

const FLAG: Review = {
  verdict: "flag",
  summary: "One date differs from its source.",
  checked_at: "2026-11-12T14:05:00Z",
  findings: [
    { claim: "Exploited since 3 Nov", problem: "The source says 5 Nov.", source: "https://example.com/a" },
    { claim: "", problem: "No TLP marking.", source: "javascript:alert(1)" },
  ],
  stale: false,
};

describe("ReviewNote", () => {
  it("lists each finding and links only web sources", () => {
    render(<ReviewNote kind="bulletin" review={FLAG} />);
    expect(screen.getByText("Flagged by the Reviewer")).toBeInTheDocument();
    expect(screen.getByText("The source says 5 Nov.")).toBeInTheDocument();
    expect(screen.getAllByRole("link").map((a) => a.getAttribute("href"))).toEqual([
      "https://example.com/a",
    ]);
    expect(screen.getByText("javascript:alert(1)").tagName).toBe("SPAN");
  });

  it("says when a document has not been reviewed, only for reviewed kinds", () => {
    const { rerender } = render(<ReviewNote kind="hunt" review={null} />);
    expect(screen.getByText(/Not checked by the Reviewer yet/)).toBeInTheDocument();
    rerender(<ReviewNote kind="cve_brief" review={null} />);
    expect(screen.queryByText(/Reviewer/)).not.toBeInTheDocument();
  });

  it("warns when the document changed after its review", () => {
    render(<ReviewNote kind="bulletin" review={{ ...FLAG, verdict: "pass", findings: [], stale: true }} />);
    expect(screen.getByText(/Checked by the Reviewer/)).toBeInTheDocument();
    expect(screen.getByText(/changed after this review/)).toBeInTheDocument();
  });

  it("filters the reports list to flagged documents", () => {
    const items = DELIVERABLES.map((d, i) => (i === 0 ? { ...d, review: FLAG } : d));
    expect(filterDeliverables(items, "all", "flagged", "").map((d) => d.id)).toEqual(["CTI26-137"]);
  });

  it("does not double the quotes the Reviewer already put around a claim", () => {
    expect(unquote('"Derived from the scan of 12 Sep"')).toBe("Derived from the scan of 12 Sep");
    expect(unquote("“Chain three”")).toBe("Chain three");
    expect(unquote("plain claim")).toBe("plain claim");
  });
});
