# CTI console

A local, read only view of what the pipeline produced: runs, stages, costs and every
deliverable. It reads `out/` and `logs/`, never writes to them, and makes no model calls.
It is not part of the pipeline image (`.dockerignore` leaves `console/` out).

Status: the backend API, the overview page and the report reader are in place. Run
detail and the CVE table come next.

## Run it

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

The overview page shows the headline numbers, how the last scan ran (six stages, each
with a status word as well as a colour) and the model cost per day. If the backend is
not running it says how to start it and offers a retry.

The Reports page lists every deliverable, filtered by kind, status and a search on ID or
title. Picking one opens it in the reader, rendered from its `.docx`, with a button to
download the original. A report has its own link, such as `#/reports/CTI26-137`, for a
demo script or a bookmark.

### Showing documents safely

Report HTML is built from documents full of links and text the pipeline copied from the
web, so it is treated as hostile:

- The front end runs it through DOMPurify, keeping plain document markup only. Scripts,
  event handlers, styles and frames are removed. Links open in a new tab with no access
  to the page, and only images embedded in the document may load.
- A Content Security Policy, set in `vite.config.ts`, lets the page load nothing from
  anywhere but itself. `npm run preview` serves the built page with the strict policy.
  `npm run dev` relaxes it just enough for Vite's inline refresh script and styles.
- The API sends `default-src 'none'` on every answer, so nothing it returns can run.

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

### Endpoints (GET only)

| Path | Returns |
|---|---|
| `/api/health` | `{"status": "ok"}` |
| `/api/summary` | Counts per kind, CVEs tracked, total model cost, the last scan run and its six stages |
| `/api/runs?component=&limit=` | Runs, newest first, each with its sessions and cost |
| `/api/deliverables?kind=&status=&q=&limit=` | One entry per ID: kind, title, path under `out/`, first seen, status |
| `/api/deliverables/{id}/html` | The same entry plus the document as HTML, made with mammoth |
| `/api/deliverables/{id}/file` | The original `.docx`, as a download |

An ID must look like one (letters, digits and hyphens), and the file must sit inside
`out/`, or the answer is 404. A bold paragraph on its own outside a table becomes a
heading in the HTML, because the pipeline writes its headings that way.

### Where the numbers come from

- **Runs and cost:** every `out/*/state/cost-log.jsonl`. A run is inferred: a scan
  session starts one, and a gap of more than 30 minutes between sessions starts another.
  Cost is what the sessions would cost at API prices; on a Claude plan it is not billed.
- **Deliverables:** every `.docx` under `out/` outside `state/`, identified with the ID
  patterns in `scripts/update_state.py`. The newest copy of an ID wins.
- **Broken or not:** `shell_reason` from `scripts/pending_deliverables.py`, on the kinds
  the pipeline checks (bulletins, hunts, awareness posts). Other kinds show `unchecked`.
- **Stages:** the run's log in `logs/`, its `reports/scan-<date>.md` and the dedup log.
  When a source is missing or silent the stage says `unknown`, never a guess.

### Tests

```
cd console/backend
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check .
```

The tests build a small sample `out/` and `logs/` tree, so they do not need real output.
