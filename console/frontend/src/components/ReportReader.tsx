import { Download } from "lucide-react";
import { useMemo } from "react";

import { fileUrl, useDeliverableDocument } from "../api/client";
import { formatDay } from "../lib/format";
import { kindLabel } from "../lib/kinds";
import { sanitizeReport } from "../lib/sanitize";
import DocStatus from "./DocStatus";

/** One deliverable, rendered from its .docx, with a download of the original. */
const ReportReader = ({ id }: { id: string | null }) => {
  const doc = useDeliverableDocument(id);
  const html = useMemo(() => (doc.data ? sanitizeReport(doc.data.html) : ""), [doc.data]);

  if (id === null) {
    return <p className="py-16 text-center text-muted">Pick a report from the list to read it here.</p>;
  }
  if (doc.error) {
    return (
      <p className="py-16 text-center text-muted" role="alert">
        Could not open {id}. {doc.error.message}
      </p>
    );
  }
  if (!doc.data) {
    return (
      <p className="py-16 text-center text-muted" role="status">
        Opening {id}.
      </p>
    );
  }

  const d = doc.data;
  return (
    <article aria-labelledby="reader-title">
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3 border-b border-line pb-4">
        <div className="min-w-0">
          <p className="text-xs text-muted">
            {d.id} · {kindLabel(d.kind)} · first seen {formatDay(d.first_seen)}
          </p>
          <h2 id="reader-title" className="mt-1 text-lg font-medium">
            {d.title}
          </h2>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
            <DocStatus status={d.status} />
            {d.problem && <span className="text-fail-ink">{d.problem}</span>}
          </div>
        </div>
        <a
          href={fileUrl(d.id)}
          download
          className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm hover:bg-raised"
        >
          <Download aria-hidden size={16} />
          Download .docx
        </a>
      </header>
      {/* Safe to inject: sanitizeReport keeps plain document markup only. */}
      <div className="report" dangerouslySetInnerHTML={{ __html: html }} />
    </article>
  );
};

export default ReportReader;
