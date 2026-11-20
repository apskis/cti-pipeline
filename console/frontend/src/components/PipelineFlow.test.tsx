import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { SUMMARY } from "../test/fixtures";
import PipelineFlow, { StatusTally } from "./PipelineFlow";

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

  it("cuts a long note to a few lines and opens it on request", async () => {
    const note = `Failed: ${Array.from({ length: 10 }, (_, i) => `Feed ${i} (URLError: )`).join(", ")}`;
    const stages = [{ key: "feeds", label: "Feeds", value: "0 items", status: "warn" as const, note }];
    render(<PipelineFlow stages={stages} />);
    expect(screen.getByText(note)).toHaveClass("line-clamp-3");
    await userEvent.click(screen.getByRole("button", { name: "Show all" }));
    expect(screen.getByText(note)).not.toHaveClass("line-clamp-3");
    expect(screen.getByRole("button", { name: "Show less" })).toHaveAttribute("aria-expanded", "true");
  });

  it("leaves a short note whole, with no button", () => {
    render(<PipelineFlow stages={SUMMARY.stages} />);
    expect(screen.queryByRole("button", { name: "Show all" })).toBeNull();
  });

  it("tallies the stages by status, leaving out statuses with none", () => {
    const stages = [
      { key: "feeds", label: "Feeds", value: "1", status: "ok" as const, note: "" },
      { key: "scan", label: "Scan", value: "1", status: "ok" as const, note: "" },
      { key: "build", label: "Build", value: "1", status: "unknown" as const, note: "" },
    ];
    render(<StatusTally stages={stages} />);
    expect(screen.getByText("2 OK")).toBeInTheDocument();
    expect(screen.getByText("1 Unknown")).toBeInTheDocument();
    expect(screen.queryByText(/Check/)).toBeNull();
  });

  it("says so when there is no scan run", () => {
    render(<PipelineFlow stages={[]} />);
    expect(screen.getByText(/No scan run found/)).toBeInTheDocument();
  });
});
