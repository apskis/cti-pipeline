import clsx from "clsx";
import { ShieldAlert, ShieldCheck } from "lucide-react";

import type { Review } from "../api/types";
import { REVIEWER } from "../lib/agents";
import { formatDay } from "../lib/format";

// The kinds the Reviewer reads. A CVE brief is a table rendered by code from the register.
const REVIEWED_KINDS = new Set(["bulletin", "hunt", "awareness"]);

/** Only web links become clickable: the Reviewer is a model and its text is untrusted. */
const isWebLink = (value: string): boolean => /^https?:\/\//i.test(value);

const Source = ({ value }: { value: string }) =>
  isWebLink(value) ? (
    <a href={value} target="_blank" rel="noreferrer noopener" className="break-all underline">
      {value}
    </a>
  ) : (
    <span className="break-words">{value}</span>
  );

/** The Reviewer's verdict on one document, with its findings when it flagged something. */
const ReviewNote = ({ kind, review }: { kind: string; review: Review | null }) => {
  if (!REVIEWED_KINDS.has(kind)) return null;
  if (!review) {
    return <p className="mb-4 text-xs text-muted">Not checked by the {REVIEWER} yet.</p>;
  }
  const flagged = review.verdict === "flag";
  const Icon = flagged ? ShieldAlert : ShieldCheck;
  const when = review.checked_at ? ` on ${formatDay(review.checked_at.slice(0, 10))}` : "";
  return (
    <section
      aria-label={`${REVIEWER} verdict`}
      className={clsx(
        "mb-4 rounded-xl border p-4 text-sm",
        flagged ? "border-warn-ink/30 bg-warn-bg text-warn-ink" : "border-line bg-surface",
      )}
    >
      <p className="flex items-center gap-1.5 font-medium">
        <Icon aria-hidden size={16} className={flagged ? undefined : "text-ok-ink"} />
        {flagged ? `Flagged by the ${REVIEWER}` : `Checked by the ${REVIEWER}`}
        <span className="font-normal opacity-80">{when}</span>
      </p>
      {review.summary && <p className="mt-1">{review.summary}</p>}
      {review.stale && (
        <p className="mt-1 text-xs opacity-80">
          The document changed after this review. The next run checks it again.
        </p>
      )}
      {review.findings.length > 0 && (
        <ol className="mt-3 list-decimal space-y-2 pl-5">
          {review.findings.map((f, i) => (
            <li key={i}>
              {f.claim && <p className="italic">"{f.claim}"</p>}
              <p>{f.problem}</p>
              {f.source && (
                <p className="text-xs opacity-80">
                  Source: <Source value={f.source} />
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
};

export default ReviewNote;
