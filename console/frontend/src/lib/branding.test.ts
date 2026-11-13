import { describe, expect, it } from "vitest";

import { BRAND } from "../test/fixtures";
import { completeDraft, draftOf, isHex, isSlug, normaliseHex, sameDraft, slugOf, tokenStyle } from "./branding";
import { parseRoute } from "./route";

describe("branding helpers", () => {
  it("normalises hex the way company.json keeps it", () => {
    expect(normaliseHex(" #1d4ed8 ")).toBe("1D4ED8");
    expect(isHex("#1d4ed8")).toBe(true);
    expect(isHex("1d4ed")).toBe(false);
    expect(isHex("GGGGGG")).toBe(false);
  });

  it("completes a draft by trimming names and upper casing colours", () => {
    const draft = { ...draftOf(BRAND), name: "  Acme  ", palette: { ...BRAND.palette, accent: "#1d4ed8" } };
    const ready = completeDraft(draft);
    expect(ready?.name).toBe("Acme");
    expect(ready?.palette.accent).toBe("1D4ED8");
  });

  it("holds back a draft with an empty name, a long name or a bad colour", () => {
    expect(completeDraft({ ...draftOf(BRAND), name: "   " })).toBeNull();
    expect(completeDraft({ ...draftOf(BRAND), contact: "x".repeat(201) })).toBeNull();
    expect(completeDraft({ ...draftOf(BRAND), palette: { ...BRAND.palette, tint: "red" } })).toBeNull();
  });

  it("treats drafts that would save the same thing as the same", () => {
    const a = draftOf(BRAND);
    expect(sameDraft(a, { ...a, name: " GeneLabs ", palette: { ...a.palette, accent: "#167d61" } })).toBe(true);
    expect(sameDraft(a, { ...a, name: "Acme" })).toBe(false);
  });

  it("turns tokens into custom properties for one preview box", () => {
    expect(tokenStyle({ accent: "#167d61" })).toEqual({ "--color-accent": "#167d61" });
  });

  it("routes Settings to its Branding tab, whatever follows", () => {
    expect(parseRoute("#/settings")).toEqual({ page: "settings", section: "branding" });
    expect(parseRoute("#/settings/branding")).toEqual({ page: "settings", section: "branding" });
    expect(parseRoute("#/settings/nope")).toEqual({ page: "settings", section: "branding" });
  });
});

describe("company short names", () => {
  it("makes a folder safe short name from a company name", () => {
    expect(slugOf("Acme Biotech, Inc.")).toBe("acme-biotech-inc");
    expect(slugOf("  Société Générale ")).toBe("societe-generale");
    expect(slugOf("---")).toBe("");
    expect(slugOf("x".repeat(60))).toHaveLength(40);
  });

  it("accepts only what the backend accepts", () => {
    expect(isSlug("acme-eu")).toBe(true);
    expect(isSlug("-acme")).toBe(false);
    expect(isSlug("Acme")).toBe(false);
    expect(isSlug("../x")).toBe(false);
    expect(isSlug("")).toBe(false);
  });
});
