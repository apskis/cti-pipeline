import { useEffect, useState } from "react";

// Hash routes keep the console a static page: no server routing, and a reader link such
// as #/reports/CTI26-137 can be bookmarked or pasted into a demo script.
export type Route = { page: "overview" } | { page: "reports"; id: string | null };

export function parseRoute(hash: string): Route {
  const [page, id] = hash.replace(/^#\/?/, "").split("/");
  if (page === "reports") {
    return { page: "reports", id: id ? decodeURIComponent(id) : null };
  }
  return { page: "overview" };
}

export const reportHref = (id: string | null): string =>
  id ? `#/reports/${encodeURIComponent(id)}` : "#/reports";

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const handleChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", handleChange);
    return () => window.removeEventListener("hashchange", handleChange);
  }, []);
  return route;
}
