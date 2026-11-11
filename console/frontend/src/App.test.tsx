import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { CVES, DELIVERABLES, DOCUMENT, RUN_DETAIL, RUNS, SUMMARY } from "./test/fixtures";

// jsdom has no canvas; the chart's own drawing is Chart.js's business, not ours.
vi.mock("react-chartjs-2", () => ({ Bar: () => <div data-testid="chart" /> }));

const answer = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }));

function mockApi(handler: (url: string) => Promise<Response>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input) => handler(String(input)));
}

describe("App", () => {
  it("shows the headline numbers, the stages and the chart", async () => {
    mockApi((url) => answer(url.startsWith("/api/summary") ? SUMMARY : RUNS));
    render(<App />);
    expect(await screen.findByText("151")).toBeInTheDocument();
    expect(screen.getByText("54")).toBeInTheDocument();
    expect(screen.getByText("67")).toBeInTheDocument();
    expect(screen.getByText("$49.07")).toBeInTheDocument();
    expect(screen.getByText(/How the last scan ran, 10 Nov 2026/)).toBeInTheDocument();
    expect(await screen.findByTestId("chart")).toBeInTheDocument();
  });

  it("explains how to start the backend when it does not answer, and retries", async () => {
    const fetchMock = mockApi(() => answer({ detail: "down" }, 503));
    render(<App />);
    expect(await screen.findByRole("alert", {}, { timeout: 4000 })).toHaveTextContent(
      "The console backend did not answer.",
    );
    fetchMock.mockImplementation((input) =>
      answer(String(input).startsWith("/api/summary") ? SUMMARY : RUNS),
    );
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("151")).toBeInTheDocument();
  });

  it("opens a report from the list and renders it without its script", async () => {
    window.location.hash = "#/reports";
    mockApi((url) =>
      answer(url.startsWith("/api/deliverables/CTI26-137/html") ? DOCUMENT : DELIVERABLES),
    );
    render(<App />);
    await userEvent.click(await screen.findByRole("link", { name: /IBM Aspera Faspex RCE/ }));
    expect(await screen.findByRole("heading", { name: "Why This Matters" })).toBeInTheDocument();
    expect(screen.getByText("Patch now.")).toBeInTheDocument();
    expect(document.querySelector(".report script")).toBeNull();
    expect(screen.getByRole("link", { name: /Download .docx/ })).toHaveAttribute(
      "href",
      "/api/deliverables/CTI26-137/file",
    );
    const broken = screen.getByRole("link", { name: /Broken Example/ });
    expect(within(broken).getByText("Broken")).toBeInTheDocument();
    window.location.hash = "";
  });

  it("opens a run with its stages, documents and sanitized report", async () => {
    window.location.hash = "#/runs";
    mockApi((url) => answer(url.startsWith("/api/runs/bulletin-scan-1") ? RUN_DETAIL : RUNS));
    render(<App />);
    expect(await screen.findAllByText("Reporting")).not.toHaveLength(0);
    const links = await screen.findAllByRole("link", { name: /Bulletin scan/ });
    await userEvent.click(links[0] as HTMLElement);
    expect(await screen.findByRole("heading", { name: "CTI Daily Scan" })).toBeInTheDocument();
    expect(screen.getByText("Run report, scan-2026-11-10.md")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "CTI26-137" })).toHaveAttribute(
      "href",
      "#/reports/CTI26-137",
    );
    expect(screen.getByLabelText(/Feeds: 189 items/)).toBeInTheDocument();
    // a remote image in a report must not load
    expect(document.querySelector(".report img")?.getAttribute("src")).toBeNull();
    window.location.hash = "";
  });

  it("lists CVEs and narrows to the exploited ones", async () => {
    window.location.hash = "#/cves";
    mockApi(() => answer(CVES));
    render(<App />);
    expect(await screen.findByText("3 of 3 CVEs, newest first")).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText("Exploited only"));
    expect(screen.getByText("1 of 3 CVEs, newest first")).toBeInTheDocument();
    const row = screen.getByText("CVE-2026-0001").closest("tr") as HTMLElement;
    expect(within(row).getByText("Exploited")).toBeInTheDocument();
    expect(within(row).getByRole("link", { name: "TH26-54" })).toHaveAttribute(
      "href",
      "#/reports/TH26-54",
    );
    window.location.hash = "";
  });
});
