# Companies

One folder per company. Its `company.json` and `assets/` decide how that company's
reports and console look. Nothing else in the repo carries a company's colours, name
or logo.

```
<slug>/
  company.json
  assets/logo.png      footer logo on every document
  assets/banner.png    page header image on every document
  assets/symbol.png    the mark beside the name in the console
```

## Where they live

- **`data/companies/<slug>/`** is each company's working folder: its brand, and for every
  company but GeneLabs its stakeholders, `out/` and `logs/` too. The console keeps it and
  the Branding tab saves into it. `data/` is gitignored and kept out of the pipeline
  image, because it holds people and reports.
- **`config/companies/<slug>/`** (this folder) holds committed first copies. The console
  copies each into `data/` once, on its first start, and never again, so a saved brand
  is not overwritten. `genelabs/` is the GeneLabs brand; `_starter/` is the neutral
  brand a blank company begins from, with placeholder images, and is never listed.

## Who reads it

| Reader | Reads | Chooses the company with |
|---|---|---|
| Document builders (bulletin, hunt package and report, advisory, documentation, restyler, hand off, awareness blog, CVE brief, exposure briefing) | `core/tools/cti_brand.py` | `CTI_COMPANY=<slug>` (looked up in `data/companies`, then here) or `CTI_COMPANY_DIR=<folder>` |
| Console | `console/backend/src/cti_console/brand.py`, served at `/api/brand` | The **Company** list in the header |

Both default to `genelabs`. A local run (`scripts/run-local.*`) hands the container
`data/companies/genelabs/` read only, so a Branding tab save reaches the next run. A
cloud image has no `data/` and uses the committed copy here.

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
   another company's branding. It opens on its Branding tab.
2. Set its names, colours and images there.
3. Build a document with `CTI_COMPANY=<slug>` to check it.

Not yet per company: the pipeline itself (it runs for GeneLabs only), the console's
favicon, the weekly and quarterly report package (`core/tools/reporting`), and the
company facts in the agents' prompts. Those come in phase 4.
