import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { RUNS, SUMMARY } from "./test/fixtures";

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
});
