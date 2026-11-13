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

/** Said once, under the header, while the shown company has no pipeline of its own yet. */
export const NoPipelineNote = () => {
  const { data } = useCompanies();
  const shown = data?.companies.find((c) => c.slug === data.active);
  const pipeline = data?.companies.find((c) => c.pipeline);
  if (!shown || shown.pipeline) return null;
  return (
    <p role="note" className="mb-4 rounded-md border border-line bg-raised px-3 py-2 text-sm text-muted">
      The pipeline runs for {pipeline?.name ?? "one company"} only for now, so {shown.name} has no
      reports or runs yet. Its branding and stakeholders are its own and can be set up now.
    </p>
  );
};
