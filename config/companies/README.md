# Companies

One folder per company. Its `company.json` and `assets/` decide how that company's
reports and console look. Nothing else in the repo carries a company's colours, name
or logo.

```
config/companies/<slug>/
  company.json
  assets/logo.png      footer logo on every document
  assets/banner.png    page header image on every document
  assets/symbol.png    the mark beside the name in the console
```

## Who reads it

| Reader | Reads | Chooses the company with |
|---|---|---|
| Document builders (bulletin, hunt package and report, advisory, documentation, restyler, hand off, awareness blog, CVE brief, exposure briefing) | `core/tools/cti_brand.py` | `CTI_COMPANY=<slug>` or `CTI_COMPANY_DIR=<folder>` |
| Console | `console/backend/src/cti_console/brand.py`, served at `/api/brand` | `CTI_CONSOLE_COMPANY=<slug>` or `CTI_CONSOLE_COMPANY_DIR=<folder>` |

Both default to `genelabs`.

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

A save changes the files in the company's folder. For `genelabs`, that is this
repository, so it shows up as a change to commit or discard.

## Add a company

1. Copy `genelabs/` to a new folder named for the company's slug.
2. Start the console with `CTI_CONSOLE_COMPANY=<slug>` and change it on the Branding
   tab, or edit `company.json` and the images by hand.
3. Build a document with `CTI_COMPANY=<slug>` to check it.

Not yet branded per company: the console's favicon, the weekly and quarterly report
package (`core/tools/reporting`), and the company facts in the agents' prompts. A company
picker comes in phase 3. Those come in later phases.
