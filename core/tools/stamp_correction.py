#!/usr/bin/env python3
"""Stamp a CORRECTION NOTICE into an already-issued GeneLabs CTI document.

Written 2026-08-27, when re-measuring the Splunk estate retracted GAP-13 and re-scoped
GAP-14, and three exposure advisories already in circulation turned out to assert things
that are no longer true.

WHY STAMP RATHER THAN REBUILD

The originating specs for those advisories are not retained, so a rebuild would mean
reconstructing their content from the rendered document — which risks changing sentences
nobody asked to change, in a document somebody has already read and acted on. Stamping
adds; it does not silently rewrite. The reader sees the original claim AND the correction,
which is also the honest record: a corrected document that hides what it used to say is
harder to trust than one that shows its own history.

WHERE IT GOES

Immediately after the summary callout, before Why We Care. A correction placed in an
appendix is a correction nobody reads. It is shaded in the house callout fill with a red
label, because it must be visible on a skim.

The stamp does NOT alter the original paragraphs. Where a specific sentence is now wrong,
name it in the correction text and quote enough of it to be found.

Usage:
  python stamp_correction.py <doc.docx> <label> <text...>
"""
import sys, copy

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ORANGE, ABBEY, GREY, TINT, RED = "FF7109", "444648", "676765", "FFF4E8", "C62828"


def _rgb(h):
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _run(p, text, size=9, bold=False, italic=False, color=ABBEY):
    r = p.add_run(text)
    r.font.name = "Arial"; r.font.size = Pt(size)
    r.font.bold = bold; r.font.italic = italic
    r.font.color.rgb = _rgb(color)
    rpr = r._element.get_or_add_rPr()
    rf = OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:cs"):
        rf.set(qn(a), "Arial")
    rpr.append(rf)
    return r


def _anchor(doc):
    """Insert after the summary, or after the document control table if there is no summary.

    Falls back to the first body paragraph rather than failing: a stamp in a slightly odd
    place still gets read, whereas an exception means the correction never ships.
    """
    for p in doc.paragraphs:
        t = p.text.strip().lower()
        if t.startswith("summary") or "summary:" in t[:20]:
            return p
    for p in doc.paragraphs:
        if p.style.name.startswith("Heading"):
            return p
    return doc.paragraphs[0] if doc.paragraphs else None


def stamp(path, label, lines):
    doc = Document(path)
    anchor = _anchor(doc)
    if anchor is None:
        sys.exit(f"no anchor paragraph found in {path}")

    tbl = doc.add_table(rows=1, cols=1)
    cell = tbl.rows[0].cells[0]
    cell.width = Inches(6.6)
    sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:fill"), TINT)
    cell._tc.get_or_add_tcPr().append(sh)

    p0 = cell.paragraphs[0]
    p0.paragraph_format.space_before = Pt(6); p0.paragraph_format.space_after = Pt(3)
    _run(p0, label.upper(), 9, bold=True, color=RED)
    for ln in lines:
        p = cell.add_paragraph()
        p.paragraph_format.space_before = Pt(0); p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.12
        _run(p, ln, 8.5, color=ABBEY)
    cell.paragraphs[-1].paragraph_format.space_after = Pt(7)

    # left accent bar, matching the house callout
    tblPr = tbl._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge, sz, col in (("left", "24", ORANGE), ("top", "4", "D9D9D9"),
                          ("bottom", "4", "D9D9D9"), ("right", "4", "D9D9D9")):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), sz)
        e.set(qn("w:space"), "0"); e.set(qn("w:color"), col)
        borders.append(e)
    tblPr.append(borders)

    anchor._p.addnext(tbl._tbl)
    doc.save(path)
    return len(lines)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    n = stamp(sys.argv[1], sys.argv[2], sys.argv[3:])
    print(f"stamped {sys.argv[1]} with {n} correction line(s)")
