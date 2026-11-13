import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  Audience,
  Brand,
  CveRegister,
  Deliverable,
  DeliverableDocument,
  Run,
  RunDetail,
  Stakeholder,
  StakeholderInput,
  StakeholderList,
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

export function useBrand() {
  return useQuery({
    queryKey: ["brand"],
    queryFn: () => getJson<Brand>("/api/brand"),
    // The brand changes only when someone edits company.json; a reload picks that up.
    staleTime: Infinity,
  });
}

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

const deliverablePath = (id: string, part: "html" | "file" | "pdf" | "pdf/ready"): string =>
  `/api/deliverables/${encodeURIComponent(id)}/${part}`;

export const fileUrl = (id: string): string => deliverablePath(id, "file");

/** The branded PDF, shown in the page, or saved when `download` is set. */
export const pdfUrl = (id: string, download = false): string =>
  deliverablePath(id, "pdf") + (download ? "?download=true" : "");

/**
 * Asks the backend to make the PDF (once; it is cached), so the page can say what is
 * happening before it frames the finished file. Word's first export can take a minute.
 */
export function usePdfReady(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["pdf", id],
    queryFn: () => getJson<{ id: string; bytes: number }>(deliverablePath(id, "pdf/ready")),
    enabled,
    staleTime: STALE_MS,
    retry: false,
  });
}

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

export function useStakeholders() {
  return useQuery({
    queryKey: ["stakeholders"],
    queryFn: () => getJson<StakeholderList>("/api/stakeholders"),
    staleTime: STALE_MS,
  });
}

export function useAudience() {
  return useQuery({
    queryKey: ["audience"],
    queryFn: () => getJson<Audience>("/api/audience"),
    staleTime: STALE_MS,
  });
}

/** The backend refuses a write without this header, so other sites cannot send one. */
const WRITE_HEADERS = { "Content-Type": "application/json", "X-CTI-Console": "1" };

async function send<T>(method: "POST" | "PUT" | "DELETE", path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: WRITE_HEADERS,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new ApiError(saveProblem(response.status, detail), response.status);
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

/** A plain sentence from FastAPI's error body, which is a string or a list of field errors. */
function saveProblem(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { loc?: unknown[]; msg?: string };
    const field = String(first.loc?.at(-1) ?? "a field").replace(/_/g, " ");
    return `Check ${field}: ${first.msg ?? "not accepted"}.`;
  }
  return `The console API answered ${status}.`;
}

const stakeholderPath = (id: string): string => `/api/stakeholders/${encodeURIComponent(id)}`;

/** Add, change or remove a stakeholder; every view that uses the list is refreshed after. */
export function useStakeholderWrites() {
  const client = useQueryClient();
  const refresh = () => {
    void client.invalidateQueries({ queryKey: ["stakeholders"] });
    void client.invalidateQueries({ queryKey: ["audience"] });
  };
  return {
    save: useMutation({
      mutationFn: ({ id, input }: { id: string | null; input: StakeholderInput }) =>
        id === null
          ? send<Stakeholder>("POST", "/api/stakeholders", input)
          : send<Stakeholder>("PUT", stakeholderPath(id), input),
      onSuccess: refresh,
    }),
    remove: useMutation({
      mutationFn: (id: string) => send<void>("DELETE", stakeholderPath(id)),
      onSuccess: refresh,
    }),
    startFromExample: useMutation({
      mutationFn: () => send<unknown>("POST", "/api/stakeholders/start-from-example"),
      onSuccess: refresh,
    }),
  };
}
