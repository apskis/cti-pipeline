import clsx from "clsx";
import { Building2 } from "lucide-react";

import { useCompanies, useCompanyWrites } from "../api/client";
import { useAccess } from "../lib/access";
import { settingsHref } from "../lib/route";

/**
 * Which company the console shows. Switching reloads every page's data for that company.
 * Stacked puts the label over a full width select, for the sidebar.
 */
export const CompanyPicker = ({ stacked = false }: { stacked?: boolean }) => {
  const { data } = useCompanies();
  const { pick } = useCompanyWrites();
  const { canManage } = useAccess();
  if (!data) return null;
  return (
    <div className={clsx("flex flex-wrap gap-2 text-xs", stacked ? "flex-col items-stretch" : "items-center")}>
      <label className={clsx("gap-1.5", stacked ? "flex flex-col" : "inline-flex items-center")}>
        <span className="inline-flex items-center gap-1.5">
          <Building2 aria-hidden size={14} className="text-muted" />
          <span className={clsx("text-muted", stacked && "font-medium tracking-wide uppercase")}>Company</span>
        </span>
        <select
          value={data.active}
          disabled={pick.isPending}
          onChange={(e) => pick.mutate(e.target.value)}
          className={clsx(
            "rounded-md border border-line bg-surface text-ink",
            stacked ? "w-full px-2.5 py-2 text-sm" : "px-2 py-1 text-xs",
          )}
        >
          {data.companies.map((c) => (
            <option key={c.slug} value={c.slug}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
      {canManage && (
        <a href={settingsHref("companies")} className="text-muted underline hover:text-ink">
          Add or copy
        </a>
      )}
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
  const { canManage } = useAccess();
  const shown = data?.companies.find((c) => c.slug === data.active);
  // How to start a run is for whoever runs the pipeline, not for a company's own people.
  if (!shown || shown.has_runs || !canManage) return null;
  return (
    <p role="note" className="mb-4 rounded-md border border-line bg-raised px-3 py-2 text-sm text-muted">
      {shown.name} has no pipeline runs yet. Fill in what the pipeline should watch in{" "}
      <code>data/companies/{shown.slug}/profile.json</code> and its <code>reference</code> notes, then
      run <code>COMPANY={shown.slug} scripts/run-local.sh bulletin-scan</code>.
    </p>
  );
};
