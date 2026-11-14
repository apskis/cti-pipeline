import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import type { CompanyList, Me } from "../api/types";
import {
  AUDIENCE,
  BRAND,
  BRAND_PREVIEW,
  COMPANIES,
  DELIVERABLES,
  RUNS,
  STAKEHOLDERS,
  SUMMARY,
} from "../test/fixtures";

vi.mock("react-chartjs-2", () => ({ Bar: () => <div data-testid="chart" /> }));

const answer = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));

const person = (roles: Me["roles"], platform_admin = false): Me => ({
  auth: "oidc",
  name: "Dana Reyes",
  email: "dana@genelabs.example",
  platform_admin,
  can_manage: platform_admin,
  roles,
  view_as: null,
});

interface Call {
  url: string;
  method: string;
  headers: Record<string, string>;
}

/** A signed in backend. `me` null answers 401, as when nobody is signed in. */
function mockApi(me: Me | null, companies: CompanyList = COMPANIES) {
  const calls: Call[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    calls.push({ url, method, headers: (init?.headers ?? {}) as Record<string, string> });
    if (url === "/api/me") return me ? answer(me) : answer({ detail: "Sign in to use the console" }, 401);
    if (!me) return answer({ detail: "Sign in to use the console" }, 401);
    if (url === "/api/auth/logout") return answer({ redirect: "https://login.example.test/logout" });
    if (url === "/api/companies") return answer(companies);
    if (url === "/api/brand/preview") return answer(BRAND_PREVIEW);
    if (url.startsWith("/api/brand")) return answer(BRAND);
    if (url.startsWith("/api/summary")) return answer(SUMMARY);
    if (url.startsWith("/api/deliverables")) return answer(DELIVERABLES);
    if (url.startsWith("/api/stakeholders")) return answer(STAKEHOLDERS);
    if (url.startsWith("/api/audience")) return answer(AUDIENCE);
    return answer(RUNS);
  });
  return calls;
}

beforeEach(() => {
  window.location.hash = "#/";
});

afterEach(() => {
  document.documentElement.removeAttribute("style");
});

