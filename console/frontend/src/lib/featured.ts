import type { Deliverable } from "../api/types";

// The kinds a demo opens first, in the order the overview shows them, with the one line
// that tells a newcomer what each is for.
export const FEATURED_KINDS: { kind: string; label: string; blurb: string }[] = [
  { kind: "bulletin", label: "Latest bulletin", blurb: "A threat written up for the security team" },
  { kind: "hunt", label: "Latest hunt package", blurb: "Queries to look for that threat in our logs" },
  { kind: "cve_brief", label: "Latest CVE brief", blurb: "What vulnerability management should patch first" },
  { kind: "weekly", label: "Latest weekly report", blurb: "The week in one document for leadership" },
];

export interface Featured {
  label: string;
  blurb: string;
  item: Deliverable;
}

const newest = (a: Deliverable, b: Deliverable): number =>
  b.first_seen.localeCompare(a.first_seen) || b.modified.localeCompare(a.modified);

/**
 * The newest document of each featured kind that is not broken. A broken document is
 * never featured: it would open the demo on a fault. Kinds with nothing are left out.
 */
export function pickFeatured(items: Deliverable[]): Featured[] {
  const usable = items.filter((d) => d.status !== "broken").sort(newest);
  return FEATURED_KINDS.flatMap(({ kind, label, blurb }) => {
    const item = usable.find((d) => d.kind === kind);
    return item ? [{ label, blurb, item }] : [];
  });
}
