#!/usr/bin/env python3
"""
Build an GeneLabs Threat Hunt REPORT .docx from a JSON spec, using the bundled
GeneLabs template (assets/hunt_template.docx) for branding. Mirrors April's
CTI2602 house structure: metadata header table, ABLE hypotheses, per-source
Splunk tstats query chains (against the accelerated data models in
references/splunk_datamodels.md) plus CrowdStrike Falcon starters, an IOC
Inventory table, MITRE ATT&CK & D3FEND mappings, recommended saved searches,
a findings-classification key, a Coverage & Gaps roll-up, and (for unexecuted packages only) blank execution/outcome sections.

Usage:
    python build_hunt.py spec.json out.docx [path/to/hunt_template.docx]

See SKILL.md for the full JSON schema.
"""
import datetime
import json
import os
import re
import sys
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ---- GeneLabs corporate palette (shared with the genelabs-cti-bulletin skill)
ORANGE = "E05F00"            # deepened GeneLabs orange for small heading text
ORANGE_RULE = "FF7109"       # GeneLabs orange, sampled from the corporate deck rule
ABBEY = "444648"             # GeneLabs Abbey, body and headline text
BLUE = "1565C0"              # link blue
BOX_FILL = "FFF4E8"          # warm callout tint
CODE_FILL = "F1F3F4"
HDR_FILL = "F4F4F4"
GREY = "676765"              # corporate grey
GENELABS_ORANGE = "E05F00"   # table header fill
ZEBRA = "FFF8F2"             # very light warm row stripe
META_LABEL = "F4F4F4"        # label cells for the metadata header
BORDER = "D9D9D9"            # light grey: Word keeps it light on a dark canvas (verified)
WHITE = "FFFFFF"
FONT = "Arial"
COPYRIGHT_HOLDER = "GeneLabs LLC"
FOOTER_LABEL = "CTI Threat Hunt Report"
DEFAULT_TLP = "AMBER+STRICT"
SERVICENOW_URL = ("https://<your-instance>.service-now.com/esp?id=sc_cat_item"
                  "&sys_id=2498318b4fee53c0f628d0af0310c75d")
PRIO = {"CRITICAL": "B71C1C", "HIGH": "C62828", "MEDIUM": "EF6C00",
        "LOW": "2E7D32", "INFORMATIONAL": "1565C0"}
CLASS_COLOR = {
    "confirmed compromise": "B71C1C", "confirmed": "B71C1C",
    "suspicious activity": "EF6C00", "suspicious": "EF6C00",
    "benign / false positive": "2E7D32", "benign": "2E7D32", "false positive": "2E7D32",
    "inconclusive": "676765",
    "environmental gap": "6A1B9A",
    "detection engineering need": "1565C0",
    "informational / context": "00796B", "informational": "00796B",
}


def _class_color(label):
    return CLASS_COLOR.get(str(label).strip().lower(), GREY)


def _shade(p, fill):
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), fill)
    pPr.append(shd)


def _cell_shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), fill)
    tcPr.append(shd)


def _table_borders(table, color=BORDER, size="6"):
    tblPr = table._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement(f'w:{edge}')
        e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), size)
        e.set(qn('w:space'), '0'); e.set(qn('w:color'), color)
        borders.append(e)
    tblPr.append(borders)


def _para_border(p, edge, color, sz=6, space=0):
    pPr = p._p.get_or_add_pPr()
    bdr = pPr.find(qn('w:pBdr'))
    if bdr is None:
        bdr = OxmlElement('w:pBdr'); pPr.append(bdr)
    e = OxmlElement('w:' + edge)
    e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), str(sz))
    e.set(qn('w:space'), str(space)); e.set(qn('w:color'), color)
    bdr.append(e)


def _fixed_layout(table, total_width):
    tblPr = table._tbl.tblPr
    lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblPr.append(lay)
    w = OxmlElement('w:tblW')
    w.set(qn('w:w'), str(int(total_width.twips))); w.set(qn('w:type'), 'dxa')
    tblPr.append(w)


def _set_grid(table, widths):
    grid = table._tbl.find(qn('w:tblGrid'))
    if grid is None:
        grid = OxmlElement('w:tblGrid'); table._tbl.insert(1, grid)
    for gc in list(grid):
        grid.remove(gc)
    for w in widths:
        gc = OxmlElement('w:gridCol'); gc.set(qn('w:w'), str(int(w.twips))); grid.append(gc)
    for row in table.rows:
        for cell, w in zip(row.cells, widths):
            cell.width = w


