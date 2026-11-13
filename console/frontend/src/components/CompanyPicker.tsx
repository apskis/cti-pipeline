import { Building2 } from "lucide-react";

import { useCompanies, useCompanyWrites } from "../api/client";
import { settingsHref } from "../lib/route";

/** Which company the console shows. Switching reloads every page's data for that company. */
export const CompanyPicker = () => {
  const { data } = useCompanies();
  const { pick } = useCompanyWrites();
  if (!data) return null;
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <label className="inline-flex items-center gap-1.5">
        <Building2 aria-hidden size={14} className="text-muted" />
        <span className="text-muted">Company</span>
        <select
          value={data.active}
          disabled={pick.isPending}
          onChange={(e) => pick.mutate(e.target.value)}
          className="rounded-md border border-line bg-surface px-2 py-1 text-xs text-ink"
        >
          {data.companies.map((c) => (
            <option key={c.slug} value={c.slug}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
      <a href={settingsHref("companies")} className="text-muted underline hover:text-ink">
        Add or copy
      </a>
      {pick.isError && (
        <span role="alert" className="text-fail-ink">
          Not switched. {pick.error.message}
        </span>
      )}
    </div>
  );
};

/** Said once, under the header, until the shown company's first pipeline run. */
export const NoRunsNote = () => {
  const { data } = useCompanies();
  const shown = data?.companies.find((c) => c.slug === data.active);
  if (!shown || shown.has_runs) return null;
  return (
    <p role="note" className="mb-4 rounded-md border border-line bg-raised px-3 py-2 text-sm text-muted">
      {shown.name} has no pipeline runs yet. Fill in what the pipeline should watch in{" "}
      <code>data/companies/{shown.slug}/profile.json</code> and its <code>reference</code> notes, then
      run <code>COMPANY={shown.slug} scripts/run-local.sh bulletin-scan</code>.
    </p>
  );
};
