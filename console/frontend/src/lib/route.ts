import { useEffect, useState } from "react";

// Hash routes keep the console a static page: no server routing, and a link such as
// #/reports/CTI26-137 or #/runs/<run id> can be bookmarked or pasted into a demo script.
export type Route =
  | { page: "overview" }
  | { page: "reports"; id: string | null }
  | { page: "runs"; id: string | null }
  | { page: "cves" }
  | { page: "stakeholders"; id: string | null };

export function parseRoute(hash: string): Route {
  const [page, raw] = hash.replace(/^#\/?/, "").split("/");
  const id = raw ? decodeURIComponent(raw) : null;
  if (page === "reports" || page === "runs" || page === "stakeholders") return { page, id };
  if (page === "cves") return { page: "cves" };
  return { page: "overview" };
}

export const reportHref = (id: string | null): string =>
  id ? `#/reports/${encodeURIComponent(id)}` : "#/reports";

export const runHref = (id: string | null): string =>
  id ? `#/runs/${encodeURIComponent(id)}` : "#/runs";

export const stakeholderHref = (id: string | null): string =>
  id ? `#/stakeholders/${encodeURIComponent(id)}` : "#/stakeholders";

/** The add form, optionally with the team filled in, as in #/stakeholders/new:SOC. */
export const newStakeholderHref = (team?: string): string =>
  team ? `#/stakeholders/new:${encodeURIComponent(team)}` : "#/stakeholders/new";

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const handleChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", handleChange);
    return () => window.removeEventListener("hashchange", handleChange);
  }, []);
  return route;
}
