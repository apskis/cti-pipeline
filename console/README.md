# CTI console

A local view of what the pipeline produced: runs, stages, costs and every deliverable,
and who each one is for. It reads `out/` and `logs/`, never writes to them, and makes no
model calls. It saves two things, on this machine: the stakeholder list, and the company's
branding from the Settings page.
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
5. **Stakeholders.** Back on a bulletin, "Intended for" shows the teams it asks
   questions of and who on the list answers for each. Open one person to see every report
   that names their team. The panel of teams with nobody on file is the gap list.

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

### Look and theme

The console wears the brand of the company it shows, read from
`data/companies/<slug>/company.json` (see `config/companies/README.md`), the same file
the document builders use. The header shows the company's
symbol, a divider and its name as one lockup, with its program name beneath; the browser
tab is named after it.

The colour tokens in `src/index.css` hold the GeneLabs values, so the page draws in them
before the brand loads. Once `/api/brand` answers, the company's own tokens for the theme
on show are set on `<html>` over them. Tokens a company leaves out keep the
`index.css` value.

The **Settings** page's **Branding** tab changes the company's names, colours and images,
with a live preview and contrast checks; see `config/companies/README.md`.

### Companies

The console holds any number of companies and shows one at a time. Pick it from the
**Company** list in the header, or on **Settings, Companies**, which also adds a company:
blank (a neutral slate brand to fill in) or a copy of another company's branding. A new
company opens on its Branding tab.

- **Kept apart.** Each company has its own branding, stakeholders, `out/` and `logs/`
  under `data/companies/<slug>/`. Every page reads the shown company's folders only, so
  another company's report is a 404, not a leak.
- **GeneLabs reads the repo root.** GeneLabs keeps `out/`, `logs/` and
  `config/stakeholders.json` where the pipeline and scheduled runs wrote them before
  companies existed. Every other company's runs (`COMPANY=<slug>
  scripts/run-local.sh <component>`) write into its own folder. Until a company's first
  run, a note under the header says how to start one.
- **Remembered.** The choice is kept in `data/console.json` for the next start. With none
  saved, the console opens on `CTI_CONSOLE_COMPANY` (default `genelabs`).
- **A stale tab cannot write elsewhere.** Every write names the company the page shows
  (`X-CTI-Company`). If another tab has switched since, the write is refused and the page
  asks to be reloaded.
- **Only copies are made.** Adding a company never moves or removes anything. There is no
  delete yet: remove a company's folder under `data/companies/` by hand.

### Sign in and roles

By default the console is for one person on this machine, who may do everything. With
`CTI_AUTH=oidc` people sign in with Entra ID or Cognito, and roles decide what they see:

- **Platform admin** (`cti-platform-admin`): every company, and adding companies.
- **Company admin** (`cti-admin-<slug>`): that company, and changing its branding and
  stakeholders.
- **Viewer** (`cti-viewer-<slug>`): that company, read only.

Each person keeps their own shown company, the header names them and their role with a
**Sign out** button, and the page leaves out what their role cannot do. The backend
refuses it anyway. Setup for both providers is in `docs/console-sign-in.md`.

With sign in off the console is for this machine only: it refuses any request that
arrives through a proxy or tunnel (one carrying `Forwarded` or `X-Forwarded-*` headers),
because a tunnel rewrites `Host` to localhost and would otherwise get past the host check.

- **Light, dark or system.** The switch in the header is remembered in this browser.
  System follows Windows. `public/theme-init.js` applies a saved choice before the page
  draws, so it never flashes the other theme.
- **Dark mode** is Charcoal `#202C29` cards on a near black charcoal page, with Mist text.
  Emerald is lifted to `#3FB48C`,
  because the brand Emerald is too dark to read on a dark page.
- **Contrast.** Every text colour meets WCAG AA (4.5:1) on the surfaces it sits on, in both
  themes; chart colours meet 3:1 against the card, with a hairline between segments.
- **Status colours** stay red, amber and green in both themes: they carry meaning.
- **Font.** Aptos where installed (the kit names it but ships no font files), then Segoe UI.
- **Logo in dark mode.** The helix has a dark Forest strand that would vanish on the
  charcoal page, so in dark mode it sits on a small Mist tile.
