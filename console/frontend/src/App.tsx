import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import clsx from "clsx";
import { useState } from "react";

import { ApiError, useCompanies, useMe } from "./api/client";
import { Account, NoCompany, SignIn } from "./components/Account";
import { BrandLockup, ThemeSwitch } from "./components/Brand";
import { CompanyPicker, NoRunsNote } from "./components/CompanyPicker";
import { type Route, useRoute } from "./lib/route";
import { ThemeProvider } from "./lib/theme";
import BuiltPage from "./pages/BuiltPage";
import CvesPage from "./pages/CvesPage";
import OverviewPage from "./pages/OverviewPage";
import ReportsPage from "./pages/ReportsPage";
import RunsPage from "./pages/RunsPage";
import SettingsPage from "./pages/SettingsPage";
import StakeholdersPage from "./pages/StakeholdersPage";

const TABS = [
  { page: "overview", label: "Overview", href: "#/" },
  { page: "reports", label: "Reports", href: "#/reports" },
  { page: "runs", label: "Runs", href: "#/runs" },
  { page: "cves", label: "CVEs", href: "#/cves" },
  { page: "stakeholders", label: "Stakeholders", href: "#/stakeholders" },
  { page: "built", label: "How it's built", href: "#/built" },
  { page: "settings", label: "Settings", href: "#/settings/branding" },
] as const;

const Page = ({ route }: { route: Route }) => {
  switch (route.page) {
    case "reports":
      return <ReportsPage selected={route.id} />;
    case "runs":
      return <RunsPage selected={route.id} />;
    case "cves":
      return <CvesPage />;
    case "stakeholders":
      return <StakeholdersPage selected={route.id} />;
    case "built":
      return <BuiltPage />;
    case "settings":
      return <SettingsPage section={route.section} />;
    default:
      return <OverviewPage />;
  }
};

/** The console, once it is known who is using it and that they have a company. */
const Console = () => {
  const route = useRoute();
  const me = useMe();
  const companies = useCompanies();
  // The page draws at once; only signed out and no company stop it. Until /api/me answers,
  // buttons that need a role stay hidden rather than appearing and vanishing.
  if (me.error instanceof ApiError && me.error.status === 401) return <SignIn />;
  if (companies.data?.active === "") return <NoCompany />;
  const local = me.data?.auth !== "oidc";
  return (
        <div className="mx-auto max-w-6xl px-4 py-6 md:px-8">
          <header className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b-[3px] border-accent pb-4">
            <BrandLockup />
            <div className="flex flex-col items-start gap-2 sm:items-end">
              <div className="flex flex-wrap items-center gap-3 sm:justify-end">
                <CompanyPicker />
                <ThemeSwitch />
                <Account />
              </div>
              <p className="text-xs text-muted">
                {local ? "Local only. " : ""}Nothing here changes the pipeline; only companies, their branding and
                stakeholders are saved.
              </p>
            </div>
          </header>
          <nav aria-label="Pages" className="mb-6 flex gap-1 overflow-x-auto [scrollbar-width:none] shadow-[inset_0_-1px_0_var(--color-line)]">
            {TABS.map((tab) => (
              <a
                key={tab.page}
                href={tab.href}
                aria-current={route.page === tab.page ? "page" : undefined}
                className={clsx(
                  "shrink-0 border-b-2 px-3 py-2 text-sm",
                  route.page === tab.page
                    ? "border-accent font-medium text-brand"
                    : "border-transparent text-muted hover:text-ink",
                )}
              >
                {tab.label}
              </a>
            ))}
          </nav>
          <main>
            <NoRunsNote />
            <Page route={route} />
          </main>
        </div>
  );
};

const App = () => {
  // One client per mount, so tests never share a cache.
  const [client] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } }),
  );
  return (
    <ThemeProvider>
      <QueryClientProvider client={client}>
        <Console />
      </QueryClientProvider>
    </ThemeProvider>
  );
};

export default App;
