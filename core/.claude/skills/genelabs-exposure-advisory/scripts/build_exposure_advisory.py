"""
Build an GeneLabs CTI Exposure Advisory (.docx) from a JSON spec.

    python build_exposure_advisory.py spec.json out.docx [template.docx]

An exposure advisory is the document you write when a hunt, a scan or a
connector lookup finds an GeneLabs asset reachable from somewhere it should not
be. It is read by leadership and by the engineers who will fix it, in that
order, so the risk and the required actions come first and the evidence comes
last.

For a threat bulletin use genelabs-cti-bulletin. For a hunt use
genelabs-threat-hunt-package or genelabs-threat-hunt-report. For CVE
prioritisation use genelabs-cve-priority-brief.
"""
import json
import os
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genelabs_style import (  # noqa: E402
    ABBEY, CALLOUT_FILL, DEFAULT_TEMPLATE, GREY, LABEL_FILL, ORANGE, RULE,
    add_banner, border, build_footer, bullet, keep_with_next, para, run,
    set_base_style, shade_cell, shade_paragraph, style_headings, table_borders,
)

DEFAULT_TLP = "AMBER+STRICT"
DEFAULT_MARKING = "CTI Exposure Advisory"
HEADING_STYLES = {1: "Heading 1", 2: "Heading 2", 3: "Heading 3", 4: "Heading 4"}

# House section order. The build warns when a spec departs from it, because the
# whole point of the advisory is that a reader can stop after the actions.
HOUSE_ORDER = ["Why We Care", "What Needs To Be Done", "Technical Detail",
               "Bottom Line"]

# Column widths as fractions of the text column, keyed by the first header cell.
# Detail and Description columns get the room, because they are the ones that
# wrap into unreadable ribbons when Word is left to autofit.
WIDTHS = {
    ("Title", 2): (0.26, 0.74),
    ("Field", 2): (0.30, 0.70),
    ("Action", 3): (0.24, 0.21, 0.55),
    ("Version", 4): (0.09, 0.13, 0.16, 0.62),
}
FALLBACK_WIDTHS = {2: (0.30, 0.70), 3: (0.24, 0.21, 0.55),
                   4: (0.09, 0.13, 0.16, 0.62)}


# ---- table geometry --------------------------------------------------------
def text_width(doc):
    s = doc.sections[0]
    return int(s.page_width - s.left_margin - s.right_margin)


def fix_table(t, width, fracs, repeat_header=True):
    """Fixed layout, explicit grid, repeating header row.

    python-docx writes cell widths but leaves w:tblGrid alone, and Word and
    LibreOffice both believe the grid. Rewrite both or nothing moves.
    """
    t.autofit = False
    tbl = t._tbl
    tblPr = tbl.tblPr
    for tag in ("w:tblLayout", "w:tblW"):
        old = tblPr.find(qn(tag))
        if old is not None:
            tblPr.remove(old)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:w"), str(width))
    tw.set(qn("w:type"), "dxa")
    tblPr.append(tw)

    grid = tbl.find(qn("w:tblGrid"))
    if grid is not None:
        tbl.remove(grid)
    grid = OxmlElement("w:tblGrid")
    for fr in fracs:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(int(width * fr / 635)))
        grid.append(gc)
    tbl.insert(list(tbl).index(tblPr) + 1, grid)

    for row in t.rows:
        for cell, fr in zip(row.cells, fracs):
            cell.width = Emu(int(width * fr))
    if repeat_header:
        trPr = t.rows[0]._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:tblHeader"))


def apply_widths(doc):
    width = text_width(doc)
    for t in doc.tables:
        ncols = len(t.columns)
        first = t.rows[0].cells[0].text.strip()
        fracs = WIDTHS.get((first, ncols)) or FALLBACK_WIDTHS.get(ncols)
        if fracs:
            fix_table(t, width, fracs, repeat_header=(first != "Title"))


# ---- blocks ----------------------------------------------------------------
def add_doc_control(doc, rows):
    t = doc.add_table(rows=len(rows), cols=2)
    for i, pair in enumerate(rows):
        label, value = (list(pair) + [""])[:2]
        lc, vc = t.rows[i].cells
        lc.text = ""
        vc.text = ""
        run(lc.paragraphs[0], label, size=9, bold=True, color=ABBEY)
        run(vc.paragraphs[0], value, size=9, color=GREY)
        shade_cell(lc, LABEL_FILL)
    table_borders(t, color=RULE)
    return t


def add_title_block(doc, title, subtitle=None, meta=None):
    p = para(doc, space_before=10, space_after=2)
    run(p, title, size=18, bold=True, color=ABBEY)
    border(p, "bottom", ORANGE, sz=18, space=4)
    if subtitle:
        para(doc, subtitle, size=10, color=GREY, italic=True, space_after=4)
    if meta:
        p = para(doc, space_after=10)
        run(p, meta, size=8, color=GREY, caps=True, spacing=20)


def add_callout(doc, label, text):
    p = para(doc, space_before=8, space_after=8)
    shade_paragraph(p, CALLOUT_FILL)
    border(p, "left", ORANGE, sz=24, space=6)
    run(p, label + "  ", size=10, bold=True, color=ABBEY)
    run(p, text, size=10, color=ABBEY)
    return p


