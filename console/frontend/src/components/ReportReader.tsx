import { Download, FileText, LoaderCircle } from "lucide-react";
import { useMemo, useState } from "react";

import { fileUrl, pdfUrl, useDeliverableDocument, usePdfReady } from "../api/client";
import { kindAgents } from "../lib/agents";
import { formatDay } from "../lib/format";
import { kindLabel } from "../lib/kinds";
import { sanitizeReport } from "../lib/sanitize";
import DocStatus from "./DocStatus";
import IntendedFor from "./IntendedFor";

type View = "branded" | "text";

const LINK_BUTTON =
  "inline-flex shrink-0 items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm hover:bg-raised";

/** The report exactly as Word lays it out, made into a PDF by the backend and framed. */
const BrandedPdf = ({ id, onShowText }: { id: string; onShowText: () => void }) => {
  const ready = usePdfReady(id, true);

  if (ready.error) {
    return (
      <div className="py-16 text-center text-muted" role="alert">
        <p>Could not make the branded PDF. {ready.error.message}</p>
        <button type="button" onClick={onShowText} className={`${LINK_BUTTON} mt-4`}>
          Show the text view
        </button>
      </div>
    );
  }
  if (!ready.data) {
    return (
      <div className="flex flex-col items-center gap-2 py-16 text-center text-muted" role="status">
        <LoaderCircle aria-hidden size={20} className="animate-spin motion-reduce:animate-none" />
        <p>Making the branded PDF with Word.</p>
        <p className="text-xs">
          This takes a second or two, but up to a minute when Word has just started: after the
          console starts or after hours without a PDF.
        </p>
        <button type="button" onClick={onShowText} className={`${LINK_BUTTON} mt-2`}>
          Read the text instead
        </button>
      </div>
    );
  }
  return (
    <iframe
      title={`${id}, branded PDF`}
      src={`${pdfUrl(id)}#view=FitH`}
      className="h-[80vh] w-full rounded-md border border-line bg-white"
    />
  );
};

/** One deliverable: its branded PDF or a text rendering, with downloads of both files. */
const ReportReader = ({ id }: { id: string | null }) => {
  const doc = useDeliverableDocument(id);
  const html = useMemo(() => (doc.data ? sanitizeReport(doc.data.html) : ""), [doc.data]);
  // Remembered per report, so moving to another report starts on its branded view again.
  const [chosen, setChosen] = useState<{ id: string | null; view: View }>({ id, view: "branded" });
  const picked: View = chosen.id === id ? chosen.view : "branded";

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
  const view: View = d.pdf ? picked : "text";
  const show = (next: View) => setChosen({ id, view: next });
  return (
    <article aria-labelledby="reader-title">
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3 border-b border-line pb-4">
        <div className="min-w-0">
          <p className="text-xs text-muted">
            {d.id} · {kindLabel(d.kind)} · first seen {formatDay(d.first_seen)} · {kindAgents(d.kind)}
          </p>
          <h2 id="reader-title" className="mt-1 text-lg font-medium">
            {d.title}
          </h2>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
            <DocStatus status={d.status} />
            {d.problem && <span className="text-fail-ink">{d.problem}</span>}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <a href={fileUrl(d.id)} download className={LINK_BUTTON}>
            <Download aria-hidden size={16} />
            Download .docx
          </a>
          {d.pdf && (
            <a href={pdfUrl(d.id, true)} download className={LINK_BUTTON}>
              <FileText aria-hidden size={16} />
              Download .pdf
            </a>
          )}
        </div>
      </header>
      <IntendedFor reportId={d.id} kind={d.kind} />
      {d.pdf && (
        <div role="group" aria-label="How to show the report" className="mb-4 inline-flex rounded-md border border-line p-0.5 text-sm">
          {(
            [
              ["branded", "Branded"],
              ["text", "Text"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              aria-pressed={view === value}
              onClick={() => show(value)}
              className={`rounded px-3 py-1 ${view === value ? "bg-raised font-medium" : "text-muted hover:text-ink"}`}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      {view === "branded" ? (
        <BrandedPdf id={d.id} onShowText={() => show("text")} />
      ) : (
        /* Safe to inject: sanitizeReport keeps plain document markup only. */
        <div className="report" dangerouslySetInnerHTML={{ __html: html }} />
      )}
    </article>
  );
};

export default ReportReader;
