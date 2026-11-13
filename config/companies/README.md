# Companies

One folder per company. Its `company.json` and `assets/` decide how that company's
reports and console look; its `profile.json` and `reference/` notes decide what the
pipeline watches for it. Nothing else in the repo carries a company's colours, name,
logo, products or peers.

```
<slug>/
  company.json                 the brand
  assets/logo.png              footer logo on every document
  assets/banner.png            page header image on every document
  assets/symbol.png            the mark beside the name in the console
  profile.json                 the facts the prompts and the weekly report use
  reference/tech-profile.md    what the company runs, read by the scans
  reference/peer-watchlist.md  competitors, partners and vendors, read by the scans
```

## Where they live

- **`data/companies/<slug>/`** is each company's working folder: its brand, and for every
  company but GeneLabs its stakeholders, `out/` and `logs/` too. The console keeps it and
  the Branding tab saves into it. `data/` is gitignored and kept out of the pipeline
  image, because it holds people and reports.
- **`config/companies/<slug>/`** (this folder) holds committed first copies. The console
  copies each into `data/` once, on its first start, and never again, so a saved brand
  is not overwritten. A copy from before profiles existed gets `profile.json` and
  `reference/` added, and nothing else changes. `genelabs/` is GeneLabs; `_starter/` is
  the neutral brand and blank facts a new company begins from, and is never listed.

## Who reads it

| Reader | Reads | Chooses the company with |
|---|---|---|
| Document builders (bulletin, hunt package and report, advisory, documentation, restyler, hand off, awareness blog, CVE brief, exposure briefing) | `core/tools/cti_brand.py` | `CTI_COMPANY=<slug>` (looked up in `data/companies`, then here) or `CTI_COMPANY_DIR=<folder>` |
| Pipeline prompts | `scripts/render_task.py` fills the `{{company}}` style placeholders in `components/*/task*.md`, through `core/tools/cti_profile.py` | `COMPANY=<slug>` for the container |
| Weekly and quarterly reports | `core/tools/reporting/src/core/config.py` (name, colours, industry, products, peers) and the brand banner | The same |
| Console | `console/backend/src/cti_console/brand.py`, served at `/api/brand` | The **Company** list in the header |

All default to `genelabs`. A local run (`scripts/run-local.*`, `COMPANY=<slug>` or
`-Company <slug>`) hands the container `data/companies/<slug>/` read only, so a save in
the console reaches the next run. A cloud image has no `data/` and uses the committed
copy here, so a company runs in the cloud only once its folder is committed.

## The fields

| Field | Used for |
|---|---|
| `slug` | The folder name. Lower case letters, digits and `-` only |
| `name` | "Relevance to <name>", the console heading, the browser tab |
| `legal_name` | Copyright lines |
| `department`, `program` | The document properties comment; `program` is the console's subtitle |
| `contact` | The bulletin footer contact line, unless a spec gives its own |
| `palette` | Document colours, six digit hex without `#`: `primary` (headings, table headers), `accent` (rules, bullets, links), `text`, `muted` (footer, meta), `rule` (light rules, borders), `tint` (label cells, callouts), `zebra` (alternate rows) |
| `assets` | Paths to the three images, inside this folder |
| `console.light`, `console.dark` | Console colour tokens for each theme. A token left out uses the default in `console/frontend/src/index.css`. Status colours (ok, warn, fail) are not brand and cannot be set |

Severity, category and TLP colours mean the same thing for every company, so they stay
in the builders.

## The profile

`profile.json` holds what the pipeline knows about the company. Text fields may be
empty and lists may be `[]`: a run then reports that check as NOT SET UP instead of
treating it as clean.

| Field | Used for |
|---|---|
| `analyst` | Who the agents support, "April, the CTI Lead" |
| `industry` | The company line every prompt opens with, and the strategic report's framing |
| `domains` | The Shodan certificate check, and the hostname check on awareness posts |
| `own_products`, `ics_products` | The own product watch: a vulnerability in one goes to the top |
| `security_contact`, `osint_source_name` | Report footers and source labels |
| `products`, `flagship_product`, `strategic_profile`, `product_keywords`, `ir_feed_urls` | The weekly and quarterly report analysis |
| `peer_watch_orgs`, `peer_competitor_orgs` | Peer incident matching in the weekly report. Keep them in step with `reference/peer-watchlist.md` |

Every prompt a run uses is saved with its state, in `state/_work/prompts/`, so what the
agents were told can be read back.

## Change a company's brand

Open the console's **Settings, Branding** tab. Names and colours are a draft until you
save; the tab previews the console in light and dark and a report page as you type, and
checks every pair of colours for contrast. Text needs 4.5:1 against its background, and
charts and lines need 3:1 (WCAG AA). A save that fails a check is refused, with the pair
named. The console's own light and dark colours are worked out from the seven document
colours, so the `console` block is rewritten on every save.

Images save as soon as they are picked: PNG only, up to 2 MB, 16 to 4000 pixels a side,
and of a shape the reports can hold (logo 1.5 to 8 times as wide as tall, banner 4 to
12, symbol 0.3 to 3). The previous file is kept beside the new one as `.bak`, which git
ignores.

A save changes the files in `data/companies/<slug>/`, not this repository. To make a
saved brand the committed GeneLabs default (for the cloud image), copy its
`company.json` and `assets/` back here and commit them.

## Add a company

1. In the console, open **Settings, Companies** and add it, blank or as a copy of
   another company's branding. It opens on its Branding tab. A copy takes the brand
   only: the facts always start blank.
2. Set its names, colours and images there.
3. Fill in `data/companies/<slug>/profile.json` and the two notes in `reference/`.
4. Run it: `COMPANY=<slug> scripts/run-local.sh bulletin-scan`, or on Windows
   `.\scripts\run-local.ps1 bulletin-scan -Company <slug>`. Its reports go to
   `data/companies/<slug>/out/`, where the console shows them.
5. To schedule it: `.\scripts\register-schedule.ps1 -Company <slug>`.

In the cloud, each company other than GeneLabs keeps its state under
`companies/<slug>/<component>/` in the bucket, so two companies never share a dedup log
or register. GeneLabs keeps the layout it had.

Not yet per company: the console's favicon, and what the hunt and connector rules say
about one company's own Splunk and Falcon (index maps, measured volumes): those were
measured at GeneLabs and are labelled so.