def add_table(doc, spec):
    header = spec.get("header") or []
    rows = spec.get("rows") or []
    if not rows and not header:
        return None
    ncols = len(header) if header else max(len(r) for r in rows)
    t = doc.add_table(rows=len(rows) + (1 if header else 0), cols=ncols)
    if header:
        for ci, cell_text in enumerate(header):
            cell = t.rows[0].cells[ci]
            cell.text = ""
            run(cell.paragraphs[0], str(cell_text), size=9, bold=True, color=ABBEY)
            shade_cell(cell, CALLOUT_FILL)
    off = 1 if header else 0
    for ri, row in enumerate(rows):
        for ci in range(ncols):
            cell = t.rows[ri + off].cells[ci]
            cell.text = ""
            value = str(row[ci]) if ci < len(row) else ""
            run(cell.paragraphs[0], value, size=9, color=ABBEY)
    table_borders(t, color=RULE)
    if spec.get("caption"):
        para(doc, spec["caption"], size=8, color=GREY, italic=True,
             space_before=2, space_after=8)
    return t


def add_section(doc, sec, level=1):
    """Render order is intro, paragraphs, bullets, callout, table, subsections.

    Data tables therefore land after the prose that introduces them, and any
    bullets that unpack a table belong in a subsection so they follow it.
    """
    heading = sec.get("heading")
    if heading:
        p = doc.add_paragraph(heading, style=HEADING_STYLES.get(level, "Heading 4"))
        keep_with_next(p)
    if sec.get("intro"):
        para(doc, sec["intro"], size=10, color=ABBEY, space_after=6)
    for text in sec.get("paragraphs", []):
        para(doc, text, size=10, color=ABBEY, space_after=6)
    for item in sec.get("bullets", []):
        bullet(doc, item)
    if sec.get("callout"):
        c = sec["callout"]
        add_callout(doc, c.get("label", "Note:"), c.get("text", ""))
    if sec.get("table"):
        add_table(doc, sec["table"])
    for sub in sec.get("subsections", []):
        add_section(doc, sub, level + 1)


def add_release_history(doc, spec):
    """Optional. Omit the release_history key entirely on a single issue advisory;
    include it only where the advisory will be reissued and the reader needs to
    know whether the findings moved."""
    p = doc.add_paragraph(spec.get("heading", "Release History"), style="Heading 1")
    keep_with_next(p)
    add_table(doc, {
        "header": spec.get("columns",
                           ["Version", "Date", "Originator", "Description of Change"]),
        "rows": spec.get("rows", []),
    })


# ---- validation ------------------------------------------------------------
def check(spec):
    warn = []
    headings = [s.get("heading") for s in spec.get("sections", [])]
    if headings[:1] != ["Why We Care"]:
        warn.append("first section is %r, house order opens on 'Why We Care'"
                    % (headings[0] if headings else None))
    for name in HOUSE_ORDER:
        if name not in headings:
            warn.append("missing house section %r" % name)
    if not spec.get("summary"):
        warn.append("no summary: the one sentence callout is required")
    tech = next((s for s in spec.get("sections", [])
                 if s.get("heading") == "Technical Detail"), None)
    subs = [s.get("heading", "") for s in (tech or {}).get("subsections", [])]
    if not any("finding" in h.lower() or "external" in h.lower() for h in subs):
        warn.append("Technical Detail has no external view subsection; an "
                    "exposure advisory must show what the outside world sees")
    return warn


# ---- build -----------------------------------------------------------------
def build(spec, out_path, template_path=None):
    for w in check(spec):
        print("warning:", w, file=sys.stderr)

    template_path = template_path or DEFAULT_TEMPLATE
    doc = Document(template_path) if os.path.exists(template_path) else Document()
    set_base_style(doc)
    style_headings(doc)

    if spec.get("doc_control"):
        add_doc_control(doc, spec["doc_control"])
    add_title_block(doc, spec["title"], spec.get("subtitle"), spec.get("meta"))
    if spec.get("summary"):
        add_callout(doc, spec.get("summary_label", "Summary:"),
                    spec["summary"])
    for sec in spec.get("sections", []):
        add_section(doc, sec, sec.get("level", 1))
    if spec.get("release_history"):
        add_release_history(doc, spec["release_history"])
    for sec in spec.get("appendix", []):
        add_section(doc, sec, sec.get("level", 1))

    add_banner(doc)
    build_footer(doc, spec.get("doc_id", ""),
                 spec.get("marking", DEFAULT_MARKING),
                 tlp=spec.get("tlp", DEFAULT_TLP),
                 copyright_line=spec.get("copyright_line", ""))
    apply_widths(doc)

    cp = doc.core_properties
    cp.title = spec["title"]
    cp.comments = ("GeneLabs Enterprise Information Security | "
                   "Cyber Threat Intelligence")
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    template = sys.argv[3] if len(sys.argv) > 3 else None
    print("wrote", build(spec, sys.argv[2], template))
