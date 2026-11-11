# CTI console

A local, read only view of what the pipeline produced: runs, stages, costs and every
deliverable. It reads `out/` and `logs/`, never writes to them, and makes no model calls.
It is not part of the pipeline image (`.dockerignore` leaves `console/` out).

## Run it

One command from the repo root, in Windows PowerShell:

```
.\scripts\console.ps1
```

It starts the backend on `127.0.0.1:8765` and the built page on `127.0.0.1:5173`, with
the strict Content Security Policy, then opens the browser. Ctrl+C stops both. The first
start installs the front end's packages and builds the page; the backend needs its Python
environment already (see Backend below).

| Option | Does |
|---|---|
| `-Build` | Rebuild the page first, after a `git pull` |
| `-Dev` | Use the Vite dev server instead, which reloads on edits |
| `-Out <dir>` and `-Logs <dir>` | Read another copy of the output, such as `D:\projects\cti-pipeline\out` from a worktree |
| `-NoBrowser` | Do not open the browser |

A backend already running on port 8765 is reused, and keeps the folders it started with.

### A five minute demo

1. **Overview.** The headline numbers, then the six stages of the last scan: where the
   feeds came from, what Claude ranked, what got an ID, what was built and checked.
2. **Start here.** Open the latest bulletin, then its hunt package. Each opens on its
   **Branded** view: the real document as Word lays it out, banner and footer included,
   with buttons to download the `.docx` or the PDF. **Text** shows the same report as
   plain page text.
3. **Runs.** Open the last bulletin scan: its sessions, what each cost, the documents it
   saved and the scan report it left.
4. **CVEs.** Tick "Exploited only" and "On CISA KEV" to show the CVEs that need action
   now, with the deadlines that have passed marked.

### By hand

Two terminals. Start the backend first, then the front end, then open
`http://127.0.0.1:5173`.

```
cd console/backend
.venv\Scripts\python -m cti_console
```

```
cd console/frontend
npm install
npm run dev
```

## Front end

React 18 with TypeScript, built with Vite, styled with Tailwind v4, data through
TanStack Query, the chart through Chart.js. Vite proxies `/api` to the backend on
`127.0.0.1:8765`, so the browser only ever talks to one origin.

The overview page shows the headline numbers, a "Start here" row, how the last scan ran
(six stages, each with a status word as well as a colour) and the model cost per day.
"Start here" links the newest bulletin, hunt package, CVE brief and weekly report that
are not broken, so a demo opens on a working document. If the backend is not running the
page says how to start it and offers a retry. With no output at all it says how to make
some, and every list says so when it is empty.

The Reports page lists every deliverable, filtered by kind, status and a search on ID or
title. Picking one opens it in the reader, rendered from its `.docx`, with a button to
download the original. A report has its own link, such as `#/reports/CTI26-137`, for a
demo script or a bookmark.

The Runs page lists every run, newest first. Picking one shows its sessions with time,
turns and cost, the six stages for a bulletin scan, the documents saved while it ran
(each a link into the reader) and the run report the component left, such as
`reports/scan-<date>.md`. A run has its own link, such as
`#/runs/bulletin-scan-20261110T145714`.

The CVEs page is the CVE register as a table: newest first, then highest CVSS. It can
narrow to exploited CVEs or those on CISA KEV, and a KEV deadline that has passed is
marked. Bulletin and hunt IDs link into the reader.

### Showing documents safely

Report HTML, from a `.docx` or a run report in Markdown, is built from text the pipeline
copied from the web, so it is treated as hostile:

- The front end runs it through DOMPurify, keeping plain document markup only. Scripts,
  event handlers, styles and frames are removed. Links open in a new tab with no access
  to the page, and only images embedded in the document may load.
- A Content Security Policy, set in `vite.config.ts`, lets the page load nothing from
  anywhere but itself. `npm run preview` serves the built page with the strict policy.
  `npm run dev` relaxes it just enough for Vite's inline refresh script and styles.
- Markdown run reports are rendered with raw HTML switched off, so any HTML in them
  arrives as plain text, and then go through DOMPurify like the rest.
- The API sends `default-src 'none'` on every answer, so nothing it returns can run.
  Only the branded PDF may be framed, and only by the console's own page
  (`frame-ancestors 'self'`). The page allows frames from itself and no plugins.

| Command | Does |
|---|---|
| `npm run dev` | Dev server on `127.0.0.1:5173` |
| `npm run preview` | The built page on `127.0.0.1:5173`, with the strict policy |
| `npm test` | Vitest |
| `npm run typecheck` | TypeScript, no output |
| `npm run lint` | ESLint |
| `npm run build` | Production build into `dist/` |