- **Favicon.** The kit's favicons (ICO, 32 and 192 pixel PNG, Apple touch icon).

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
| `CTI_CONSOLE_STAKEHOLDERS` | `<repo>/config/stakeholders.json` | GeneLabs' stakeholder list (gitignored) |
| `CTI_DATA_DIR` | `<repo>/data` | Every company's folder and the remembered choice (gitignored) |
| `CTI_CONSOLE_COMPANY` | `genelabs` | The company to open with when none has been picked |
| `CTI_AUTH` | `off` | `oidc` turns on sign in; its other settings are in `docs/console-sign-in.md` |

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

### Stakeholders

The list of who the intelligence is for: name, role, team, other names the team goes by,
email, preferred channel, the report kinds they get all of, interests and notes.

- **Where it lives.** `config/stakeholders.json` (`CTI_CONSOLE_STAKEHOLDERS`). It holds
  names and email addresses, so it is gitignored. `config/stakeholders.example.json` is a
  made up GeneLabs list, committed; on a first start the page offers to copy it in.
- **Who a report is for.** The console reads the build specs the pipeline leaves under
  `out/`. A bulletin spec names teams in its audience line and on each question for the
  reader. Each name is matched, ignoring case, punctuation and a trailing "team", to a
  stakeholder's team or any of their other names; "DevOps / Platform Engineering" matches
  either part. People who get all reports of a kind are listed too.
- **Gaps.** Teams the reports name that nobody covers are listed, most named first, each
  with a link to add someone for that team.
- **Nothing is sent.** The reader has a button that copies the addresses for a report,
  ready to paste. The console sends no email or message.
- **Saving safely.** One save at a time; each writes a new file and swaps it in, and the
  previous list is kept as `stakeholders.json.bak`. A list that cannot be read is never
  overwritten.
- **Only the console may write.** Each write needs an `X-CTI-Console` header. Another
  site's page cannot send that header without a CORS preflight, which the API refuses.
  Any `Origin` must be the console's own, and the API answers only to the hosts
  `127.0.0.1` and `localhost`, which stops DNS rebinding.

### Endpoints

Everything is GET except the stakeholder writes.

| Path | Returns |
|---|---|
| `/api/health` | `{"status": "ok"}` |
| `/api/me` | Who is using the console, their roles, and whether sign in is on |
| `/api/auth/login`, `/api/auth/callback` | Sign in at the provider and back (`CTI_AUTH=oidc` only) |
| `POST /api/auth/logout` | Sign out; answers the provider's sign out page to go to |
| `/api/companies` | The companies this person may see, and which one is shown to them |
| `PUT /api/companies/active` | Show another company; remembered for the next start |
| `POST /api/companies` | Add a company, blank or copying another's branding |
| `/api/brand` | The company's name, legal name, program and console colour tokens for light and dark |
| `/api/brand/assets/{logo,banner,symbol}` | One of the company's images, a PNG from its folder |
| `POST /api/brand/preview` | The console colours a draft palette gives, and every contrast check, without saving |
| `PUT /api/brand` | Save names, palette and the derived console colours; refused if a contrast check fails |
| `PUT /api/brand/assets/{kind}` | Replace an image with the PNG in the body, after checking its size and shape |
| `/api/summary` | Counts per kind, CVEs tracked, total model cost, the last scan run and its six stages |
| `/api/runs?component=&limit=` | Runs, newest first, each with its sessions and cost |
| `/api/runs/{id}` | One run: its sessions, stages, documents saved while it ran, and its run report as HTML |
| `/api/cves` | The CVE register's rows, without the SPL and CQL columns |
| `/api/deliverables?kind=&status=&q=&limit=` | One entry per ID: kind, title, path under `out/`, first seen, status |
| `/api/deliverables/{id}/html` | The same entry plus the document as HTML, made with mammoth, and `pdf`: whether Word can make the branded PDF |
| `/api/deliverables/{id}/file` | The original `.docx`, as a download |
| `/api/deliverables/{id}/pdf/ready` | Makes the branded PDF if it is not cached yet; the page calls it to show progress |
| `/api/deliverables/{id}/pdf?download=` | The branded PDF, shown in the page, or as a download with `download=true` |
| `/api/stakeholders` | The list, and whether it exists yet |
| `POST /api/stakeholders` | Add one. `PUT` and `DELETE /api/stakeholders/{id}` change or remove one |
| `POST /api/stakeholders/start-from-example` | Copy the example list in, only when there is no list |
| `/api/audience` | Teams each report names, the stakeholders matched to each, and the teams nobody covers |

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
