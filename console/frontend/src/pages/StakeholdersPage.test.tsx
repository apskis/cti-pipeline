import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "../App";
import {
  AUDIENCE,
  DELIVERABLES,
  DOCUMENT,
  NO_STAKEHOLDERS,
  STAKEHOLDERS,
} from "../test/fixtures";

const answer = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }));

type Call = { url: string; init?: RequestInit };

/** Serves the stakeholder views and records every call, writes included. */
function mockApi(list = STAKEHOLDERS) {
  const calls: Call[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    calls.push({ url, init });
    if (init?.method === "DELETE") return Promise.resolve(new Response(null, { status: 204 }));
    if (init?.method === "POST" && url.endsWith("/start-from-example")) return answer(STAKEHOLDERS, 201);
    if (init?.method === "POST") {
      return answer({ id: "sh-00000009", ...JSON.parse(String(init.body)) }, 201);
    }
    if (url.startsWith("/api/stakeholders")) return answer(list);
    if (url.startsWith("/api/audience")) return answer(AUDIENCE);
    if (url.startsWith("/api/deliverables/CTI26-137/html")) return answer(DOCUMENT);
    return answer(DELIVERABLES);
  });
  return calls;
}

const writes = (calls: Call[]) => calls.filter((c) => c.init?.method);

describe("Stakeholders", () => {
  it("lists people by team and the teams nobody covers", async () => {
    window.location.hash = "#/stakeholders";
    mockApi();
    render(<App />);
    expect(await screen.findByRole("link", { name: /Jordan Reyes/ })).toBeInTheDocument();
    expect(screen.getByText("3 stakeholders in 3 teams")).toBeInTheDocument();
    const gaps = await screen.findByRole("region", { name: /nobody on file/ });
    expect(within(gaps).getByText(/Lab Operations/)).toBeInTheDocument();
    expect(within(gaps).getByRole("link", { name: "Add" })).toHaveAttribute(
      "href",
      "#/stakeholders/new:Lab%20Operations",
    );
  });

  it("shows what a person gets and what the reports ask their team", async () => {
    window.location.hash = "#/stakeholders/sh-00000001";
    mockApi();
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Jordan Reyes" })).toBeInTheDocument();
    expect(screen.getByText("Hunt packages")).toBeInTheDocument();
    expect(await screen.findByText("Would Falcon see it?")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "CTI26-137" })).toHaveAttribute("href", "#/reports/CTI26-137");
  });

  it("adds a stakeholder for a team the reports name, through the guarded write", async () => {
    window.location.hash = "#/stakeholders/new:Lab%20Operations";
    const calls = mockApi();
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Add a stakeholder" })).toBeInTheDocument();
    expect(screen.getByLabelText(/^Team/)).toHaveValue("Lab Operations");
    await userEvent.type(screen.getByLabelText("Name (required)"), "Morgan Ellis");
    await userEvent.type(screen.getByLabelText(/Also known as/), "Lab Ops, Laboratory");
    await userEvent.click(screen.getByLabelText("Bulletins"));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    const [post] = writes(calls);
    expect(post?.url).toBe("/api/stakeholders");
    expect(post?.init?.method).toBe("POST");
    expect(new Headers(post?.init?.headers).get("X-CTI-Console")).toBe("1");
    expect(JSON.parse(String(post?.init?.body))).toMatchObject({
      name: "Morgan Ellis",
      team: "Lab Operations",
      also_known_as: ["Lab Ops", "Laboratory"],
      receives: ["bulletin"],
    });
    await vi.waitFor(() => expect(window.location.hash).toBe("#/stakeholders/sh-00000009"));
  });

  it("shows why a save was refused", async () => {
    window.location.hash = "#/stakeholders/new";
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) =>
      init?.method === "POST"
        ? answer({ detail: [{ loc: ["body", "email"], msg: "does not look like an email address" }] }, 422)
        : answer(String(input).startsWith("/api/stakeholders") ? STAKEHOLDERS : DELIVERABLES),
    );
    render(<App />);
    await userEvent.type(await screen.findByLabelText("Name (required)"), "X");
    await userEvent.type(screen.getByLabelText(/^Team/), "SOC");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Not saved. Check email: does not look like an email address.",
    );
  });

  it("asks before deleting", async () => {
    window.location.hash = "#/stakeholders/sh-00000003";
    const calls = mockApi();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Delete" }));
    expect(writes(calls)).toEqual([]);
    const dialog = screen.getByRole("alertdialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Delete" }));
    expect(writes(calls).map((c) => [c.init?.method, c.url])).toEqual([
      ["DELETE", "/api/stakeholders/sh-00000003"],
    ]);
  });

  it("offers the example list when there is no list yet", async () => {
    window.location.hash = "#/stakeholders";
    const calls = mockApi(NO_STAKEHOLDERS);
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Start from the example list" }));
    expect(writes(calls).map((c) => c.url)).toEqual(["/api/stakeholders/start-from-example"]);
  });

  it("says in the reader who a report is for, with the gaps", async () => {
    window.location.hash = "#/reports/CTI26-137";
    mockApi();
    render(<App />);
    const panel = await screen.findByRole("region", { name: "Intended for" });
    expect(within(panel).getByRole("link", { name: "Jordan Reyes" })).toHaveAttribute(
      "href",
      "#/stakeholders/sh-00000001",
    );
    expect(within(panel).getByRole("link", { name: /Nobody on file, add/ })).toHaveAttribute(
      "href",
      "#/stakeholders/new:Lab%20Operations",
    );
    expect(within(panel).getByText("Gets all bulletins:")).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: "Copy 2 addresses" })).toBeInTheDocument();
  });
});
