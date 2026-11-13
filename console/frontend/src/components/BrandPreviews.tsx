import { Check, X } from "lucide-react";
import type { CSSProperties } from "react";

import { brandImageUrl } from "../api/client";
import type { BrandInput, ContrastCheck } from "../api/types";
import { tokenStyle } from "../lib/branding";

interface ConsolePreviewProps {
  theme: "Light" | "Dark";
  tokens: Record<string, string>;
  draft: BrandInput;
  version: string;
}

/** A small copy of the console's header and a card, drawn in the draft's colours. */
// index.css leaves the light symbol tile clear; without this the page's own theme leaks in.
const LIGHT_DEFAULTS = { "symbol-tile": "transparent" };

export const ConsolePreview = ({ theme, tokens, draft, version }: ConsolePreviewProps) => (
  <figure className="m-0">
    <figcaption className="mb-1 text-xs text-muted">Console, {theme.toLowerCase()} theme</figcaption>
    <div
      style={tokenStyle(theme === "Light" ? { ...LIGHT_DEFAULTS, ...tokens } : tokens) as CSSProperties} className="rounded-lg border border-line bg-page p-3 text-ink">
      <div className="flex items-center gap-2 border-b-2 border-accent pb-2">
        <span className="inline-flex h-7 items-center rounded bg-symbol-tile p-0.5">
          <img src={brandImageUrl("symbol", version)} alt="" className="h-full w-auto" />
        </span>
        <span className="h-6 w-px bg-rung" />
        <span className="leading-tight">
          <span className="block text-sm font-semibold text-brand">{draft.name || "Company name"}</span>
          <span className="block text-[0.6rem] font-medium tracking-[0.12em] text-accent uppercase">
            {draft.program || "Program name"}
          </span>
        </span>
      </div>
      <div className="mt-2 flex gap-3 text-xs">
        <span className="border-b-2 border-accent font-medium text-brand">Overview</span>
        <span className="text-muted">Reports</span>
        <span className="text-faint">Runs</span>
      </div>
      <div className="mt-2 flex items-end gap-2 rounded-md border border-line bg-surface p-2">
        <div className="flex-1">
          <p className="text-[0.65rem] text-muted">Bulletins</p>
          <p className="text-lg font-semibold">160</p>
        </div>
        <div aria-hidden className="flex h-8 items-end gap-0.5">
          <span className="w-2 bg-series-scan" style={{ height: "100%" }} />
          <span className="w-2 bg-series-build" style={{ height: "60%" }} />
          <span className="w-2 bg-series-report" style={{ height: "80%" }} />
        </div>
        <span className="rounded bg-accent px-2 py-1 text-xs text-on-accent">Open</span>
      </div>
      <p className="mt-2 rounded bg-accent-soft px-2 py-1 text-xs text-accent-soft-ink">Picked for you</p>
    </div>
  </figure>
);

/** The top and foot of a report page, in the draft's document colours. */
export const DocumentPreview = ({ draft, version }: { draft: BrandInput; version: string }) => {
  const p = draft.palette;
  const hex = (value: string) => `#${value.replace(/^#/, "")}`;
  return (
    <figure className="m-0">
      <figcaption className="mb-1 text-xs text-muted">Report page</figcaption>
      <div className="rounded-lg border border-line bg-white p-3 text-xs" style={{ color: hex(p.text) }}>
        <img src={brandImageUrl("banner", version)} alt="" className="w-full" />
        <p className="mt-2 text-sm font-semibold" style={{ color: hex(p.primary) }}>
          Example bulletin title
        </p>
        <hr className="my-1.5 border-0 border-t-2" style={{ borderColor: hex(p.accent) }} />
        <p className="rounded px-2 py-1" style={{ background: hex(p.tint) }}>
          <strong>Relevance to {draft.name || "Company name"}:</strong> HIGH. Why it matters here.{" "}
          <span className="underline" style={{ color: hex(p.accent) }}>
            Source link
          </span>
        </p>
        <table className="mt-2 w-full border-collapse" style={{ borderColor: hex(p.rule) }}>
          <thead>
            <tr style={{ background: hex(p.primary), color: "#ffffff" }}>
              <th className="px-1.5 py-0.5 text-left font-medium">Field</th>
              <th className="px-1.5 py-0.5 text-left font-medium">Value</th>
            </tr>
          </thead>
          <tbody>
            {["Threat actor", "Severity", "Affected"].map((row, i) => (
              <tr key={row} style={{ background: i % 2 ? hex(p.zebra) : "#ffffff", borderBottom: `1px solid ${hex(p.rule)}` }}>
                <td className="px-1.5 py-0.5">{row}</td>
                <td className="px-1.5 py-0.5">Example</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-3 flex items-center gap-2 border-t pt-1.5" style={{ borderColor: hex(p.rule), color: hex(p.muted) }}>
          <img src={brandImageUrl("logo", version)} alt="" className="h-4 w-auto" />
          <span className="text-[0.6rem]">
            © {new Date().getFullYear()} {draft.legal_name || "Legal name"}. {draft.contact}
          </span>
        </div>
      </div>
    </figure>
  );
};

/** Every contrast rule, failures first, each with its ratio and what it needs. */
export const ContrastList = ({ checks }: { checks: ContrastCheck[] }) => {
  const sorted = [...checks].sort((a, b) => Number(a.ok) - Number(b.ok));
  const failed = checks.filter((c) => !c.ok).length;
  return (
    <section aria-labelledby="contrast-title">
      <h3 id="contrast-title" className="text-sm font-medium">
        Readability
      </h3>
      <p className="text-xs text-muted">
        {failed === 0
          ? "Every pair passes. Text needs 4.5:1 against its background; charts and lines need 3:1."
          : `${failed} ${failed === 1 ? "pair is" : "pairs are"} too close to read. Change the colour named, then save.`}
      </p>
      <ul className="mt-2 space-y-1 text-xs">
        {sorted.map((check) => (
          <li key={check.label} className="flex items-center gap-2">
            {check.ok ? (
              <Check aria-label="Passes" size={14} className="shrink-0 text-ok-ink" />
            ) : (
              <X aria-label="Fails" size={14} className="shrink-0 text-fail-ink" />
            )}
            <span
              aria-hidden
              className="inline-flex h-4 w-6 shrink-0 items-center justify-center rounded border border-line text-[0.6rem] font-semibold"
              style={{ background: check.background, color: check.foreground }}
            >
              Aa
            </span>
            <span className={check.ok ? "text-muted" : "font-medium"}>{check.label}</span>
            <span className="ml-auto shrink-0 tabular-nums text-faint">
              {check.ratio.toFixed(1)}:1{check.ok ? "" : `, needs ${check.needed}:1`}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
};
