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

const overview = (url: string) =>
  answer(
    url.startsWith("/api/summary") ? SUMMARY : url.startsWith("/api/deliverables") ? DELIVERABLES : RUNS,
  );

describe("App", () => {
  it("shows the headline numbers, the stages and the chart", async () => {
    mockApi(overview);
    render(<App />);
    expect(await screen.findByText("151")).toBeInTheDocument();
    expect(screen.getByText("54")).toBeInTheDocument();
    expect(screen.getByText("67")).toBeInTheDocument();
    expect(screen.getByText("$49.07")).toBeInTheDocument();
    expect(screen.getByText(/How the last scan ran, 10 Nov 2026/)).toBeInTheDocument();
    expect(await screen.findByTestId("chart")).toBeInTheDocument();
  });

  it("asks for the summary, runs and reports together, not one after another", () => {
    // The summary never answers, so a request made only after it arrives would not appear.
    const fetchMock = mockApi((url) =>
      url.startsWith("/api/summary") ? new Promise<Response>(() => {}) : overview(url),
    );
    render(<App />);
    const asked = fetchMock.mock.calls.map(([input]) => String(input).split("?")[0]);
    expect(asked).toEqual(
      expect.arrayContaining(["/api/summary", "/api/runs", "/api/deliverables"]),
    );
  });

  it("features the newest working report of each kind", async () => {
    mockApi(overview);
    render(<App />);
    const bulletin = await screen.findByRole("link", { name: /Latest bulletin/ });
    expect(bulletin).toHaveAttribute("href", "#/reports/CTI26-137");
    expect(screen.getByRole("link", { name: /Latest hunt package/ })).toHaveAttribute(
      "href",
      "#/reports/TH26-54",
    );
    expect(screen.queryByRole("link", { name: /Broken Example/ })).toBeNull();
  });

  it("says how to make output when there is none", async () => {
    const empty = { ...SUMMARY, counts: {}, cves_tracked: null, run_days: 0, last_scan: null };
    mockApi((url) => answer(url.startsWith("/api/summary") ? empty : []));
    render(<App />);
    expect(await screen.findByText("No pipeline output yet.")).toBeInTheDocument();
  });

  it("explains how to start the backend when it does not answer, and retries", async () => {
    const fetchMock = mockApi(() => answer({ detail: "down" }, 503));
    render(<App />);
    expect(await screen.findByRole("alert", {}, { timeout: 4000 })).toHaveTextContent(
      "The console backend did not answer.",
    );
    fetchMock.mockImplementation((input) => overview(String(input)));
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

  it("shows the branded PDF first when Word can make it, with both downloads", async () => {
    window.location.hash = "#/reports/CTI26-137";
    mockApi((url) =>
      url.startsWith("/api/deliverables/CTI26-137/html")
        ? answer({ ...DOCUMENT, pdf: true })
        : url.startsWith("/api/deliverables/CTI26-137/pdf/ready")
          ? answer({ id: "CTI26-137", bytes: 1200 })
          : answer(DELIVERABLES),
    );
    render(<App />);
    const frame = await screen.findByTitle("CTI26-137, branded PDF");
    expect(frame).toHaveAttribute("src", "/api/deliverables/CTI26-137/pdf#view=FitH");
    expect(screen.getByRole("link", { name: /Download .pdf/ })).toHaveAttribute(
      "href",
      "/api/deliverables/CTI26-137/pdf?download=true",
    );
    expect(screen.getByRole("button", { name: "Branded" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: "Text" }));
    expect(await screen.findByText("Patch now.")).toBeInTheDocument();
    expect(screen.queryByTitle("CTI26-137, branded PDF")).toBeNull();
  });

  it("offers the text view when the PDF cannot be made", async () => {
    window.location.hash = "#/reports/CTI26-137";
    mockApi((url) =>
      url.startsWith("/api/deliverables/CTI26-137/html")
        ? answer({ ...DOCUMENT, pdf: true })
        : url.startsWith("/api/deliverables/CTI26-137/pdf/ready")
          ? answer({ detail: "Word could not convert the report" }, 502)
          : answer(DELIVERABLES),
    );
    render(<App />);
    expect(await screen.findByText(/Could not make the branded PDF/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Show the text view" }));
    expect(await screen.findByText("Patch now.")).toBeInTheDocument();
  });

  it("offers the text view while Word is still making the PDF", async () => {
    window.location.hash = "#/reports/CTI26-137";
    mockApi((url) =>
      url.startsWith("/api/deliverables/CTI26-137/html")
        ? answer({ ...DOCUMENT, pdf: true })
        : url.startsWith("/api/deliverables/CTI26-137/pdf/ready")
          ? new Promise<Response>(() => {}) // a cold Word, still exporting
          : answer(DELIVERABLES),
    );
    render(<App />);
    expect(await screen.findByText("Making the branded PDF with Word.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Read the text instead" }));
    expect(await screen.findByText("Patch now.")).toBeInTheDocument();
  });

  it("shows only the text view and no PDF download without Word", async () => {
    window.location.hash = "#/reports/CTI26-137";
    mockApi((url) =>
      answer(url.startsWith("/api/deliverables/CTI26-137/html") ? DOCUMENT : DELIVERABLES),
    );
    render(<App />);
    expect(await screen.findByText("Patch now.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Branded" })).toBeNull();
    expect(screen.queryByRole("link", { name: /Download .pdf/ })).toBeNull();
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

  it("shows the agents, the run flow and both clouds on the How it's built tab", async () => {
    mockApi(overview);
    window.location.hash = "#/built";
    render(<App />);
    expect(screen.getByRole("link", { name: "How it's built" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Bulletin scan")).toBeInTheDocument();
    expect(screen.getByText("How the agents work together")).toBeInTheDocument();
    expect(screen.getByText("Writers in parallel")).toBeInTheDocument();
    expect(screen.getAllByText("The Analyst").length).toBe(2);
    expect(screen.getAllByText("Haiku 4.5").length).toBeGreaterThan(0);
    expect(screen.getByText("Prefetch feeds")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "AWS" })).toBeInTheDocument();
    expect(await screen.findByText("Documents produced")).toBeInTheDocument();
    window.location.hash = "";
  });
});
