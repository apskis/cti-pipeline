import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import type { Brand } from "../api/types";
import { THEME_KEY } from "../lib/theme";
import { BRAND, DELIVERABLES, RUNS, SUMMARY } from "../test/fixtures";

// jsdom has no canvas; the chart's drawing is Chart.js's business, not ours.
vi.mock("react-chartjs-2", () => ({ Bar: () => <div data-testid="chart" /> }));

const answer = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));

function mockOverview(brand: Brand | null = BRAND) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.startsWith("/api/brand")) return brand ? answer(brand) : answer({ detail: "No brand file" }, 500);
    return answer(url.startsWith("/api/summary") ? SUMMARY : url.startsWith("/api/deliverables") ? DELIVERABLES : RUNS);
  });
}

const token = (name: string) => document.documentElement.style.getPropertyValue(`--color-${name}`);

afterEach(() => {
  window.localStorage.clear();
  delete document.documentElement.dataset.theme;
  document.documentElement.removeAttribute("style");
});

describe("Brand and theme", () => {
  it("shows the company's lockup from the brand file as the page heading", async () => {
    window.location.hash = "#/";
    mockOverview();
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "GeneLabs" })).toBeInTheDocument();
    expect(screen.getByText("Cyber Threat Intelligence")).toBeInTheDocument();
    expect(document.querySelector('img[src="/api/brand/symbol"]')).not.toBeNull();
    expect(document.title).toBe("GeneLabs CTI console");
    expect(await screen.findByText("151")).toBeInTheDocument();
  });

  it("shows another company with no code change", async () => {
    mockOverview({ ...BRAND, slug: "acme", name: "Acme", program: "Threat Intel", light: { accent: "#aa0000" } });
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "Acme" })).toBeInTheDocument();
    expect(screen.getByText("Threat Intel")).toBeInTheDocument();
    expect(token("accent")).toBe("#aa0000");
  });

  it("paints the colours of the theme on show, and only those", async () => {
    window.localStorage.setItem(THEME_KEY, "light");
    mockOverview();
    render(<App />);
    await waitFor(() => expect(token("accent")).toBe("#167d61"));
    expect(token("brand")).toBe("#103b32");

    await userEvent.click(screen.getByRole("button", { name: "Dark" }));
    expect(token("accent")).toBe("#3fb48c");
    // The dark set has no brand token, so index.css's own dark value shows, not light's.
    expect(token("brand")).toBe("");
  });

  it("refuses colour values that are not plain hex", async () => {
    mockOverview({ ...BRAND, light: { accent: "red; background: url(x)", "bad name!": "#000000" } });
    render(<App />);
    await screen.findByRole("heading", { level: 1, name: "GeneLabs" });
    expect(token("accent")).toBe("");
  });

  it("still names the page when the brand file cannot be read", async () => {
    mockOverview(null);
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "CTI console" }, { timeout: 4000 })).toBeInTheDocument();
    expect(document.querySelector('img[src="/api/brand/symbol"]')).toBeNull();
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
