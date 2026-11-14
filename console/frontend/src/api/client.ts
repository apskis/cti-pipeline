import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  Audience,
  Brand,
  BrandImage,
  BrandInput,
  BrandPreview,
  CompanyInput,
  CompanyList,
  CveRegister,
  Me,
  Deliverable,
  DeliverableDocument,
  Run,
  RunDetail,
  Stakeholder,
  StakeholderInput,
  StakeholderList,
  Summary,
  ViewAs,
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

/**
 * The company this page shows. Every write names it, and the backend refuses one for a
 * company that is no longer active, so a tab left open on one company cannot save into
 * another after a switch elsewhere.
 */
let shownCompany: string | null = null;

const COMPANIES_KEY = ["companies"];

/** Who is using the console. Under sign in, a 401 here means nobody is signed in. */
export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => getJson<Me>("/api/me"),
    staleTime: Infinity,
    // Signed out is an answer, not a fault to retry.
    retry: (count, error) => !(error instanceof ApiError && error.status === 401) && count < 1,
  });
}

/** Sign out here, then at the identity provider when it has a sign out page. */
export function useSignOut() {
  return useMutation({
    mutationFn: () => send<{ redirect: string }>("POST", "/api/auth/logout"),
    onSuccess: ({ redirect }) => window.location.assign(redirect),
  });
}

/**
 * Act as another role (sign in off only). The backend then answers as that role would,
 * so everything the page shows is fetched again.
 */
export function useViewAs() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (view: ViewAs) => send<Me>("PUT", "/api/view-as", view),
    onSuccess: async (me) => {
      client.setQueryData(["me"], me);
      await client.resetQueries({ predicate: (query) => query.queryKey[0] !== "me" });
    },
  });
}

/** Where the sign in button goes; the backend sends the browser on to the provider. */
export const SIGN_IN_URL = "/api/auth/login";

export function useCompanies() {
  return useQuery({
    queryKey: COMPANIES_KEY,
    queryFn: async () => {
      const list = await getJson<CompanyList>("/api/companies");
      shownCompany = list.active;
      return list;
    },
    staleTime: Infinity,
  });
}

/** Switch company, or add one; a switch reloads everything the page shows. */
export function useCompanyWrites() {
  const client = useQueryClient();
  return {
    pick: useMutation({
      mutationFn: (slug: string) => send<CompanyList>("PUT", "/api/companies/active", { slug }),
      onSuccess: async (list) => {
        shownCompany = list.active;
        client.setQueryData(COMPANIES_KEY, list);
        // Drop every other answer: each belonged to the company shown before. The brand
        // is only refetched, so the header keeps the old one until the new one arrives
        // instead of going blank.
        await Promise.all([
          client.resetQueries({ predicate: (query) => !["companies", "brand"].includes(String(query.queryKey[0])) }),
          client.invalidateQueries({ queryKey: ["brand"], exact: true }),
        ]);
      },
    }),
    create: useMutation({
      mutationFn: (input: CompanyInput) => send<CompanyList>("POST", "/api/companies", input),
      onSuccess: (list) => client.setQueryData(COMPANIES_KEY, list),
    }),
  };
}

export function useBrand() {
  return useQuery({
    queryKey: ["brand"],
    queryFn: () => getJson<Brand>("/api/brand"),
    // The brand changes when it is saved or the company switches; both refresh it.
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

/**
 * The backend refuses a write without X-CTI-Console, so other sites cannot send one, and
 * one naming a company other than the active one.
 */
function writeHeaders(contentType = "application/json"): Record<string, string> {
  return {
    "Content-Type": contentType,
    "X-CTI-Console": "1",
    ...(shownCompany ? { "X-CTI-Company": shownCompany } : {}),
  };
}

async function send<T>(method: "POST" | "PUT" | "DELETE", path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: writeHeaders(),
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

/** An image of the company's, with the brand version so a replaced one is fetched again. */
export const brandImageUrl = (kind: BrandImage, version: string | undefined): string =>
  `/api/brand/assets/${kind}${version ? `?v=${version}` : ""}`;

/**
 * The console colours and contrast checks a draft gives. Sent only for a complete
 * draft; the last answer stays on screen while the next one is worked out.
 */
export function useBrandPreview(draft: BrandInput | null) {
  return useQuery({
    queryKey: ["brand-preview", draft],
    queryFn: () => send<BrandPreview>("POST", "/api/brand/preview", draft),
    enabled: draft !== null,
    placeholderData: keepPreviousData,
    staleTime: Infinity,
  });
}

/** Save the names and colours, or replace an image; the whole page then shows the result. */
export function useBrandWrites() {
  const client = useQueryClient();
  const refresh = (brand: Brand) => client.setQueryData(["brand"], brand);
  return {
    save: useMutation({
      mutationFn: (input: BrandInput) => send<Brand>("PUT", "/api/brand", input),
      onSuccess: refresh,
    }),
    upload: useMutation({
      mutationFn: async ({ kind, file }: { kind: BrandImage; file: Blob }) => {
        const response = await fetch(`/api/brand/assets/${kind}`, {
          method: "PUT",
          headers: writeHeaders("image/png"),
          body: file,
        });
        if (!response.ok) {
          const detail = await response.json().catch(() => null);
          throw new ApiError(saveProblem(response.status, detail), response.status);
        }
        return (await response.json()) as Brand;
      },
      onSuccess: refresh,
    }),
  };
}