def _footer_field(p, instr):
    r = p.add_run(); r.font.name = FONT; r.font.size = Pt(8)
    r.font.color.rgb = RGBColor.from_string(GREY)
    fld = OxmlElement('w:fldChar'); fld.set(qn('w:fldCharType'), 'begin')
    it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = instr
    sep = OxmlElement('w:fldChar'); sep.set(qn('w:fldCharType'), 'separate')
    t = OxmlElement('w:t'); t.text = "1"
    end = OxmlElement('w:fldChar'); end.set(qn('w:fldCharType'), 'end')
    for el in (fld, it, sep, t, end):
        r._element.append(el)
    return r


def _frun(p, text, size=8, bold=False, italic=False, color=ABBEY):
    r = p.add_run(text)
    r.font.name = FONT; r.font.size = Pt(size); r.font.bold = bold; r.font.italic = italic
    r.font.color.rgb = RGBColor.from_string(color)
    return r


def _copyright(date_str):
    m = re.search(r"(20\d{2})", str(date_str or ""))
    year = m.group(1) if m else str(datetime.date.today().year)
    return "\u00a9 %s %s All rights reserved." % (year, COPYRIGHT_HOLDER)


DEFAULT_WORDMARK = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "assets", "genelabs_wordmark_grey.png")


def build_footer(doc, hunt_id, tlp, copyright_line, wordmark_path=None):
    """GeneLabs brand furniture: wordmark, TLP, DOC # and live page numbers."""
    wordmark_path = wordmark_path or DEFAULT_WORDMARK
    footer = doc.sections[0].footer
    for p in list(footer.paragraphs):
        p._element.getparent().remove(p._element)
    for t in list(footer.tables):
        t._tbl.getparent().remove(t._tbl)

    rule = footer.add_paragraph()
    rule.paragraph_format.space_before = Pt(0)
    rule.paragraph_format.space_after = Pt(4)
    _para_border(rule, 'top', ORANGE_RULE, sz=12, space=1)

    table = footer.add_table(rows=1, cols=3, width=Inches(6.9))
    table.autofit = False
    _fixed_layout(table, Inches(6.9))
    widths = (Inches(1.25), Inches(3.55), Inches(2.10))
    _set_grid(table, widths)
    cells = table.rows[0].cells

    p0 = cells[0].paragraphs[0]
    p0.paragraph_format.space_after = Pt(0)
    if os.path.exists(wordmark_path):
        p0.add_run().add_picture(wordmark_path, width=Inches(0.95))

    p1 = cells[1].paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_after = Pt(0)
    _frun(p1, "TLP: ", bold=True, italic=True)
    _frun(p1, tlp, bold=True, italic=True, color=PRIO["MEDIUM"])
    _frun(p1, "  |  " + FOOTER_LABEL, color=GREY)
    p1b = cells[1].add_paragraph()
    p1b.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1b.paragraph_format.space_after = Pt(0)
    _frun(p1b, copyright_line, size=7, color=GREY)

    p2 = cells[2].paragraphs[0]
    p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p2.paragraph_format.space_after = Pt(0)
    _frun(p2, "DOC # ", bold=True)
    _frun(p2, str(hunt_id), color=GREY)
    p2b = cells[2].add_paragraph()
    p2b.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p2b.paragraph_format.space_after = Pt(0)
    _frun(p2b, "Page ", color=GREY)
    _footer_field(p2b, " PAGE ")
    _frun(p2b, " of ", color=GREY)
    _footer_field(p2b, " NUMPAGES ")


def set_base_style(doc):
    st = doc.styles['Normal']
    st.font.name = FONT
    st.font.size = Pt(10)
    st.font.color.rgb = RGBColor.from_string(ABBEY)
    rpr = st.element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts'); rpr.insert(0, rf)
    for a in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        rf.set(qn(a), FONT)


