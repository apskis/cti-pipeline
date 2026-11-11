import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { THEME_KEY } from "../lib/theme";
import { DELIVERABLES, RUNS, SUMMARY } from "../test/fixtures";

// jsdom has no canvas; the chart's drawing is Chart.js's business, not ours.
vi.mock("react-chartjs-2", () => ({ Bar: () => <div data-testid="chart" /> }));

const answer = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body)));

function mockOverview() {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    return answer(url.startsWith("/api/summary") ? SUMMARY : url.startsWith("/api/deliverables") ? DELIVERABLES : RUNS);
  });
}

afterEach(() => {
  window.localStorage.clear();
  delete document.documentElement.dataset.theme;
});

describe("Brand and theme", () => {
  it("shows the GeneLabs lockup as the page heading", async () => {
    window.location.hash = "#/";
    mockOverview();
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "GeneLabs" })).toBeInTheDocument();
    expect(screen.getByText("Cyber Threat Intelligence")).toBeInTheDocument();
    expect(await screen.findByText("151")).toBeInTheDocument();
  });

  it("switches theme, remembers it, and hands back to the system", async () => {
    mockOverview();
    render(<App />);
    const group = screen.getByRole("group", { name: "Theme" });
    expect(screen.getByRole("button", { name: "System" })).toHaveAttribute("aria-pressed", "true");
    expect(group).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Dark" }));
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(THEME_KEY)).toBe("dark");

    await userEvent.click(screen.getByRole("button", { name: "Light" }));
    expect(document.documentElement.dataset.theme).toBe("light");

    await userEvent.click(screen.getByRole("button", { name: "System" }));
    expect(document.documentElement.dataset.theme).toBeUndefined();
    expect(window.localStorage.getItem(THEME_KEY)).toBeNull();
  });

  it("starts on a saved choice", () => {
    window.localStorage.setItem(THEME_KEY, "dark");
    mockOverview();
    render(<App />);
    expect(screen.getByRole("button", { name: "Dark" })).toHaveAttribute("aria-pressed", "true");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