## Backend

Python 3.11 or later. The repo standard is `uv`:

```
cd console/backend
uv sync --extra dev
uv run python -m cti_console
```

Without `uv`, a plain virtual environment works too:

```
cd console/backend
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m cti_console
```

The API listens on `http://127.0.0.1:8765`, on this machine only. That is fixed on
purpose: the output is internal threat intelligence and the API has no login.

| Setting | Default | Use |
|---|---|---|
| `CTI_CONSOLE_PORT` | `8765` | Port |
| `CTI_CONSOLE_OUT` | `<repo>/out` | Pipeline output to read |
| `CTI_CONSOLE_LOGS` | `<repo>/logs` | Run logs to read |
| `CTI_CONSOLE_CACHE` | `<repo>/console/.cache` | Branded PDFs the console made (gitignored) |

### Branded PDFs

The Branded view is a PDF made by Microsoft Word, so it matches the document exactly.
It needs Windows with Word installed; without Word the reader shows the Text view only
and offers no PDF download.

- **One hidden Word.** The backend keeps one Word open on a worker thread and closes it
  after 15 quiet minutes. Word's first export in a session is slow (close to a minute
  on a machine whose default printer is a network printer), so the backend pays it at
  start up, in the background. After that a report takes about a second.
- **Cached.** Each PDF is made once and kept under `CTI_CONSOLE_CACHE`. A rebuilt report
  gets a fresh PDF the next time it is opened, and the old one is removed.
- **Never your Word.** The backend starts its own Word for automation and never touches
  a Word window you have open. Windows closes that Word when the backend exits, even
  when it is killed, and the launcher checks again on the way out.
- **Read only.** Word opens each `.docx` read only and never saves it. `out/` is not
  written to.

### Endpoints (GET only)

| Path | Returns |
|---|---|
| `/api/health` | `{"status": "ok"}` |
| `/api/summary` | Counts per kind, CVEs tracked, total model cost, the last scan run and its six stages |
| `/api/runs?component=&limit=` | Runs, newest first, each with its sessions and cost |
| `/api/runs/{id}` | One run: its sessions, stages, documents saved while it ran, and its run report as HTML |
| `/api/cves` | The CVE register's rows, without the SPL and CQL columns |
| `/api/deliverables?kind=&status=&q=&limit=` | One entry per ID: kind, title, path under `out/`, first seen, status |
| `/api/deliverables/{id}/html` | The same entry plus the document as HTML, made with mammoth, and `pdf`: whether Word can make the branded PDF |
| `/api/deliverables/{id}/file` | The original `.docx`, as a download |
| `/api/deliverables/{id}/pdf/ready` | Makes the branded PDF if it is not cached yet; the page calls it to show progress |
| `/api/deliverables/{id}/pdf?download=` | The branded PDF, shown in the page, or as a download with `download=true` |

An ID must look like one (letters, digits and hyphens; a run ID is the component and its
start time), and the file must sit inside `out/`, or the answer is 404. A bold paragraph on its own outside a table becomes a
heading in the HTML, because the pipeline writes its headings that way.

### Where the numbers come from

- **Runs and cost:** every `out/*/state/cost-log.jsonl`. A run is inferred: a scan
  session starts one, and a gap of more than 30 minutes between sessions starts another.
  Cost is what the sessions would cost at API prices; on a Claude plan it is not billed.
- **Deliverables:** every `.docx` under `out/` outside `state/`, identified with the ID
  patterns in `scripts/update_state.py`. The newest copy of an ID wins.
- **Broken or not:** `shell_reason` from `scripts/pending_deliverables.py`, on the kinds
  the pipeline checks (bulletins, hunts, awareness posts). Other kinds show `unchecked`.
- **Documents saved during a run:** files of that component whose modification time falls
  between the run's start and five minutes after its end. A later rebuild saves files
  again, so an older run can show fewer than it once wrote; the page says so.
- **CVEs:** the newest `CVE_Register_*.xlsx`, sheet `CVE Register`, read only. "Exploited"
  is read from the register's free text exploitation status. A bulletin or hunt cell is
  linked only when it holds a real ID, because a few older rows are shifted a column.
- **Stages:** the run's log in `logs/`, its `reports/scan-<date>.md` and the dedup log.
  When a source is missing or silent the stage says `unknown`, never a guess.

### Tests

```
cd console/backend
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check .
```

The tests build a small sample `out/` and `logs/` tree, so they do not need real output.
