import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import OverviewPage from "./pages/OverviewPage";

const App = () => {
  // One client per mount, so tests never share a cache.
  const [client] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } }),
  );
  return (
    <QueryClientProvider client={client}>
      <div className="mx-auto max-w-6xl px-4 py-6 md:px-8">
        <header className="mb-6 flex flex-wrap items-baseline justify-between gap-2">
          <h1 className="text-xl font-medium">GeneLabs CTI pipeline</h1>
          <p className="text-sm text-muted">Local and read only. Nothing here changes the pipeline.</p>
        </header>
        <main>
          <OverviewPage />
        </main>
      </div>
    </QueryClientProvider>
  );
};

export default App;
