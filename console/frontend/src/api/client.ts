import { useQuery } from "@tanstack/react-query";

import type { Run, Summary } from "./types";

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
