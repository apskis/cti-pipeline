import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Guardrail } from "../api/types";
import { filterDeliverables } from "../lib/filter";
import { clearedLine, headline, needsHuman, roundsLine } from "../lib/guardrails";
import { DELIVERABLES } from "../test/fixtures";
import GuardrailPanel, { GuardrailBadge } from "./Guardrail";

const PASS_GATES = {
  sources: "pass",
  cve_facts: "pass",
  house_rules: "pass",
  consistency: "pass",
  reasoning: "pass",
  wording: "pass",
} as const;

const FIXED: Guardrail = {
  status: "self-corrected",
  gates: { ...PASS_GATES },
  rounds: 2,
  corrections: 1,
  open_issues: [],
  lint_warnings: 0,
  updated_at: "2026-11-19T20:30:00Z",
  stale: false,
};

const STUCK: Guardrail = {
  ...FIXED,
  status: "needs-human",
  gates: { ...PASS_GATES, sources: "flag" },
  rounds: 3,
  corrections: 2,
  open_issues: ["The only source for the victim count was taken down."],
};

describe("guardrail copy", () => {
  it("says in one sentence whether a human is needed", () => {
    expect(headline({ ...FIXED, status: "verified", rounds: 1, corrections: 0 })).toMatch(/first check/);
    expect(headline(FIXED)).toBe(
      "The AI caught its own problems 1 time, fixed them, and then passed every guardrail.",
    );
    expect(headline(STUCK)).toBe("The AI could not clear this after 3 rounds. The reasons are below.");
  });

  it("never claims every guardrail when some were not checked", () => {
    const partial = { ...FIXED, status: "verified" as const, gates: { sources: "pass" as const } };
    expect(headline(partial)).toBe(
      "Verified by the AI. It passed every check it ran (5 guardrails were not checked) on the first check.",
    );
  });

  it("counts automatic fixes only when they worked", () => {
    expect(roundsLine(FIXED)).toBe("2 check rounds, 1 automatic fix");
    expect(roundsLine(STUCK)).toBe("3 check rounds");
  });

  it("uses no hyphens or dashes in what a reader sees", () => {
    const copy = [headline(FIXED), headline(STUCK), roundsLine(FIXED), clearedLine({ verified: 1, "self-corrected": 1, fixing: 0, "needs-human": 1 })];
    expect(copy.filter((t) => /[-‐-―]/.test(t))).toEqual([]);
  });

  it("reports how much was cleared with no human", () => {
    expect(clearedLine({ verified: 12, "self-corrected": 3, fixing: 0, "needs-human": 1 })).toBe(
      "15 of 16 cleared with no human",
    );
  });
});

describe("GuardrailPanel", () => {
  it("shows the reasons and the failed gate only when the AI could not clear it", () => {
    render(<GuardrailPanel kind="bulletin" guardrail={STUCK} />);
    const panel = screen.getByRole("region", { name: "AI self check" });
    expect(within(panel).getByText(/taken down/)).toBeInTheDocument();
    expect(within(panel).getByText("Needs you")).toBeInTheDocument();
    expect(within(panel).getByText(": failed")).toBeInTheDocument();
  });

  it("lists every gate as passed for a corrected document, with no reasons", () => {
    render(<GuardrailPanel kind="hunt" guardrail={FIXED} />);
    const gates = screen.getByRole("list", { name: "Guardrails" });
    expect(within(gates).getAllByRole("listitem")).toHaveLength(6);
    expect(within(gates).getAllByText(": passed")).toHaveLength(6);
    expect(screen.getByText("Fixed itself")).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Needs you" })).not.toBeInTheDocument();
  });

  it("says when a document has not been checked, and stays out of the CVE brief", () => {
    const { rerender } = render(<GuardrailPanel kind="awareness" guardrail={null} />);
    expect(screen.getByText(/Not through the AI self check yet/)).toBeInTheDocument();
    rerender(<GuardrailPanel kind="cve_brief" guardrail={null} />);
    expect(screen.queryByText(/self check/)).not.toBeInTheDocument();
  });

  it("renders nothing as a badge without a record", () => {
    const { container } = render(<GuardrailBadge guardrail={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("Needs you filter", () => {
  it("keeps only the documents the AI could not clear", () => {
    const items = DELIVERABLES.map((d, i) => ({ ...d, guardrail: i === 2 ? STUCK : FIXED }));
    expect(filterDeliverables(items, "all", "needs-human", "").map((d) => d.id)).toEqual(["TH26-54"]);
    expect(needsHuman(items).map((d) => d.id)).toEqual(["TH26-54"]);
  });
});
