# CTI console

A local, read only view of what the pipeline produced: runs, stages, costs and every
deliverable. It reads `out/` and `logs/`, never writes to them, and makes no model calls.
It is not part of the pipeline image (`.dockerignore` leaves `console/` out).

Status: the backend API and the overview page are in place. The report reader, run
detail and CVE table come next.

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

| Command | Does |
|---|---|
| `npm run dev` | Dev server on `127.0.0.1:5173` |
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
