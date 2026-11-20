import type { Deliverable, DeliverableStatus } from "../api/types";

export type StatusFilter = "all" | DeliverableStatus | "flagged" | "needs-human";

function matchesStatus(d: Deliverable, status: StatusFilter): boolean {
  switch (status) {
    case "all":
      return true;
    case "flagged":
      return d.review?.verdict === "flag";
    case "needs-human":
      return d.guardrail?.status === "needs-human";
    default:
      return d.status === status;
  }
}

/** The Reports list after the kind, status and search filters. Search matches ID and title. */
export function filterDeliverables(
  items: Deliverable[],
  kind: string,
  status: StatusFilter,
  query: string,
): Deliverable[] {
  const needle = query.trim().toLowerCase();
  return items.filter(
    (d) =>
      (kind === "all" || d.kind === kind) &&
      matchesStatus(d, status) &&
      (!needle || `${d.id} ${d.title}`.toLowerCase().includes(needle)),
  );
}
