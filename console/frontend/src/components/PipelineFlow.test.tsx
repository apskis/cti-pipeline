import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SUMMARY } from "../test/fixtures";
import PipelineFlow from "./PipelineFlow";

describe("PipelineFlow", () => {
  it("shows every stage in order with its value and a status word", () => {
    render(<PipelineFlow stages={SUMMARY.stages} />);
    const items = screen.getAllByRole("listitem").filter((li) => li.getAttribute("aria-label"));
    expect(items.map((li) => li.getAttribute("aria-label")?.split(":")[0])).toEqual([
      "Feeds",
      "Scan",
      "Triage",
      "Build",
      "Check",
      "Deliver",
    ]);
    const scan = items[1] as HTMLElement;
    expect(within(scan).getByText("19 min, 0 searches")).toBeInTheDocument();
    expect(within(scan).getByText("Check")).toBeInTheDocument();
    expect(within(items[5] as HTMLElement).getByText("Unknown")).toBeInTheDocument();
  });

  it("says so when there is no scan run", () => {
    render(<PipelineFlow stages={[]} />);
    expect(screen.getByText(/No scan run found/)).toBeInTheDocument();
  });
});