describe("Sign in", () => {
  it("asks someone signed out to sign in, and shows nothing else", async () => {
    mockApi(null);
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Sign in to the CTI console" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/api/auth/login");
    expect(screen.queryByRole("navigation", { name: "Pages" })).not.toBeInTheDocument();
  });

  it("tells someone in no company to ask for one", async () => {
    mockApi(person({}), { active: "", companies: [] });
    render(<App />);
    expect(await screen.findByText("Your account has no company yet.")).toBeInTheDocument();
  });

  it("shows who is signed in, with their role, and signs them out", async () => {
    const calls = mockApi(person({ genelabs: "viewer" }));
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign, hash: "#/" });
    try {
      render(<App />);
      expect(await screen.findByText(/Dana Reyes/)).toHaveTextContent("Dana Reyes · Viewer");
      await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
      await waitFor(() => expect(assign).toHaveBeenCalledWith("https://login.example.test/logout"));
      const logout = calls.find((c) => c.url === "/api/auth/logout");
      expect(logout?.method).toBe("POST");
      expect(logout?.headers["X-CTI-Console"]).toBe("1");
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("says nothing about accounts on the local, single user console", async () => {
    mockApi({ ...person({}, true), auth: "off", name: "Local user" });
    render(<App />);
    expect(await screen.findByRole("combobox", { name: "Company" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
    expect(screen.getByText(/^Local only\./)).toBeInTheDocument();
  });
});

describe("Roles", () => {
  it("lets a viewer look at the branding but not change it", async () => {
    window.location.hash = "#/settings/branding";
    mockApi(person({ genelabs: "viewer" }));
    render(<App />);
    expect(await screen.findByRole("note")).toHaveTextContent("You can view GeneLabs's branding but not change it.");
    expect(await screen.findByLabelText(/Company name/)).toBeDisabled();
    expect(screen.getByRole("button", { name: /Save names and colours/ })).toBeDisabled();
    expect(screen.getByLabelText("Replace the logo")).toBeDisabled();
    expect(screen.queryByRole("link", { name: "Add or copy" })).not.toBeInTheDocument();
  });

  it("lets a company admin change the branding, but not add companies", async () => {
    window.location.hash = "#/settings/branding";
    mockApi(person({ genelabs: "admin" }));
    render(<App />);
    expect(await screen.findByLabelText(/Company name/)).toBeEnabled();
    expect(screen.queryByText(/but not change it/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Add or copy" })).not.toBeInTheDocument();

    window.location.hash = "#/settings/companies";
    expect(await screen.findByRole("heading", { name: "Companies" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Add a company" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Copy/ })).not.toBeInTheDocument();
  });

  it("gives a platform admin every control", async () => {
    window.location.hash = "#/settings/companies";
    mockApi(person({}, true));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Add a company" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add or copy" })).toBeInTheDocument();
    expect(screen.getByText(/Platform admin/)).toBeInTheDocument();
  });

  it("shows a viewer the stakeholders without ways to change them", async () => {
    const first = STAKEHOLDERS.stakeholders[0]!;
    window.location.hash = `#/stakeholders/${first.id}`;
    mockApi(person({ genelabs: "viewer" }));
    render(<App />);
    expect(await screen.findByRole("heading", { name: first.name })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Add" })).not.toBeInTheDocument();

    window.location.hash = "#/stakeholders/new";
    expect(await screen.findByText(/You can view this company's stakeholders but not change it/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Name (required)")).not.toBeInTheDocument();
  });
});

describe("View as", () => {
  const local = (view: Me["view_as"]): Me => {
    const role = view?.role;
    return {
      auth: "off",
      name: "Local user",
      email: "",
      platform_admin: role === "platform",
      can_manage: role === "platform",
      roles: view && view.role !== "platform" ? { [view.company]: view.role } : {},
      view_as: view,
    };
  };

  /** The local backend, which switches role on PUT /api/view-as as the real one does. */
  function mockLocal() {
    let me = local({ role: "platform", company: null });
    const calls: Call[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      calls.push({ url, method, headers: (init?.headers ?? {}) as Record<string, string> });
      if (url === "/api/view-as") {
        me = local(JSON.parse(String(init?.body)) as Me["view_as"]);
        return answer(me);
      }
      if (url === "/api/me") return answer(me);
      if (url === "/api/companies") return answer(COMPANIES);
      if (url === "/api/brand/preview") return answer(BRAND_PREVIEW);
      if (url.startsWith("/api/brand")) return answer(BRAND);
      if (url.startsWith("/api/summary")) return answer(SUMMARY);
      if (url.startsWith("/api/deliverables")) return answer(DELIVERABLES);
      if (url.startsWith("/api/stakeholders")) return answer(STAKEHOLDERS);
      if (url.startsWith("/api/audience")) return answer(AUDIENCE);
      return answer(RUNS);
    });
    return calls;
  }

  it("acts as a viewer, says so, and goes back to platform admin", async () => {
    window.location.hash = "#/settings/branding";
    const calls = mockLocal();
    render(<App />);
    const menu = await screen.findByRole("combobox", { name: "View as" });
    expect(await screen.findByLabelText(/Company name/)).toBeEnabled();
    expect(screen.queryByText(/Viewing as/)).not.toBeInTheDocument();

    await userEvent.selectOptions(menu, "Viewer of GeneLabs");
    expect((await screen.findByText(/Viewing as/)).closest("[role=status]")).toHaveTextContent(
      "Viewing as Viewer of GeneLabs.",
    );
    expect(await screen.findByLabelText(/Company name/)).toBeDisabled();
    expect(screen.queryByRole("link", { name: "Add or copy" })).not.toBeInTheDocument();
    const put = calls.find((c) => c.url === "/api/view-as");
    expect(put?.method).toBe("PUT");
    expect(put?.headers["X-CTI-Console"]).toBe("1");

    await userEvent.click(screen.getByRole("button", { name: "Back to platform admin" }));
    await waitFor(() => expect(screen.queryByText(/Viewing as/)).not.toBeInTheDocument());
    expect(await screen.findByLabelText(/Company name/)).toBeEnabled();
    expect(screen.getByRole("link", { name: "Add or copy" })).toBeInTheDocument();
  });

  it("is not there under sign in", async () => {
    mockApi(person({}, true));
    render(<App />);
    expect(await screen.findByRole("combobox", { name: "Company" })).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "View as" })).not.toBeInTheDocument();
  });
});
