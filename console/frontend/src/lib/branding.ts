import { useEffect, useState } from "react";

import type { Brand, BrandImage, BrandInput, Palette } from "../api/types";

/** The seven document colours, in plain words, and where each one shows. */
export const COLOUR_FIELDS: { key: keyof Palette; label: string; use: string }[] = [
  { key: "primary", label: "Headings", use: "Headings, table headers and the console name" },
  { key: "accent", label: "Accent", use: "Rules, bullets, links, buttons and charts" },
  { key: "text", label: "Body text", use: "All running text" },
  { key: "muted", label: "Secondary text", use: "Footers and small print" },
  { key: "rule", label: "Lines", use: "Light rules and table borders" },
  { key: "tint", label: "Tint", use: "Label cells, callouts and soft backgrounds" },
  { key: "zebra", label: "Table stripe", use: "Every other table row" },
];

type TextKey = Exclude<keyof BrandInput, "palette">;

export const TEXT_FIELDS: { key: TextKey; label: string; hint: string }[] = [
  { key: "name", label: "Company name", hint: 'In the console header and "Relevance to …" in reports' },
  { key: "legal_name", label: "Legal name", hint: "In the copyright line of every report" },
  { key: "department", label: "Department", hint: "In each report's document properties" },
  { key: "program", label: "Program name", hint: "Under the company name in the console" },
  { key: "contact", label: "Footer contact", hint: "At the foot of bulletins" },
];

/** The rules the backend holds each image to, said the same way it says them. */
export const IMAGE_FIELDS: { kind: BrandImage; label: string; use: string; shape: string }[] = [
  { kind: "logo", label: "Logo", use: "At the foot of every report", shape: "1.5 to 8 times as wide as it is tall" },
  { kind: "banner", label: "Banner", use: "Across the top of every report", shape: "4 to 12 times as wide as it is tall" },
  { kind: "symbol", label: "Symbol", use: "Beside the company name in the console", shape: "0.3 to 3 times as wide as it is tall" },
];

export const MAX_TEXT = 200;
const HEX = /^[0-9A-F]{6}$/;

/** "#1d4ed8", " 1d4ed8 " or "1D4ED8" all become "1D4ED8", the form company.json keeps. */
export const normaliseHex = (value: string): string => value.trim().replace(/^#/, "").toUpperCase();

export const isHex = (value: string): boolean => HEX.test(normaliseHex(value));

export function draftOf(brand: Brand): BrandInput {
  const { name, legal_name, department, program, contact, palette } = brand;
  return { name, legal_name, department, program, contact, palette: { ...palette } };
}

/** The draft as the backend wants it, or null while a field is empty, too long or not hex. */
export function completeDraft(draft: BrandInput): BrandInput | null {
  const palette: Palette = { ...draft.palette };
  for (const { key } of COLOUR_FIELDS) palette[key] = normaliseHex(draft.palette[key]);
  const ready: BrandInput = { ...draft, palette };
  for (const { key } of TEXT_FIELDS) ready[key] = draft[key].trim();
  const textsOk = TEXT_FIELDS.every(({ key }) => ready[key].length > 0 && ready[key].length <= MAX_TEXT);
  const coloursOk = COLOUR_FIELDS.every(({ key }) => HEX.test(palette[key]));
  return textsOk && coloursOk ? ready : null;
}

/** Whether two drafts would save the same thing. */
export function sameDraft(a: BrandInput, b: BrandInput): boolean {
  return JSON.stringify(completeDraft(a)) === JSON.stringify(completeDraft(b));
}

/** The value, once it has stopped changing for `ms`, so typing does not send a request per key. */
export function useSettled<T>(value: T, ms = 300): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(value), ms);
    return () => window.clearTimeout(timer);
  }, [value, ms]);
  return settled;
}

/** Colour tokens as CSS custom properties, to theme one preview box and nothing else. */
export function tokenStyle(tokens: Record<string, string>): Record<string, string> {
  return Object.fromEntries(Object.entries(tokens).map(([name, value]) => [`--color-${name}`, value]));
}
