import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import type { Brand, CompanyList } from "../api/types";
import { BRAND, BRAND_PREVIEW, COMPANIES, DELIVERABLES, ME, RUNS, SUMMARY } from "../test/fixtures";

vi.mock("react-chartjs-2", () => ({ Bar: () => <div data-testid="chart" /> }));

const answer = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));

const ACME: Brand = { ...BRAND, slug: "acme", name: "Acme Biotech", version: "acme1" };

interface Call {
  url: string;
  method: string;
  headers: Record<string, string>;
  body: unknown;
}

/** A backend with two companies that really switches, and records every call. */
function mockApi() {
  const calls: Call[] = [];
  let state: CompanyList = structuredClone(COMPANIES);
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    const body = typeof init?.body === "string" ? (JSON.parse(init.body) as { slug: string; name: string }) : undefined;
    calls.push({ url, method, headers: (init?.headers ?? {}) as Record<string, string>, body });
    if (url === "/api/companies" && method === "POST") {
      state = {
        ...state,
        companies: [...state.companies, { slug: body!.slug, name: body!.name, program: "", has_runs: false }],
      };
      return answer(state, 201);
    }
    if (url === "/api/companies/active") {
      state = { ...state, active: body!.slug };
      return answer(state);
    }
    if (url === "/api/companies") return answer(state);
    if (url === "/api/me") return answer(ME);
    if (url === "/api/brand/preview") return answer(BRAND_PREVIEW);
    if (url.startsWith("/api/brand")) return answer(state.active === "acme" ? ACME : BRAND);
    if (url.startsWith("/api/summary")) return answer(SUMMARY);
    if (url.startsWith("/api/deliverables")) return answer(state.active === "acme" ? [] : DELIVERABLES);
    if (url.startsWith("/api/stakeholders")) {
      return answer({ exists: false, has_example: false, stakeholders: [] });
    }
    return answer(RUNS);
  });
  return calls;
}

const picker = () => screen.findByRole("combobox", { name: "Company" });

beforeEach(() => {
  window.location.hash = "#/";
});

afterEach(() => {
  document.documentElement.removeAttribute("style");
});

describe("Company picker", () => {
  it("lists the companies with the active one chosen", async () => {
    mockApi();
    render(<App />);
    const select = await picker();
    expect(select).toHaveValue("genelabs");
    expect(screen.getByRole("option", { name: "Acme Biotech" })).toBeInTheDocument();
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("switches company and reloads what the page shows", async () => {
    const calls = mockApi();
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "GeneLabs" })).toBeInTheDocument();
    const brandReads = () => calls.filter((c) => c.url === "/api/brand").length;
    const before = brandReads();

    await userEvent.selectOptions(await picker(), "acme");

    expect(await screen.findByRole("heading", { level: 1, name: "Acme Biotech" })).toBeInTheDocument();
    const put = calls.find((c) => c.url === "/api/companies/active");
    expect(put?.body).toEqual({ slug: "acme" });
    expect(put?.headers["X-CTI-Console"]).toBe("1");
    expect(brandReads()).toBeGreaterThan(before);
    expect(screen.getByRole("note")).toHaveTextContent(
      "Acme Biotech has no pipeline runs yet. Fill in what the pipeline should watch in data/companies/acme/profile.json",
    );
    expect(screen.getByRole("note")).toHaveTextContent("COMPANY=acme scripts/run-local.sh bulletin-scan");
  });

  it("names the shown company on every write, so a stale tab cannot save elsewhere", async () => {
    window.location.hash = "#/stakeholders/new";
    const calls = mockApi();
    render(<App />);
    await userEvent.selectOptions(await picker(), "acme");
    await screen.findByRole("heading", { level: 1, name: "Acme Biotech" });
    await userEvent.type(await screen.findByLabelText("Name (required)"), "Dana");
    await userEvent.type(screen.getByLabelText(/^Team/), "SOC");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/api/stakeholders" && c.method === "POST")).toBe(true));
    const post = calls.find((c) => c.url === "/api/stakeholders" && c.method === "POST");
    expect(post?.headers["X-CTI-Company"]).toBe("acme");
  });
});

describe("Settings, Companies", () => {
  it("adds a blank company, shows it, and opens its Branding tab", async () => {
    window.location.hash = "#/settings/companies";
    const calls = mockApi();
    render(<App />);
    await userEvent.type(await screen.findByLabelText("Company name"), "Initech, Inc.");
    expect(screen.getByLabelText(/^Short name/)).toHaveValue("initech-inc");
    await userEvent.click(screen.getByRole("button", { name: /Add and show it/ }));

    await waitFor(() => expect(window.location.hash).toBe("#/settings/branding"));
    const post = calls.find((c) => c.url === "/api/companies" && c.method === "POST");
    expect(post?.body).toEqual({ name: "Initech, Inc.", slug: "initech-inc", source: null });
    const put = calls.find((c) => c.url === "/api/companies/active");
    expect(put?.body).toEqual({ slug: "initech-inc" });
  });

  it("copies a company's branding under a new name", async () => {
    window.location.hash = "#/settings/companies";
    const calls = mockApi();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Copy GeneLabs" }));
    expect(screen.getByLabelText("Company name")).toHaveValue("GeneLabs copy");
    expect(screen.getByLabelText(/^Short name/)).toHaveValue("genelabs-copy");
    expect(screen.getByLabelText(/^Start from/)).toHaveValue("genelabs");
    await userEvent.click(screen.getByRole("button", { name: /Add and show it/ }));
    await waitFor(() => expect(calls.some((c) => c.url === "/api/companies" && c.method === "POST")).toBe(true));
    expect(calls.find((c) => c.method === "POST")?.body).toMatchObject({ source: "genelabs" });
  });

  it("will not add a short name already in use", async () => {
    window.location.hash = "#/settings/companies";
    mockApi();
    render(<App />);
    await userEvent.type(await screen.findByLabelText("Company name"), "Acme");
    const slug = screen.getByLabelText(/^Short name/);
    await userEvent.clear(slug);
    await userEvent.type(slug, "genelabs");
    expect(screen.getByText("Another company already uses this short name.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Add and show it/ })).toBeDisabled();
  });

  it("switches from the list", async () => {
    window.location.hash = "#/settings/companies";
    const calls = mockApi();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Show this company" }));
    expect(await screen.findByText("Shown now", { selector: "span" })).toBeInTheDocument();
    expect(calls.find((c) => c.url === "/api/companies/active")?.body).toEqual({ slug: "acme" });
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Company" })).toHaveValue("acme"));
  });
});
