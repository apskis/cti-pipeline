"""
Apply the GeneLabs CTI house style to an EXISTING .docx, in place, without
rewriting its content.

    python restyle_cti_doc.py in.docx out.docx \
        --doc-id "CTI-PLAN-08" \
        --marking "CTI Program Documentation" \
        --tlp "AMBER" \
        --copyright "© 2026 GeneLabs LLC  |  Proprietary and Confidential"

What it changes: typeface, palette, heading treatment, bullet colour, table
borders and header fill, the page banner and the footer furniture.
What it never changes: words, section order, images, tables, or numbering.

Use this to bring legacy CTI documents onto the house system, or after editing a
document's content, so branding stays consistent across the whole program.
"""
import argparse
import os
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genelabs_style import (  # noqa: E402
    ABBEY, CALLOUT_FILL, FONT, GREY, LABEL_FILL, ORANGE, RULE,
    add_banner, build_footer, fit_change_history, promote_headings,
    set_base_style, shade_cell, strip_watermarks, style_headings, table_borders,
)

NEUTRAL = {None, "000000", "auto", "444648", "333333", "1F1F1F", "212121"}


def _force_font(r):
    r.font.name = FONT
    rpr = r._element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rpr.insert(0, rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), FONT)


def _neutral_to_abbey(r):
    """Recolour only text that carries no deliberate colour of its own."""
    cur = None
    try:
        if r.font.color is not None and r.font.color.rgb is not None:
            cur = str(r.font.color.rgb)
    except (AttributeError, ValueError):
        cur = None
    if cur is None or cur.upper() in {c.upper() for c in NEUTRAL if c}:
        r.font.color.rgb = RGBColor.from_string(ABBEY)


def _style_bullet_glyph(p):
    """Colour the list glyph orange by styling the paragraph mark."""
    pPr = p._p.get_or_add_pPr()
    if pPr.find(qn('w:numPr')) is None:
        return False
    rpr = pPr.find(qn('w:rPr'))
    if rpr is None:
        rpr = OxmlElement('w:rPr')
        pPr.insert(0, rpr)
    for tag, attrs in (('w:rFonts', {'w:ascii': FONT, 'w:hAnsi': FONT}),
                       ('w:color', {'w:val': ORANGE})):
        old = rpr.find(qn(tag))
        if old is not None:
            rpr.remove(old)
        el = OxmlElement(tag)
        for k, v in attrs.items():
            el.set(qn(k), v)
        rpr.append(el)
    return True


COLOURFUL_STYLES = ("Grid Table", "List Table", "Light Shading", "Medium Shading",
                    "Colorful", "Light List", "Medium List")


def _neutralize_table_style(table, doc):
    """Swap Word's stock coloured table styles for a neutral grid.

    Those styles carry their own blue headers and row banding, which fights the
    GeneLabs palette. Custom house styles are left alone.
    """
    try:
        name = table.style.name or ""
    except Exception:
        return
    if not name.startswith(COLOURFUL_STYLES):
        return
    try:
        table.style = doc.styles["Table Grid"]
    except KeyError:
        pass


def _clear_shading(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    for sh in tcPr.findall(qn('w:shd')):
        tcPr.remove(sh)


def _has_image(cell):
    return "<w:drawing" in cell._tc.xml or "<w:pict" in cell._tc.xml


def _restyle_paragraph(p):
    for r in p.runs:
        _force_font(r)
        if not p.style.name.startswith("Heading") and p.style.name != "Title":
            _neutral_to_abbey(r)
    _style_bullet_glyph(p)


def restyle(in_path, out_path, doc_id, marking, tlp, copyright_line,
            banner=True, table_headers=True, promote=False, watermark=True):
    doc = Document(in_path)
    if not watermark:
        strip_watermarks(doc)
    if promote:
        promote_headings(doc)
    set_base_style(doc)
    style_headings(doc)

    for p in doc.paragraphs:
        _restyle_paragraph(p)

    for t in doc.tables:
        _neutralize_table_style(t, doc)
        table_borders(t, color=RULE, sz=6)
        rows = t.rows
        if not rows:
            continue
        head = rows[0]
        headerish = (table_headers
                     and all(c.text.strip() for c in head.cells)
                     and not any(_has_image(c) for c in head.cells))
        for ri, row in enumerate(rows):
            for ci, cell in enumerate(row.cells):
                for p in cell.paragraphs:
                    _restyle_paragraph(p)
                if headerish and ri == 0:
                    _clear_shading(cell)
                    shade_cell(cell, CALLOUT_FILL)
                    for p in cell.paragraphs:
                        for r in p.runs:
                            r.font.bold = True
                elif headerish and not _has_image(cell):
                    _clear_shading(cell)
                elif (not headerish) and ci == 0 and len(row.cells) == 2:
                    shade_cell(cell, LABEL_FILL)

    fit_change_history(doc)

    if banner:
        add_banner(doc)
    build_footer(doc, doc_id, marking, tlp=tlp, copyright_line=copyright_line)

    cp = doc.core_properties
    cp.comments = ("GeneLabs Enterprise Information Security | "
                   "Cyber Threat Intelligence")
    doc.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--doc-id", required=True)
    ap.add_argument("--marking", default="CTI Program Documentation")
    ap.add_argument("--tlp", default="AMBER")
    ap.add_argument("--copyright", default="")
    ap.add_argument("--no-banner", action="store_true")
    ap.add_argument("--no-table-headers", action="store_true")
    ap.add_argument("--promote-headings", action="store_true",
                    help="shift heading levels so top level sections are Heading 1")
    ap.add_argument("--strip-watermark", action="store_true",
                    help="remove a stale DRAFT watermark from the header")
    a = ap.parse_args()
    print("wrote", restyle(a.infile, a.outfile, a.doc_id, a.marking, a.tlp,
                           a.copyright, banner=not a.no_banner,
                           table_headers=not a.no_table_headers,
                           promote=a.promote_headings,
                           watermark=not a.strip_watermark))


if __name__ == "__main__":
    main()
