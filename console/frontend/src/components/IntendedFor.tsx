import { Check, Copy, UserPlus } from "lucide-react";
import { useMemo, useState } from "react";

import { useAudience, useStakeholders } from "../api/client";
import { kindLabel } from "../lib/kinds";
import { newStakeholderHref, stakeholderHref } from "../lib/route";
import { distributionList, recipientsFor } from "../lib/stakeholders";

const Person = ({ id, name }: { id: string; name: string }) => (
  <a href={stakeholderHref(id)} className="rounded bg-raised px-1.5 py-0.5 text-xs hover:underline">
    {name}
  </a>
);

/**
 * Who this report is for: the teams it names, matched to the stakeholder list, and the
 * people who get every report of its kind. Gaps link to the add form for that team.
 */
const IntendedFor = ({ reportId, kind }: { reportId: string; kind: string }) => {
  const list = useStakeholders();
  const audience = useAudience();
  const [copied, setCopied] = useState(false);
  const people = list.data?.stakeholders;
  const recipients = useMemo(
    () => recipientsFor(reportId, kind, audience.data, people ?? []),
    [reportId, kind, audience.data, people],
  );

  if (!people || !audience.data) return null;
  const { teams, byKind, everyone } = recipients;
  if (teams.length === 0 && byKind.length === 0) {
    return (
      <p className="mb-4 text-sm text-muted">
        Intended for: this report names no teams, and nobody on the{" "}
        <a href={stakeholderHref(null)} className="underline">
          stakeholder list
        </a>{" "}
        gets all {kindLabel(kind).toLowerCase()}.
      </p>
    );
  }

  const emails = distributionList(everyone);
  const copy = () => {
    void navigator.clipboard?.writeText(emails).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <section aria-labelledby="intended-title" className="mb-4 rounded-md border border-line p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id="intended-title" className="font-medium">
          Intended for
        </h3>
        {emails && (
          <button
            type="button"
            onClick={copy}
            className="inline-flex items-center gap-1.5 rounded-md border border-line px-2 py-1 text-xs hover:bg-raised"
          >
            {copied ? <Check aria-hidden size={14} /> : <Copy aria-hidden size={14} />}
            {copied ? "Copied" : `Copy ${everyone.filter((p) => p.email).length} addresses`}
          </button>
        )}
      </div>
      <ul className="mt-2 flex flex-col gap-1.5">
        {teams.map((team) => (
          <li key={team.name} className="flex flex-wrap items-center gap-1.5">
            <span className="text-muted">
              {team.name}
              {team.questions.length > 0 &&
                ` · ${team.questions.length} ${team.questions.length === 1 ? "question" : "questions"}`}
              :
            </span>
            {team.people.length > 0 ? (
              team.people.map((p) => <Person key={p.id} id={p.id} name={p.name} />)
            ) : (
              <a
                href={newStakeholderHref(team.name)}
                className="inline-flex items-center gap-1 text-xs text-warn-ink underline"
              >
                <UserPlus aria-hidden size={14} />
                Nobody on file, add
              </a>
            )}
          </li>
        ))}
        {byKind.length > 0 && (
          <li className="flex flex-wrap items-center gap-1.5">
            <span className="text-muted">Gets all {kindLabel(kind).toLowerCase()}:</span>
            {byKind.map((p) => (
              <Person key={p.id} id={p.id} name={p.name} />
            ))}
          </li>
        )}
      </ul>
    </section>
  );
};

export default IntendedFor;
