---
name: genelabs-cti-documentation
description: "Produce and maintain official GeneLabs CTI program documentation as .docx — the governance layer: the CTI Plan, Threat Hunting Plan, procedures, policies, playbooks, methodologies and standards. Applies the same GeneLabs house identity as the bulletin and hunt skills (banner, corporate palette, wordmark footer, TLP marking, DOC # and page fields), enforces Document Control and Release History conventions, and can restyle an existing legacy document in place without touching its words. Use when writing, revising, formatting or rebranding any CTI program document, or when bringing older CTI documents onto the house system."
---

# GeneLabs CTI Program Documentation Builder

The CTI program ships four kinds of artifact, and they must read as one system:

| Artifact | Skill |
| --- | --- |
| Bulletins | `genelabs-cti-bulletin` |
| Hunt plans, not yet run | `genelabs-threat-hunt-package` |
| Completed hunts and run summaries | `genelabs-threat-hunt-report`, `genelabs-hunt-run-summary` |
| CVE priority briefs | `genelabs-cve-priority-brief` |
| **Program documentation and governance** | **this skill** |

This skill covers the documents that describe how the program works rather than
what a threat is doing: the CTI Plan, the Threat Hunting Plan, procedures,
policies, playbooks, methodologies, standards and communication plans. They live
in `CTI Documentation\Strategy_and_Plan` and `CTI Documentation\Policies_and_Procedures`.

Do NOT use this for a bulletin, a hunt, or a CVE brief. Those have their own
skills with their own section flow.

## Two ways in

**1. Restyle an existing document** — the common case. Content stays exactly as
written; only the branding changes.

```
python scripts/restyle_cti_doc.py in.docx out.docx \
    --doc-id "CTI-PLAN-09" \
    --marking "CTI Program Documentation" \
    --tlp "AMBER" \
    --copyright "© 2026 GeneLabs LLC  |  Proprietary and Confidential — For Internal Use Only" \
    --promote-headings --strip-watermark
```

| Flag | What it does |
| --- | --- |
| `--doc-id` | Goes in the footer as `DOC #`. Use the document slug plus its current version, for example `CTI-PLAN-09`. |
| `--marking` | Footer marking beside the TLP level. Default `CTI Program Documentation`. |
| `--tlp` | Footer TLP level. Default `AMBER+STRICT`; program documentation is usually `AMBER`. |
| `--promote-headings` | Shifts heading levels so the document's top level sections become Heading 1. Use on documents drafted with Heading 3 as their top level — it fixes the outline, never the words. |
| `--strip-watermark` | Removes a stale DRAFT watermark. Off by default: a document is only not a draft when a human says so. |
| `--no-banner` | Skips the page banner, for documents that must keep their own header. |

The restyler is deliberately conservative. It forces Arial, recolours only text
that carried no deliberate colour of its own, replaces stock Word table styles
with a neutral grid so blue banding stops fighting the palette, gives change
history tables usable column widths, clears legacy header furniture in favour of
the banner, and rebuilds the footer. It never rewrites a sentence, reorders a
section, or drops an image.

**2. Build a new document** from a JSON spec.

```
python scripts/build_cti_doc.py spec.json out.docx
```

```json
{
  "doc_id": "CTI-PROC-01",
  "title": "Threat Intelligence Sharing Procedure",
  "tlp": "AMBER",
  "marking": "CTI Program Documentation",
  "copyright_line": "© 2026 GeneLabs LLC  |  Proprietary and Confidential — For Internal Use Only",
  "doc_control": [
    ["Title", "Threat Intelligence Sharing Procedure"],
    ["ER Number", "DIR Workflow"],
    ["Effective Date", "2026-09-01"],
    ["Document Owner Function", "EIS"],
    ["Quality Manual Section", "N/A"]
  ],
  "summary": "One or two sentences a reader can act on without reading further.",
  "sections": [
    {"heading": "Purpose", "paragraphs": ["..."]},
    {"heading": "Scope", "paragraphs": ["..."], "bullets": ["..."]},
    {"heading": "Procedure", "subsections": [
      {"heading": "Intake", "bullets": ["..."]},
      {"heading": "Review", "table": {"header": ["Step", "Owner", "Output"],
                                      "rows": [["...", "...", "..."]]}}
    ]}
  ],
  "release_history": {
    "columns": ["Version", "Date", "Originator", "Description of Change"],
    "rows": [["00", "2026.09.01", "April Parker", "Initial release"]]
  },
  "appendix": [{"heading": "Appendix", "subsections": [{"heading": "Definitions", "table": {"header": ["Term", "Definition"], "rows": []}}]}]
}
```

If `python-docx` is missing, install it (`pip install python-docx --break-system-packages`).

## Document control — the part that makes it governance

Every governed CTI document opens with a control block and closes its main body
with a change history. Both are required; a document without them is a draft.

