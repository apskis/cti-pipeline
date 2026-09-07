---
name: "genelabs-hunt-run-summary"
description: "Build an GeneLabs-branded Threat Hunt Summary .docx — the day-level roll-up across a whole automated hunt loop (multiple hunts plus pivots): run metadata, a colour-coded verdicts-at-a-glance table, per-hunt narrative cards, pivot gate reasoning, cross-engine standouts, recurring gaps, and an archived-reports index. Also triggers on \"hunt run summary\", \"run summary\", \"daily hunt roll-up\". Use when summarizing a completed threat hunt run or turning the end-of-run summary into a branded document. For a single completed hunt use genelabs-threat-hunt-report instead; for a not-yet-run hunt plan use genelabs-threat-hunt-package."
---

# GeneLabs Threat Hunt Summary Builder

Produces the **run-level roll-up** .docx for a whole day's automated threat hunt loop —
many hunts and pivots in one document — in April's GeneLabs CTI house branding. The
document is titled **Threat Hunt Summary** (renamed from the former "CTI Threat Hunting Automation Run
Summary" on 2026-08-25 at April's instruction). This is distinct from the per-hunt
deliverables:

- **This skill (`genelabs-hunt-run-summary`)** — one document covering an entire run: the
  verdict on every hypothesis, pivot reasoning, cross-engine notes, and recurring gaps.
- `genelabs-threat-hunt-report` — one completed hunt in depth (hypotheses, queries, findings).
- `genelabs-threat-hunt-package` — one not-yet-run hunt plan.

The branding (banner template, corporate palette, wordmark / TLP / DOC # / page-number
footer) is **reused from the installed `genelabs-threat-hunt-report` skill** so the summary
reads as one set with the per-hunt reports. The builder finds those shared assets
automatically — no path argument needed.

## When to use
- The automated threat hunt task has finished a run and you want the end-of-run summary as a
  branded Word document.
- The user asks for a "threat hunt summary", "hunt run summary", "run summary", "daily hunt
  roll-up", "summary docx of today's hunts", or similar.

## How to build
1. Assemble the run into a `spec.json` using the schema below (one `hunts[]` entry per hunt,
   parents and pivots together; mark a pivot with `pivot_of`).
2. Write the builder script (the full source is embedded at the bottom of this file) to
   `scripts/build_hunt_run_summary.py`.
3. Run:
   ```
   python3 scripts/build_hunt_run_summary.py spec.json out.docx
   ```
4. Name the output to April's archive convention and write it into the CTI Threat Hunts year
   archive alongside the per-hunt reports:
   `<YYYY-MM-DD>-ThreatHuntSummary.docx`
   (do **not** add the `-Complete` marker — that is reserved for per-hunt reports and the
   hunt task skips filenames containing "Complete").
5. Deliver with `present_files`.

If `python-docx` is missing: `pip install python-docx --break-system-packages`.

## Verdict colours (run roll-up)
The verdict cell and each hunt's accent bar are coloured by verdict, distinct from the
single-hunt classification palette:

| Verdict | Colour |
| --- | --- |
| SUPPORTED | red `B71C1C` |
| PARTIALLY SUPPORTED | amber `EF6C00` |
| NOT SUPPORTED | green `2E7D32` |
| INCONCLUSIVE | grey `676765` |

`NOT SUPPORTED` renders green because "no evidence in the window with the telemetry
available" is the clean outcome — never write "disproven". Set `flag` on a hunt to surface a
Suspicious side-finding, an environmental gap, or campaign pressure in the glance table
(rendered in amber).

## JSON spec schema
```json
{
  "run_date": "2026-08-20",
  "doc_id": "FHR-2026-08-20",
  "status": "Complete",
  "window": "14-day ceiling per hunt (individual windows)",
  "engine_status": "Both engines green; Falcon and Splunk corroboration ran on every hunt.",
  "headline": "5 parent hunts + 2 pivots, all filed. No confirmed compromise; 2 Suspicious side findings actioned.",
  "reviewed_by": "[Pending Review]",
  "tlp": "AMBER+STRICT",
  "hunts": [
    {
      "id": "TH26-06",
      "title": "SharePoint forged JWT",
      "verdict": "NOT SUPPORTED",
      "confidence": "High",
      "flag": "",
      "pivot_of": null,
      "archived": "2026-08-20-SharePointJWTBypass-TH2606-Complete.docx",
      "narrative": "One tight paragraph: what the hunt tested, what both engines showed, the decisive evidence, and any hygiene flag."
    },
    {
      "id": "TH26-07A",
      "title": "SmartApeSG / NetSupport",
      "verdict": "NOT SUPPORTED",
      "confidence": "Medium-High",
      "flag": "Campaign pressure",
      "pivot_of": "TH26-07",
      "archived": "2026-08-20-SmartApeSGNetSupport-TH2607A-Complete.docx",
      "narrative": "Pivot narrative..."
    }
  ],
  "pivot_reasoning": "Which pivots were spawned and why they passed the four gates; which candidates were Blocked / Handed / Detection-engineering, and the run budget used.",
  "cross_engine": "Standouts one engine alone would have missed — what Splunk caught that Falcon could not and vice versa.",
  "recurring_gaps": ["Gap 1 ...", "Gap 2 ...", "Gap 3 ..."],
  "closing_note": "Optional footer paragraph; a sensible default is used if omitted."
}
```
`recurring_gaps` accepts a list (rendered as GeneLabs orange bullets) or a single string.
`subtitle`, `doc_title`, `tlp`, and `closing_note` are optional overrides. `doc_title`
defaults to "Threat Hunt Summary"; pass it only to override.

## Layout produced
1. Right-aligned `DOC # | run date` header and the "Threat Hunt Summary" title.
2. Run-at-a-glance metadata table (run date, hunts executed, window, engine status, reviewer).
3. Run-headline callout in the warm GeneLabs tint.
4. **Verdicts at a Glance** — colour-coded table: Hunt · Title · Verdict · Flag (pivots
   labelled "pivot of …").
5. **Hunt-by-Hunt Detail** — one card per hunt: a verdict-coloured left accent bar, a
   Verdict / Confidence / Archived chip strip, and the narrative paragraph.
6. **Pivot Gate Reasoning**, **Cross-Engine Standouts**, **Recurring Gaps to Close**.
7. **Archived Reports** index table.
8. Italic closing note, then the shared GeneLabs footer (wordmark, TLP marking, copyright,
   DOC #, live page numbers) beneath an orange rule.

## Builder source
Write this verbatim to `scripts/build_hunt_run_summary.py`, then run it. It imports the
branding helpers and clones the banner template from the installed
`genelabs-threat-hunt-report` skill, which it locates automatically.

```python
#!/usr/bin/env python3
"""
Build an GeneLabs-branded Threat Hunt Summary .docx from a JSON spec.

This is the run-level roll-up across a whole day's hunt loop (many hunts +
pivots), NOT a single-hunt report. It reuses the GeneLabs house branding
(banner template, corporate palette, wordmark/TLP/DOC#/page footer) from the
installed genelabs-threat-hunt-report skill, so summaries read as one set with
the per-hunt reports.

Usage:
    python build_hunt_run_summary.py spec.json out.docx

The builder locates the shared GeneLabs assets automatically by searching for
the genelabs-threat-hunt-report skill; no path argument is needed.
"""
import glob
import json
import os
import sys
import importlib.util

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def _locate_report_skill():
    """Find the installed genelabs-threat-hunt-report skill dir (template, wordmark, helpers).

    glob '**' does not descend into hidden dirs such as .claude, so try explicit
    patterns for the common install locations first, then a broad recursive fallback.
    """
    marker = os.path.join("genelabs-threat-hunt-report", "scripts", "build_hunt_report.py")
    patterns = [
        os.path.join("/sessions", "*", "mnt", ".claude", "skills", marker),
        os.path.join(os.path.expanduser("~"), ".claude", "skills", marker),
        os.path.join("/sessions", "*", "mnt", "*", "skills", marker),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", marker),
    ]
    for pat in patterns:
        hits = glob.glob(pat)
        if hits:
            return os.path.dirname(os.path.dirname(os.path.abspath(hits[0])))
    for root in ("/sessions", os.path.expanduser("~"), os.getcwd()):
        hits = glob.glob(os.path.join(root, "**", marker), recursive=True)
        if hits:
            return os.path.dirname(os.path.dirname(os.path.abspath(hits[0])))
    raise SystemExit("Could not locate the genelabs-threat-hunt-report skill for branding assets.")


SKILL = _locate_report_skill()
_spec = importlib.util.spec_from_file_location(
    "ithr", os.path.join(SKILL, "scripts", "build_hunt_report.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

TEMPLATE = os.path.join(SKILL, "assets", "hunt_template.docx")
WORDMARK = os.path.join(SKILL, "assets", "genelabs_wordmark_grey.png")

# Verdict palette for a run roll-up (distinct from single-hunt classifications).
VERDICT_COLOR = {
    "supported": "B71C1C",
    "partially supported": "EF6C00",
    "not supported": "2E7D32",
    "inconclusive": "676765",
}


def _vcolor(v):
    return VERDICT_COLOR.get(str(v).strip().lower(), R.GREY)


def build(spec, out_path):
    doc = Document(TEMPLATE)
    R.set_base_style(doc)
    run_date = spec.get("run_date", "")
    doc_id = spec.get("doc_id", "FHR-" + run_date)

    # header line (right-aligned run id + date), matching the report house style
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run(f"{doc_id}  |  {run_date}")
    r.font.name = R.FONT; r.font.size = Pt(9); r.font.bold = True

    R.h_title(doc, spec.get("doc_title", "Threat Hunt Summary"))
    sub = spec.get("subtitle") or (
        "Daily automated threat-hunt roll-up — CrowdStrike Falcon + Splunk Cloud. "
        f"Run executed {run_date}.")
    R._p(doc, sub, size=10, italic=True, color=R.GREY, after=4)

    hunts = spec.get("hunts", [])
    parents = [h for h in hunts if not h.get("pivot_of")]
    pivots = [h for h in hunts if h.get("pivot_of")]

    # Run-at-a-glance metadata table
    t = doc.add_table(rows=0, cols=4); t.style = "Table Grid"; R._table_borders(t)
    meta_rows = [
        ["Run Date (UTC)", run_date, "Status", spec.get("status", "Complete")],
        ["Hunts Executed", f"{len(parents)} parent + {len(pivots)} pivot",
         "Window", spec.get("window", "14-day ceiling per hunt")],
        ["Engine Status", spec.get("engine_status", ""), "Reviewed By",
         spec.get("reviewed_by", "[Pending Review]")],
    ]
    for a, b, c, d in meta_rows:
        cells = t.add_row().cells
        for cell, val, bold in ((cells[0], a, True), (cells[1], b, False),
                                (cells[2], c, True), (cells[3], d, False)):
            R._cell_shade(cell, R.META_LABEL if (bold and val) else R.WHITE)
            cell.paragraphs[0].text = ""
            rr = cell.paragraphs[0].add_run(val)
            rr.font.name = R.FONT; rr.font.size = Pt(9); rr.font.bold = bold
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # Headline callout
    if spec.get("headline"):
        p = doc.add_paragraph(); R._shade(p, R.BOX_FILL)
        p.paragraph_format.space_after = Pt(3); p.paragraph_format.space_before = Pt(2)
        r1 = p.add_run("Run headline:  "); r1.font.name = R.FONT; r1.font.size = Pt(10); r1.font.bold = True
        r2 = p.add_run(spec["headline"]); r2.font.name = R.FONT; r2.font.size = Pt(10)

    # Verdict-at-a-glance table (colour-coded verdicts)
    R.h_section(doc, "Verdicts at a Glance")
    headers = ["Hunt", "Title", "Verdict", "Flag"]
    tbl = doc.add_table(rows=1, cols=len(headers)); tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT; R._table_borders(tbl)
    for j, h in enumerate(headers):
        c = tbl.rows[0].cells[j]; R._cell_shade(c, R.GENELABS_ORANGE)
        c.paragraphs[0].text = ""
        rr = c.paragraphs[0].add_run(h); rr.font.name = R.FONT; rr.font.size = Pt(9)
        rr.font.bold = True; rr.font.color.rgb = RGBColor.from_string(R.WHITE)
    for i, h in enumerate(hunts):
        cells = tbl.add_row().cells
        if i % 2 == 1:
            for cc in cells:
                R._cell_shade(cc, R.ZEBRA)
        idlabel = h.get("id", "")
        if h.get("pivot_of"):
            idlabel += f"  (pivot of {h['pivot_of']})"
        vals = [idlabel, h.get("title", ""), h.get("verdict", ""), h.get("flag", "")]
        for j, val in enumerate(cells):
            val.paragraphs[0].text = ""
            rr = val.paragraphs[0].add_run(str(vals[j]))
            rr.font.name = R.FONT; rr.font.size = Pt(9)
            if j == 2:  # verdict cell coloured + bold
                rr.font.bold = True
                rr.font.color.rgb = RGBColor.from_string(_vcolor(vals[2]))
            if j == 3 and vals[3]:  # flag amber
                rr.font.bold = True
                rr.font.color.rgb = RGBColor.from_string(R.PRIO["MEDIUM"])
    for j, w in enumerate([1.7, 2.5, 1.6, 1.1]):
        for row in tbl.rows:
            row.cells[j].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # Per-hunt narrative cards, with a coloured accent bar keyed to the verdict
    R.h_section(doc, "Hunt-by-Hunt Detail")
    for h in hunts:
        col = _vcolor(h.get("verdict", ""))
        title = h.get("id", "")
        if h.get("title"):
            title += " — " + h["title"]
        if h.get("pivot_of"):
            title += f"  ·  pivot of {h['pivot_of']}"
        R._accent_bar(doc, title, col, size=10.5)
        R._chip_row(doc, [("Verdict", h.get("verdict", "")),
                          ("Confidence", h.get("confidence", "")),
                          ("Archived", h.get("archived", ""))])
        if h.get("narrative"):
            R._p(doc, h["narrative"], size=10, after=4)

    # Pivot gate reasoning
    if spec.get("pivot_reasoning"):
        R.h_section(doc, "Pivot Gate Reasoning")
        R._p(doc, spec["pivot_reasoning"], size=10)

    # Cross-engine standouts
    if spec.get("cross_engine"):
        R.h_section(doc, "Cross-Engine Standouts")
        R._p(doc, spec["cross_engine"], size=10)

    # Recurring gaps
    if spec.get("recurring_gaps"):
        R.h_section(doc, "Recurring Gaps to Close")
        if isinstance(spec["recurring_gaps"], list):
            R.bullets(doc, spec["recurring_gaps"])
        else:
            R._p(doc, spec["recurring_gaps"], size=10)

    # Archived reports index
    archived = [h for h in hunts if h.get("archived")]
    if archived:
        R.h_section(doc, "Archived Reports")
        R.grid_table(doc, ["Hunt", "Verdict", "Archived Filename"],
                     [[h.get("id", ""), h.get("verdict", ""), h.get("archived", "")]
                      for h in archived], widths=[1.4, 1.6, 4.0])

    _closing = spec.get("closing_note") or (
        "Automated threat hunt run summary. Each hunt was executed against CrowdStrike Falcon "
        "endpoint telemetry and corroborated in Splunk Cloud within its own 14-day window; "
        "per-hunt reports are filed in the CTI Threat Hunts year archive. Verdicts reflect the "
        "evidence available at run time — NOT SUPPORTED means no evidence in the window with the "
        "telemetry available, never proof of absence.")
    R._p(doc, "", before=8)
    R._p(doc, _closing, size=8, italic=True, color=R.GREY)

    R.build_footer(doc, doc_id, spec.get("tlp", R.DEFAULT_TLP),
                   R._copyright(run_date), wordmark_path=WORDMARK)
    cp = doc.core_properties
    cp.title = f"Threat Hunt Summary {run_date}"
    cp.category = "Threat Hunt Summary"
    cp.comments = "GeneLabs Enterprise Information Security | Cyber Threat Intelligence"
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    print("wrote", build(spec, sys.argv[2]))
```

