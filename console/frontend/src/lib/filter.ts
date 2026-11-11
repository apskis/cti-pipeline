import type { Deliverable, DeliverableStatus } from "../api/types";

export type StatusFilter = "all" | DeliverableStatus;

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
      (status === "all" || d.status === status) &&
      (!needle || `${d.id} ${d.title}`.toLowerCase().includes(needle)),
  );
}