**Control block**, a two column table at the very top: Title, ER Number,
Effective Date, Document Owner Function, Quality Manual Section.

**Change history**, a four column table: Version, Date, Originator, Description
of Change. Two conventions are in use and both are correct — follow whichever the
document already uses:

| Document | Heading | Version form | Date form |
| --- | --- | --- | --- |
| CTI Plan | Release History | `08`, `09` | `2026.08.21` |
| Threat Hunting Plan | Revision History | `1.0`, `1.1` | `2026-08-21` |

Rules for entries:
- One row per substantive revision. Name the sections affected, say what changed,
  and give the reason or source where it helps: "Source: TH26-01 through TH26-13".
- **Never add a row when nothing material changed.** A branding pass alone is
  worth a row only when it is bundled with content change; formatting churn is not
  program history.
- **Never edit a document just so a row can be written.**
- Use the real date of the change.
- The `--doc-id` in the footer should carry the version, so the page furniture and
  the history table agree.

## Section flow

House order for a plan or procedure. Keep content in these buckets rather than
inventing new top level sections:

1. Document control block
2. Purpose
3. Authority
4. Scope
5. Definitions
6. Methodology, or the framework the document aligns to
7. Objectives
8. The body: lifecycle, procedure steps, or the process being governed
9. Metrics and KPIs, where the document owns any
10. Release or Revision History
11. Appendix: matrices, taxonomies, terminology

## Writing standard

- **No hyphenated compound modifiers.** House preference. "AI assisted pipeline",
  not "AI-assisted pipeline". Hyphens inside real identifiers stay: `TH26-03A`,
  `CTI26-19`, MITRE technique IDs.
- Tight language. A governance document is read under pressure; every sentence
  should survive being read once.
- Say what is true today. A plan that describes an aspiration as a capability
  fails an audit and misleads the team.
- Separate observation from recommendation. Where a document proposes something
  not yet in place, label it as a recommendation.
- Terminology must match the deliverables. If bulletins are tagged
  `PEER INCIDENT`, the plan does not call them Summary Bulletins.

## GeneLabs corporate branding (applied by the scripts)

Do not override these; they are the house identity, shared with the bulletin and
hunt skills.

| Element | Value |
| --- | --- |
| Accent, section headings, rules | GeneLabs orange `#FF7109` (`#E05F00` for small heading text) |
| Body and headline text | Abbey `#444648` |
| Meta text, wordmark, footer | Corporate grey `#676765` |
| Table header fill, callouts | `#FFF4E8`; label columns `#F4F4F4` |
| Rules and table borders | `#D9D9D9` at 0.75pt |
| Typeface | Arial throughout |

Heading treatment: Heading 1 in letterspaced orange caps over a 1.5pt orange
rule; Heading 2 in deepened orange; Heading 3 in Abbey bold. Bullets carry an
orange glyph. Page furniture: the Enterprise Information Security banner in the
header, and a footer beneath an orange rule holding the grey wordmark, the TLP
marking, the marking text, the copyright line, `DOC #` and live `Page X of Y`
fields.

Word shows page number fields as `1` until refreshed: Ctrl+A then F9. LibreOffice
resolves them on open.

Do NOT darken the `#D9D9D9` rules to "improve" dark mode. Word keeps an explicit
light border light on a dark canvas, so they stay visible; a mid grey disappears
into the dark page. Weight, not darkness, is the lever.

## Verify before delivering

- Fonts resolve to Arial only.
- The banner appears once at the top of every page, with no leftover legacy header
  block above or beside it.
- The footer carries wordmark, TLP marking, `DOC #` and `Page X of Y`.
- Every heading level is used for its actual depth; no stray automatic numbers
  appear in front of a heading that should not be numbered. If numbering shows up
  on inserted content, clone an existing paragraph of that style rather than
  creating one from the style name, so the document's own numbering carries over.
- Change history table: last row matches what actually changed, and the
  Description of Change column is wide enough to read.
- Tables carry the house grid, not Word's blue Grid Table banding.
- No stale DRAFT watermark on a document that is under version control.
- Render to PDF and look at it before shipping. Most defects in these documents
  are visual and invisible in the XML.

## Reference files
- `assets/cti_doc_template.docx` — the branded shell with the house banner. Clone
  it; never rebuild the banner by hand.
- `assets/cti_banner.jpg` — the banner image, used when restyling a document that
  already exists.
- `assets/genelabs_wordmark_grey.png` — footer wordmark, resolved automatically.
- `scripts/genelabs_style.py` — the shared palette, typography and page furniture.
  Import from here so every CTI artifact stays on one system.
- `scripts/build_cti_doc.py` — new documents from a JSON spec.
- `scripts/restyle_cti_doc.py` — house style applied to an existing document.
