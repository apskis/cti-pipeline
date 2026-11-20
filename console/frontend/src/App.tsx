import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Info } from "lucide-react";
import { useState } from "react";

import { ApiError, useCompanies, useMe } from "./api/client";
import { Account, NoCompany, SignIn, ViewAsBanner, ViewAsSwitch } from "./components/Account";
import { ThemeSwitch } from "./components/Brand";
import { NoRunsNote } from "./components/CompanyPicker";
import Sidebar, { pageLabel } from "./components/Sidebar";
import { type Route, useRoute } from "./lib/route";
import { ThemeProvider } from "./lib/theme";
import BuiltPage from "./pages/BuiltPage";
import CvesPage from "./pages/CvesPage";
import OverviewPage from "./pages/OverviewPage";
import ReportsPage from "./pages/ReportsPage";
import RunsPage from "./pages/RunsPage";
import SettingsPage from "./pages/SettingsPage";
import StakeholdersPage from "./pages/StakeholdersPage";

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
    <div className="md:flex md:min-h-screen">
      <Sidebar current={route.page} />
      <div className="min-w-0 flex-1">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-4 md:px-8">
          <div className="leading-tight">
            <p className="text-xs text-faint">Console</p>
            <h2 className="text-xl font-semibold tracking-tight text-brand">{pageLabel(route.page)}</h2>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <ViewAsSwitch />
            <ThemeSwitch />
            <Account />
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6 md:px-8">
          <p className="mb-6 flex items-start gap-2 rounded-lg border border-line bg-surface px-4 py-3 text-sm text-muted">
            <Info aria-hidden size={16} className="mt-0.5 shrink-0 text-accent" />
            <span>
              {local && <strong className="font-medium text-ink">Local only. </strong>}
              Nothing here changes the pipeline; only companies, their branding and stakeholders are saved.
            </span>
          </p>
          <ViewAsBanner />
          <NoRunsNote />
          <Page route={route} />
        </main>
      </div>
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
