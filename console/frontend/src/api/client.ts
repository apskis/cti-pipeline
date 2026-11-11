import { useQuery } from "@tanstack/react-query";

import type {
  CveRegister,
  Deliverable,
  DeliverableDocument,
  Run,
  RunDetail,
  Summary,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new ApiError(`The console API answered ${response.status} for ${path}`, response.status);
  }
  return (await response.json()) as T;
}

// The pipeline writes at most a few times a day, so a minute of staleness is fine and
// keeps the page from rereading every document on each focus.
const STALE_MS = 60_000;

export function useSummary() {
  return useQuery({
    queryKey: ["summary"],
    queryFn: () => getJson<Summary>("/api/summary"),
    staleTime: STALE_MS,
  });
}

export function useRuns() {
  return useQuery({
    queryKey: ["runs"],
    queryFn: () => getJson<Run[]>("/api/runs?limit=200"),
    staleTime: STALE_MS,
  });
}

export function useDeliverables() {
  return useQuery({
    queryKey: ["deliverables"],
    queryFn: () => getJson<Deliverable[]>("/api/deliverables?limit=1000"),
    staleTime: STALE_MS,
  });
}

const deliverablePath = (id: string, part: "html" | "file"): string =>
  `/api/deliverables/${encodeURIComponent(id)}/${part}`;

export const fileUrl = (id: string): string => deliverablePath(id, "file");

export function useDeliverableDocument(id: string | null) {
  return useQuery({
    queryKey: ["deliverable", id],
    queryFn: () => getJson<DeliverableDocument>(deliverablePath(id ?? "", "html")),
    enabled: id !== null,
    staleTime: STALE_MS,
  });
}

export function useRunDetail(id: string | null) {
  return useQuery({
    queryKey: ["run", id],
    queryFn: () => getJson<RunDetail>(`/api/runs/${encodeURIComponent(id ?? "")}`),
    enabled: id !== null,
    staleTime: STALE_MS,
  });
}

export function useCves() {
  return useQuery({
    queryKey: ["cves"],
    queryFn: () => getJson<CveRegister>("/api/cves"),
    staleTime: STALE_MS,
  });
}
