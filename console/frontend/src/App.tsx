import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import clsx from "clsx";
import { useState } from "react";

import { useRoute } from "./lib/route";
import OverviewPage from "./pages/OverviewPage";
import ReportsPage from "./pages/ReportsPage";

const TABS = [
  { page: "overview", label: "Overview", href: "#/" },
  { page: "reports", label: "Reports", href: "#/reports" },
] as const;

const App = () => {
  // One client per mount, so tests never share a cache.
  const [client] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } }),
  );
  const route = useRoute();
  return (
    <QueryClientProvider client={client}>
      <div className="mx-auto max-w-6xl px-4 py-6 md:px-8">
        <header className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <h1 className="text-xl font-medium">GeneLabs CTI pipeline</h1>
          <p className="text-sm text-muted">Local and read only. Nothing here changes the pipeline.</p>
        </header>
        <nav aria-label="Pages" className="mb-6 flex gap-1 border-b border-line">
          {TABS.map((tab) => (
            <a
              key={tab.page}
              href={tab.href}
              aria-current={route.page === tab.page ? "page" : undefined}
              className={clsx(
                "-mb-px border-b-2 px-3 py-2 text-sm",
                route.page === tab.page
                  ? "border-ink font-medium"
                  : "border-transparent text-muted hover:text-ink",
              )}
            >
              {tab.label}
            </a>
          ))}
        </nav>
        <main>
          {route.page === "reports" ? <ReportsPage selected={route.id} /> : <OverviewPage />}
        </main>
      </div>
    </QueryClientProvider>
  );
};

export default App;
