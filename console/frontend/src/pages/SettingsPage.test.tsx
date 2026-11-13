import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import type { Brand, BrandPreview } from "../api/types";
import { BRAND, BRAND_PREVIEW, DELIVERABLES, RUNS, SUMMARY } from "../test/fixtures";

vi.mock("react-chartjs-2", () => ({ Bar: () => <div data-testid="chart" /> }));

const answer = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status }));

interface Call {
  url: string;
  method: string;
  headers: Record<string, string>;
  body: unknown;
}

function mockApi(options: { preview?: BrandPreview; saveStatus?: number; uploadStatus?: number } = {}) {
  const calls: Call[] = [];
  let brand: Brand = BRAND;
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    calls.push({
      url,
      method,
      headers: (init?.headers ?? {}) as Record<string, string>,
      body: typeof init?.body === "string" ? JSON.parse(init.body) : init?.body,
    });
    if (url === "/api/brand/preview") return answer(options.preview ?? BRAND_PREVIEW);
    if (url === "/api/brand" && method === "PUT") {
      if (options.saveStatus) return answer({ detail: "Not saved: Accent on white is 2.1:1" }, options.saveStatus);
      brand = { ...brand, ...(JSON.parse(String(init?.body)) as Partial<Brand>), version: "v2" };
      return answer(brand);
    }
    if (url.startsWith("/api/brand/assets/") && method === "PUT") {
      if (options.uploadStatus) {
        return answer({ detail: "The banner is 1.0 times as wide as it is tall; it must be 4 to 12 times" }, options.uploadStatus);
      }
      brand = { ...brand, version: "v3" };
      return answer(brand);
    }
    if (url.startsWith("/api/brand")) return answer(brand);
    if (url.startsWith("/api/summary")) return answer(SUMMARY);
    if (url.startsWith("/api/deliverables")) return answer(DELIVERABLES);
    return answer(RUNS);
  });
  return calls;
}

const saveButton = () => screen.getByRole("button", { name: /Save names and colours/ });

beforeEach(() => {
  window.location.hash = "#/settings/branding";
});

afterEach(() => {
  document.documentElement.removeAttribute("style");
});

describe("Settings, Branding", () => {
  it("opens from the Settings tab with the saved names and colours", async () => {
    window.location.hash = "#/";
    mockApi();
    render(<App />);
    await userEvent.click(screen.getByRole("link", { name: "Settings" }));
    expect(await screen.findByLabelText(/Company name/)).toHaveValue("GeneLabs");
    expect(screen.getByRole("textbox", { name: /^Accent/ })).toHaveValue("167D61");
    expect(screen.getByRole("link", { name: "Branding" })).toHaveAttribute("aria-current", "page");
    expect(saveButton()).toBeDisabled();
    expect(screen.getByText("No changes.")).toBeInTheDocument();
  });

  it("checks a changed colour, then saves names and colours together", async () => {
    const calls = mockApi();
    render(<App />);
    const name = await screen.findByLabelText(/Company name/);
    await userEvent.clear(name);
    await userEvent.type(name, "Acme");
    const accent = screen.getByRole("textbox", { name: /^Accent/ });
    await userEvent.clear(accent);
    await userEvent.type(accent, "#1d4ed8");

    await waitFor(() => expect(saveButton()).toBeEnabled());
    const previews = calls.filter((c) => c.url === "/api/brand/preview");
    expect(previews.at(-1)?.body).toMatchObject({ name: "Acme", palette: { accent: "1D4ED8" } });
    expect(previews.at(-1)?.headers["X-CTI-Console"]).toBe("1");

    await userEvent.click(saveButton());
    expect(await screen.findByText(/Saved\. The console shows it now/)).toBeInTheDocument();
    const put = calls.find((c) => c.url === "/api/brand" && c.method === "PUT");
    expect(put?.body).toMatchObject({ name: "Acme", palette: { accent: "1D4ED8" } });
    // The header follows the save at once.
    expect(screen.getByRole("heading", { level: 1, name: "Acme" })).toBeInTheDocument();
  });

  it("will not save colours that fail a readability check, and says which", async () => {
    mockApi({
      preview: {
        ...BRAND_PREVIEW,
        ok: false,
        checks: [
          ...BRAND_PREVIEW.checks.filter((c) => c.ok && c.label !== "Accent on white (links)"),
          { label: "Accent on white (links)", foreground: "#ffd400", background: "#ffffff", ratio: 1.4, needed: 4.5, ok: false },
        ],
      },
    });
    render(<App />);
    const accent = await screen.findByRole("textbox", { name: /^Accent/ });
    await userEvent.clear(accent);
    await userEvent.type(accent, "FFD400");
    expect(await screen.findByText("Fix the colours marked under Readability to save.")).toBeInTheDocument();
    expect(saveButton()).toBeDisabled();
    expect(screen.getByText("1 pair is too close to read. Change the colour named, then save.")).toBeInTheDocument();
    expect(screen.getByText(/needs 4.5:1/)).toBeInTheDocument();
  });

  it("asks for six hex digits and sends nothing until there are", async () => {
    const calls = mockApi();
    render(<App />);
    const tint = await screen.findByRole("textbox", { name: /^Tint/ });
    await userEvent.clear(tint);
    await userEvent.type(tint, "red");
    expect(screen.getByText("Six hex digits, such as 167D61")).toBeInTheDocument();
    expect(await screen.findByText("Fill in every name and give every colour six hex digits.")).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 400));
    expect(calls.filter((c) => c.url === "/api/brand/preview").every((c) => (c.body as Brand).palette.tint !== "RED")).toBe(true);
    expect(saveButton()).toBeDisabled();
  });

  it("undoes unsaved changes", async () => {
    mockApi();
    render(<App />);
    const name = await screen.findByLabelText(/Company name/);
    await userEvent.type(name, " Inc");
    await userEvent.click(screen.getByRole("button", { name: /Undo changes/ }));
    expect(name).toHaveValue("GeneLabs");
  });

  it("uploads a picked image as a PNG with the console header, and shows it", async () => {
    const calls = mockApi();
    render(<App />);
    const input = await screen.findByLabelText("Replace the banner");
    const file = new File([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], "banner.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() =>
      expect(screen.getByAltText("Current banner")).toHaveAttribute("src", "/api/brand/assets/banner?v=v3"),
    );
    const put = calls.find((c) => c.url === "/api/brand/assets/banner");
    expect(put?.method).toBe("PUT");
    expect(put?.headers).toMatchObject({ "Content-Type": "image/png", "X-CTI-Console": "1" });
  });

  it("says why an image was refused", async () => {
    mockApi({ uploadStatus: 422 });
    render(<App />);
    const input = await screen.findByLabelText("Replace the banner");
    fireEvent.change(input, { target: { files: [new File(["x"], "square.png", { type: "image/png" })] } });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Not replaced. The banner is 1.0 times as wide as it is tall; it must be 4 to 12 times",
    );
  });
});