def _p(doc, text="", size=10, bold=False, color=None, after=6, before=0, italic=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    if text:
        r = p.add_run(text)
        r.font.name = FONT; r.font.size = Pt(size); r.font.bold = bold; r.font.italic = italic
        r.font.color.rgb = RGBColor.from_string(color or ABBEY)
    return p


def add_hyperlink(paragraph, url, text):
    part = paragraph.part
    r_id = part.relate_to(
        url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True)
    h = OxmlElement('w:hyperlink'); h.set(qn('r:id'), r_id)
    r = OxmlElement('w:r'); rPr = OxmlElement('w:rPr')
    for tag, attr, val in (('w:rStyle', 'w:val', 'Hyperlink'), ('w:color', 'w:val', BLUE),
                           ('w:u', 'w:val', 'single'), ('w:sz', 'w:val', '18')):
        e = OxmlElement(tag); e.set(qn(attr), val); rPr.append(e)
    rf = OxmlElement('w:rFonts'); rf.set(qn('w:ascii'), FONT); rf.set(qn('w:hAnsi'), FONT); rPr.append(rf)
    r.append(rPr)
    t = OxmlElement('w:t'); t.text = text; r.append(t)
    h.append(r); paragraph._p.append(h)


_BM = [900]


def add_bookmark(paragraph, name):
    """Wrap a paragraph in a Word bookmark so PAGEREF / internal links can target it."""
    _BM[0] += 1
    bid = str(_BM[0])
    st = OxmlElement('w:bookmarkStart'); st.set(qn('w:id'), bid); st.set(qn('w:name'), name)
    en = OxmlElement('w:bookmarkEnd'); en.set(qn('w:id'), bid)
    paragraph._p.insert(0, st); paragraph._p.append(en)
    return name


def add_pageref(paragraph, bookmark, size=9, bold=False):
    """Insert a PAGEREF field pointing at a bookmark. Word resolves it on field update."""
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), ' PAGEREF %s \\h ' % bookmark)
    r = OxmlElement('w:r'); rPr = OxmlElement('w:rPr')
    rf = OxmlElement('w:rFonts'); rf.set(qn('w:ascii'), FONT); rf.set(qn('w:hAnsi'), FONT); rPr.append(rf)
    sz = OxmlElement('w:sz'); sz.set(qn('w:val'), str(int(size * 2))); rPr.append(sz)
    if bold:
        b = OxmlElement('w:b'); rPr.append(b)
    r.append(rPr)
    t = OxmlElement('w:t'); t.text = "\u2013"; r.append(t)
    fld.append(r); paragraph._p.append(fld)


def add_internal_link(paragraph, bookmark, text, size=9, bold=False, color=BLUE):
    """Clickable cross-reference to a bookmark inside the same document."""
    h = OxmlElement('w:hyperlink'); h.set(qn('w:anchor'), bookmark)
    r = OxmlElement('w:r'); rPr = OxmlElement('w:rPr')
    for tag, attr, val in (('w:color', 'w:val', color), ('w:u', 'w:val', 'single'),
                           ('w:sz', 'w:val', str(int(size * 2)))):
        e = OxmlElement(tag); e.set(qn(attr), val); rPr.append(e)
    if bold:
        rPr.append(OxmlElement('w:b'))
    rf = OxmlElement('w:rFonts'); rf.set(qn('w:ascii'), FONT); rf.set(qn('w:hAnsi'), FONT); rPr.append(rf)
    r.append(rPr)
    t = OxmlElement('w:t'); t.text = text; r.append(t)
    h.append(r); paragraph._p.append(h)


