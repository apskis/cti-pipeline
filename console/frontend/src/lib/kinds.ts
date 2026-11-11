// Display names for the deliverable kinds the backend reports, in the order the
// Reports page lists them. A kind missing here still shows, under its raw name.
export const KIND_LABELS: Record<string, string> = {
  bulletin: "Bulletins",
  hunt: "Hunt packages",
  awareness: "Awareness posts",
  cve_brief: "CVE briefs",
  weekly: "Weekly reports",
  quarterly: "Quarterly briefs",
};

export const kindLabel = (kind: string): string => KIND_LABELS[kind] ?? kind;