def _accent_bar(doc, text, color, size=10.5, fill=None):
    """Finding header: coloured left accent bar + bold coloured title."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(9); p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Inches(0.02)
    if fill:
        _shade(p, fill)
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement('w:pBdr')
    left = OxmlElement('w:left')
    left.set(qn('w:val'), 'single'); left.set(qn('w:sz'), '24')
    left.set(qn('w:space'), '6'); left.set(qn('w:color'), color)
    bdr.append(left); pPr.append(bdr)
    r = p.add_run(text); r.font.name = FONT; r.font.size = Pt(size)
    r.font.bold = True; r.font.color.rgb = RGBColor.from_string(color)
    return p


def _chip_row(doc, pairs):
    """Compact Type / Confidence / Classification strip under a finding header."""
    pairs = [(k, v) for k, v in pairs if v]
    if not pairs:
        return
    t = doc.add_table(rows=1, cols=len(pairs)); t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    _table_borders(t)
    for j, (k, v) in enumerate(pairs):
        c = t.rows[0].cells[j]; _cell_shade(c, HDR_FILL)
        c.paragraphs[0].text = ""
        rk = c.paragraphs[0].add_run(k.upper() + "  ")
        rk.font.name = FONT; rk.font.size = Pt(7); rk.font.bold = True
        rk.font.color.rgb = RGBColor.from_string(GREY)
        rv = c.paragraphs[0].add_run(v)
        rv.font.name = FONT; rv.font.size = Pt(9); rv.font.bold = True
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def _render_queries(doc, items, code_key, default_src=""):
    """Render a list of query entries. Each item may be a dict
    {name, source/event, purpose, <code_key>} or a bare code string."""
    for q in items:
        if isinstance(q, str):
            code_block(doc, q)
            continue
        label = q.get("name", "")
        src = q.get("source") or q.get("event") or default_src
        head = doc.add_paragraph(); head.paragraph_format.space_after = Pt(1)
        head.paragraph_format.space_before = Pt(4)
        rr = head.add_run(label); rr.font.name = FONT; rr.font.size = Pt(10); rr.font.bold = True
        if src:
            rs = head.add_run(f"   [{src}]"); rs.font.name = FONT; rs.font.size = Pt(9)
            rs.font.color.rgb = RGBColor.from_string(GREY)
        if q.get("purpose"):
            _p(doc, q["purpose"], size=9, italic=True, color=GREY, after=2)
        code_block(doc, q.get(code_key, q.get("spl", q.get("cql", ""))))


def h_title(doc, text):
    p = _p(doc, text, size=16, bold=True, color=ABBEY, after=3)
    p.paragraph_format.line_spacing = 1.0
    return p


def h_section(doc, text):
    """Letterspaced small caps heading underlined in GeneLabs orange."""
    p = _p(doc, "", before=12, after=4)
    r = p.add_run(text.upper())
    r.font.name = FONT; r.font.size = Pt(10); r.font.bold = True
    r.font.color.rgb = RGBColor.from_string(ORANGE)
    rpr = r._element.get_or_add_rPr()
    sp = OxmlElement('w:spacing'); sp.set(qn('w:val'), '20'); rpr.append(sp)
    _para_border(p, 'bottom', ORANGE_RULE, sz=12, space=3)
    pPr = p._p.get_or_add_pPr()
    pPr.append(OxmlElement('w:keepNext'))
    return p


def h_label_value(doc, label, value, indent=0.0):
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(2)
    if indent:
        p.paragraph_format.left_indent = Inches(indent)
    r1 = p.add_run(label + ": "); r1.font.name = FONT; r1.font.size = Pt(10); r1.font.bold = True
    r2 = p.add_run(value); r2.font.name = FONT; r2.font.size = Pt(10)


def code_block(doc, text):
    for ln in text.split("\n"):
        p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.left_indent = Inches(0.15)
        _shade(p, CODE_FILL)
        r = p.add_run(ln if ln else " "); r.font.name = "Consolas"; r.font.size = Pt(8.5)


def bullets(doc, items, indent=0.25):
    for it in items:
        p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.left_indent = Inches(indent)
        pre = p.add_run("\u25aa  ")
        pre.font.name = FONT; pre.font.size = Pt(9); pre.font.bold = True
        pre.font.color.rgb = RGBColor.from_string(ORANGE_RULE)
        r = p.add_run(it); r.font.name = FONT; r.font.size = Pt(10)
        r.font.color.rgb = RGBColor.from_string(ABBEY)


def grid_table(doc, headers, rows, widths=None, header_fill=GENELABS_ORANGE, font_size=9):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"; table.alignment = WD_TABLE_ALIGNMENT.LEFT
    _table_borders(table)
    for j, h in enumerate(headers):
        c = table.rows[0].cells[j]; _cell_shade(c, header_fill)
        c.paragraphs[0].text = ""
        r = c.paragraphs[0].add_run(h); r.font.name = FONT; r.font.size = Pt(font_size)
        r.font.bold = True; r.font.color.rgb = RGBColor.from_string(WHITE)
    for i, row in enumerate(rows):
        cells = table.add_row().cells
        for j, val in enumerate(row):
            if i % 2 == 1:
                _cell_shade(cells[j], ZEBRA)
            cells[j].paragraphs[0].text = ""
            r = cells[j].paragraphs[0].add_run(str(val)); r.font.name = FONT; r.font.size = Pt(font_size)
    if widths:
        for j, w in enumerate(widths):
            for row in table.rows:
                row.cells[j].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def meta_table(doc, hid, meta, status):
    rows = [
        ["Hunt Title", meta.get("hunt_title", hid), "Status", status],
        ["Trigger Source", meta.get("trigger_source", ""), "Start Date", meta.get("start_date", "")],
        ["IOC Type(s)", meta.get("ioc_types", ""), "End Date", meta.get("end_date", "")],
        ["Campaign/Actor Tags", meta.get("campaign_actor_tags", "N/A"), "Reviewed By", meta.get("reviewed_by", "[Pending Review]")],
    ]
    # Optional analyst-role rows — only rendered if any role is explicitly provided.
    role_keys = ("hunt_lead", "scribe", "ti_threatq", "crowdstrike", "proofpoint", "splunk")
    if any(meta.get(k) for k in role_keys):
        rows += [
            ["Hunt Lead", meta.get("hunt_lead", ""), "Scribe", meta.get("scribe", "")],
            ["TI (ThreatQ)", meta.get("ti_threatq", ""), "CrowdStrike", meta.get("crowdstrike", "")],
            ["Proofpoint", meta.get("proofpoint", ""), "Splunk", meta.get("splunk", "")],
        ]
    t = doc.add_table(rows=0, cols=4); t.style = "Table Grid"
    _table_borders(t)
    for a, b, c, d in rows:
        cells = t.add_row().cells
        for cell, val, bold in ((cells[0], a, True), (cells[1], b, False),
                                (cells[2], c, True), (cells[3], d, False)):
            _cell_shade(cell, META_LABEL if (bold and val) else WHITE)
            cell.paragraphs[0].text = ""
            r = cell.paragraphs[0].add_run(val); r.font.name = FONT; r.font.size = Pt(9); r.font.bold = bold
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


GAP_CLASSES = ("environmental gap", "detection engineering need")


def _gap_items(spec):
    """Explicit spec gaps plus any finding classified as a coverage gap."""
    items = list(spec.get("gaps", []) or [])
    seen = {(g.get("title") or "").lower() for g in items}
    for f in spec.get("findings", []) or []:
        if (f.get("classification", "") or "").strip().lower() in GAP_CLASSES:
            if (f.get("title", "") or "").lower() in seen:
                continue
            items.append({
                "title": f.get("title", ""),
                "category": f.get("type", ""),
                "classification": f.get("classification", ""),
                "detail": f.get("evidence", ""),
                "impact": f.get("impact_rationale", ""),
                "remedy": f.get("recommendation", ""),
                "finding_num": f.get("num"),
            })
    return items


def add_exec_summary(doc, spec):
    """Overall finding + a linked index of findings with page numbers. Sits directly
    under the metadata table so the verdict is the first thing read."""
    ov = spec.get("overall_finding")
    findings = spec.get("findings", []) or []
    if not ov and not findings:
        return
    _p(doc, "", before=4)
    h_section(doc, "Investigation Summary")
    if spec.get("investigation_note"):
        _p(doc, spec["investigation_note"], size=9, italic=True, color=GREY, after=3)
    if ov:
        col = _class_color(ov.get("verdict", ""))
        p = doc.add_paragraph(); _shade(p, BOX_FILL)
        p.paragraph_format.space_after = Pt(3); p.paragraph_format.space_before = Pt(2)
        r1 = p.add_run("Overall Finding:  "); r1.font.name = FONT; r1.font.size = Pt(10); r1.font.bold = True
        r2 = p.add_run(ov.get("verdict", "")); r2.font.name = FONT; r2.font.size = Pt(10)
        r2.font.bold = True; r2.font.color.rgb = RGBColor.from_string(col)
        if ov.get("explanation"):
            _p(doc, ov["explanation"], size=10, after=4)
    if not findings:
        return
    _p(doc, "Findings index — click a title to jump to the detail, or see the page column.",
       size=9, italic=True, color=GREY, after=2)
    headers = ["#", "Finding", "Classification", "Page"]
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    _table_borders(t)
    for j, h in enumerate(headers):
        c = t.rows[0].cells[j]; _cell_shade(c, GENELABS_ORANGE); c.paragraphs[0].text = ""
        r = c.paragraphs[0].add_run(h); r.font.name = FONT; r.font.size = Pt(9)
        r.font.bold = True; r.font.color.rgb = RGBColor.from_string(WHITE)
    for i, f in enumerate(findings):
        num = f.get("num", i + 1)
        bm = "FIND%s" % num
        cells = t.add_row().cells
        if i % 2 == 1:
            for c in cells:
                _cell_shade(c, ZEBRA)
        cells[0].paragraphs[0].text = ""
        r = cells[0].paragraphs[0].add_run(str(num)); r.font.name = FONT; r.font.size = Pt(9); r.font.bold = True
        cells[1].paragraphs[0].text = ""
        add_internal_link(cells[1].paragraphs[0], bm, f.get("title", ""), size=9)
        cells[2].paragraphs[0].text = ""
        cl = f.get("classification", "")
        rc = cells[2].paragraphs[0].add_run(cl); rc.font.name = FONT; rc.font.size = Pt(9)
        rc.font.bold = True; rc.font.color.rgb = RGBColor.from_string(_class_color(cl))
        cells[3].paragraphs[0].text = ""
        add_pageref(cells[3].paragraphs[0], bm, size=9)
    for j, w in enumerate([0.4, 3.6, 1.9, 0.5]):
        for row in t.rows:
            row.cells[j].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    _p(doc, "Page numbers are Word fields. Press Ctrl+A then F9 to refresh them after opening.",
       size=8, italic=True, color=GREY, after=4)


def add_gaps(doc, spec):
    """Coverage & Gaps — telemetry, licensing and configuration limits found during the hunt."""
    items = _gap_items(spec)
    if not items:
        return
    _p(doc, "", before=8)
    h_section(doc, "Coverage & Gaps — Telemetry, Licensing, Configuration")
    _p(doc, "Limits encountered during this hunt that constrain what the results can prove. "
            "These are not negative findings; they are things the hunt could not see.",
       size=9, italic=True, color=GREY, after=3)
    rows = []
    for g in items:
        ref = ("Finding %s" % g["finding_num"]) if g.get("finding_num") else ""
        rows.append([g.get("category", ""), g.get("title", ""),
                     g.get("classification", ""), ref])
    grid_table(doc, ["Area", "Gap", "Classification", "Ref"], rows,
               widths=[1.5, 3.4, 1.6, 0.7])
    for g in items:
        col = _class_color(g.get("classification", "")) or GREY
        _accent_bar(doc, g.get("title", ""), col, size=10)
        if g.get("detail"):
            _p(doc, g["detail"], size=9, after=2)
        if g.get("impact"):
            _p(doc, "Why it matters: ", size=9, bold=True, color=GREY, after=1)
            _p(doc, g["impact"], size=9, after=2)
        rem = g.get("remedy")
        if rem:
            _p(doc, "To close it:", size=9, bold=True, color=GREY, after=1)
            if isinstance(rem, list):
                bullets(doc, rem)
            else:
                _p(doc, rem, size=9)


def add_findings(doc, spec):
    """Detailed findings. The verdict and index already appeared in the Investigation Summary."""
    findings = spec.get("findings", []) or []
    if not findings:
        return
    _p(doc, "", before=8)
    h_section(doc, "Findings — Detail")
    for i, f in enumerate(findings, 1):
        num = f.get("num", i)
        cl = f.get("classification", "")
        col = _class_color(cl)
        p = _accent_bar(doc, "Finding %s — %s" % (num, f.get("title", "")), col, size=10.5, fill=HDR_FILL)
        add_bookmark(p, "FIND%s" % num)
        _chip_row(doc, [("Type", f.get("type", "")),
                        ("Confidence", f.get("confidence", "")),
                        ("Classification", cl)])
        for label, key, sz in (("Evidence (Falcon)", "evidence", 9.5),
                               ("Impact & Classification Rationale", "impact_rationale", 9.5)):
            if f.get(key):
                _p(doc, label, size=8, bold=True, color=GREY, after=1, before=3)
                _p(doc, f[key], size=sz)
        if f.get("recommendation"):
            _p(doc, "Recommendation", size=8, bold=True, color=GREY, after=1, before=3)
            if isinstance(f["recommendation"], list):
                bullets(doc, f["recommendation"])
            else:
                _p(doc, f["recommendation"], size=9.5)
        if f.get("detection_opportunity"):
            _p(doc, "Detection Opportunity", size=8, bold=True, color=GREY, after=1, before=3)
            _p(doc, f["detection_opportunity"], size=9.5)


def build(spec, template_path, out_path):
    doc = Document(template_path)
    set_base_style(doc)
    hid = spec.get("hunt_id", "TH-26-XX")
    # header line
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run(f"{hid}  |  {spec.get('date','')}")
    r.font.name = FONT; r.font.size = Pt(9); r.font.bold = True
    h_title(doc, spec.get("doc_title", "Threat Hunt Report"))
    sub = spec.get("subtitle") or (
        "Completed hunt report — executed %s. Hypothesis verdicts and findings below."
        % spec.get("run_date", spec.get("date", "")))
    _p(doc, sub, size=10, italic=True, color=GREY, after=4)
    meta_table(doc, hid, spec.get("meta", {}), spec.get("status", "Proposed"))

    # Investigated hunts lead with the verdict + a linked findings index.
    add_exec_summary(doc, spec)

    # How-to-run handoff callout (e.g., open in Claude desktop and investigate via falcon-mcp)
    if spec.get("handoff_note"):
        p = doc.add_paragraph(); _shade(p, BOX_FILL); p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.space_before = Pt(2)
        r1 = p.add_run("How to run this hunt:  "); r1.font.name = FONT; r1.font.size = Pt(10); r1.font.bold = True
        r2 = p.add_run(spec["handoff_note"]); r2.font.name = FONT; r2.font.size = Pt(10)

    for i, hyp in enumerate(spec.get("hypotheses", []), 1):
        _p(doc, "", after=2)
        p = doc.add_paragraph(); _shade(p, BOX_FILL); p.paragraph_format.space_after = Pt(3)
        r = p.add_run(f"  Hypothesis {i} — {hyp['title']}  ")
        r.font.name = FONT; r.font.size = Pt(11); r.font.bold = True
        if hyp.get("priority"):
            key = str(hyp["priority"]).split()[0].upper()
            hl = h_label_value(doc, "Priority", "")
            pv = doc.paragraphs[-1]
            rr = pv.add_run(hyp["priority"]); rr.font.name = FONT; rr.font.size = Pt(10)
            rr.font.bold = True; rr.font.color.rgb = RGBColor.from_string(PRIO.get(key, "000000"))
        if hyp.get("trigger_type"):
            h_label_value(doc, "Trigger type", hyp["trigger_type"])

        h_section(doc, "Hypothesis (ABLE)")
        able = hyp.get("able", {})
        for k in ("actor", "behavior", "location", "evidence"):
            if able.get(k):
                h_label_value(doc, k.capitalize(), able[k], indent=0.15)
        if hyp.get("hypothesis"):
            _p(doc, hyp["hypothesis"], size=10, before=2)

        ds = hyp.get("data_sources")
        if ds:
            # CQL-only package (no Splunk queries): strip any Splunk/tstats data-source lines.
            if not hyp.get("queries"):
                ds = [d for d in ds if "splunk" not in d.lower() and "tstats" not in d.lower()]
            if ds:
                h_section(doc, "Data Sources Used")
                bullets(doc, ds)

        # CrowdStrike Falcon CQL (LogScale) — the primary/only query set.
        if hyp.get("falcon"):
            suffix = " — primary" if hyp.get("queries") else ""
            h_section(doc, "CrowdStrike CTI Threat Hunting Automation Queries (CQL / LogScale)" + suffix)
            _render_queries(doc, hyp["falcon"], code_key="cql", default_src="Falcon")

        # OPTIONAL supporting Splunk tstats (omitted in CQL-only packages).
        if hyp.get("queries"):
            h_section(doc, "Supporting Splunk Queries (tstats)")
            _render_queries(doc, hyp["queries"], code_key="spl", default_src="")

        if hyp.get("attack"):
            h_section(doc, "MITRE ATT&CK & D3FEND")
            grid_table(doc, ["ATT&CK", "Tactic / Technique", "D3FEND", "Defense Concept", "Coverage"],
                       [[a.get("id", ""), a.get("tactic_technique", ""), a.get("d3fend", ""),
                         a.get("defense", ""), a.get("coverage", "")] for a in hyp["attack"]],
                       widths=[0.8, 2.2, 1.1, 1.7, 1.0])

        if hyp.get("expected"):
            h_section(doc, "Expected Findings (benign vs. malicious)")
            _p(doc, hyp["expected"], size=10)

        h_section(doc, "Intelligence Sources")
        for s in hyp.get("sources", []):
            p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(2); p.paragraph_format.left_indent = Inches(0.25)
            pre = p.add_run("\u25aa  ")
            pre.font.name = FONT; pre.font.size = Pt(9); pre.font.bold = True
            pre.font.color.rgb = RGBColor.from_string(ORANGE_RULE)
            if s.get("url"):
                add_hyperlink(p, s["url"], s.get("title", s["url"]))
            else:
                r = p.add_run(s.get("title", "")); r.font.name = FONT; r.font.size = Pt(10)

        # Blank execution/outcome sections are only useful on an UNEXECUTED package.
        # Once findings exist they are dead space, so they are suppressed.
        if not (spec.get("findings") or spec.get("overall_finding")) and spec.get("blank_sections", True):
            h_section(doc, "Execution Log (to complete)")
            _p(doc, "Queries run, data range, hosts/users reviewed, evidence exports:", size=10, color=GREY)
            _p(doc, "________________________________________________", size=10, color="BBBBBB")
            h_section(doc, "Outcome & Classification (to complete)")
            _p(doc, "Classification, findings, detections to build, gaps, follow-up hunts:", size=10, color=GREY)
            _p(doc, "________________________________________________", size=10, color="BBBBBB")

    # Detailed findings, then the coverage/gaps roll-up.
    add_findings(doc, spec)
    add_gaps(doc, spec)

    # IOC inventory
    if spec.get("iocs"):
        _p(doc, "", before=8)
        h_section(doc, "IOC Inventory")
        grid_table(doc, ["Type", "Indicator / Value", "Source", "Notes"],
                   [[c.get("type", ""), c.get("value", ""), c.get("source", ""), c.get("notes", "")]
                    for c in spec["iocs"]], widths=[1.2, 2.6, 1.3, 1.7])

    # Recommended saved searches
    if spec.get("saved_searches"):
        h_section(doc, "Recommended Production Saved Searches (Splunk SPL)")
        for s in spec["saved_searches"]:
            _p(doc, s.get("name", ""), size=10, bold=True, after=1, before=3)
            code_block(doc, s.get("spl", ""))

    # ATT&CK consolidated — only worth a second table when there are multiple
    # hypotheses to consolidate. With one hypothesis it duplicates the per-hypothesis
    # table verbatim, so it is suppressed.
    if spec.get("attack_summary") and len(spec.get("hypotheses", [])) > 1:
        h_section(doc, "MITRE ATT&CK & D3FEND — Summary")
        grid_table(doc, ["ATT&CK", "Tactic / Technique", "D3FEND", "Defense Concept", "Coverage"],
                   [[a.get("id", ""), a.get("tactic_technique", ""), a.get("d3fend", ""),
                     a.get("defense", ""), a.get("coverage", "")] for a in spec["attack_summary"]],
                   widths=[0.8, 2.2, 1.1, 1.7, 1.0])

    # Classifications key
    if spec.get("include_classifications", True):
        h_section(doc, "Findings Classification Key")
        grid_table(doc, ["Classification", "When to Use"], [
            ["Confirmed Compromise", "IOC or behavior directly maps to a known threat or exposure in the environment"],
            ["Suspicious Activity", "Matching indicators or behavior, not yet validated as actively exploited"],
            ["Benign / False Positive", "Triggered logic, found to be legitimate business or user activity"],
            ["Inconclusive", "Insufficient telemetry or context to confirm either way"],
            ["Environmental Gap", "Logging, visibility, or normalization missing (e.g., no normalized telemetry)"],
            ["Detection Engineering Need", "A detection gap exists that cannot currently be alerted on"],
            ["Informational / Context", "Insightful but not action-requiring; enrichment only"],
        ], widths=[1.9, 5.0])

    _p(doc, "", before=8)
    footer = spec.get("closing_note") or (
        "Completed Threat Hunt Report. CQL queries were executed against CrowdStrike Falcon "
        "telemetry within the stated hunt window; Splunk SPL saved searches are production "
        "recommendations run separately in Splunk ES. Findings reflect the evidence available "
        "at the time of the hunt — see Coverage & Gaps for what could not be assessed.")
    _p(doc, footer, size=8, italic=True, color=GREY)
    build_footer(doc, spec.get("hunt_id", ""), spec.get("tlp", DEFAULT_TLP),
                 _copyright(spec.get("date") or spec.get("run_date")))
    cp = doc.core_properties
    cp.title = "%s %s" % (spec.get("hunt_id", ""), (spec.get("meta") or {}).get("hunt_title", ""))
    cp.category = "Threat Hunt Report"
    cp.comments = "GeneLabs Enterprise Information Security | Cyber Threat Intelligence"
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    template = sys.argv[3] if len(sys.argv) > 3 else \
        __file__.rsplit("/", 2)[0] + "/assets/hunt_template.docx"
    if not (spec.get("findings") or spec.get("overall_finding")):
        sys.stderr.write("WARNING: spec has no findings/overall_finding. This builder produces a "
                         "COMPLETED report; for an unexecuted hunt use genelabs-threat-hunt-package.\n")
    print("wrote", build(spec, template, sys.argv[2]))
