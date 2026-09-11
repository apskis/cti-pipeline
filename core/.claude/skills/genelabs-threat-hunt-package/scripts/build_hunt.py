#!/usr/bin/env python3
"""
Build an GeneLabs Threat Hunt Package .docx from a JSON spec, using the bundled
GeneLabs template (assets/hunt_template.docx) for branding. Mirrors April's
CTI2602 house structure: metadata header table, ABLE hypotheses, per-source
Splunk tstats query chains (against the accelerated data models in
references/splunk_datamodels.md) plus CrowdStrike Falcon starters, an IOC
Inventory table, MITRE ATT&CK & D3FEND mappings and recommended saved searches.

A package is a WORK ORDER: it carries no findings, no verdicts, no classification
key, no Coverage & Gaps roll-up and no blank execution sections. Those belong to
the hunt REPORT, written after the hunt has run (2026-08-24, April).

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
FOOTER_LABEL = "CTI Threat Hunt Package"
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


def meta_table(doc, hid, meta):
    """Straight 2-column label/value header.

    Status, Start Date, End Date and Reviewed By were removed on 2026-08-24: all
    four rendered as placeholders ("Proposed", an empty date, "[Pending Review]").
    They are outcomes of running the hunt and belong to the report skill.
    """
    rows = [
        ["Hunt Title", meta.get("hunt_title", hid)],
        ["Trigger Source", meta.get("trigger_source", "")],
        ["IOC Type(s)", meta.get("ioc_types", "")],
        ["Campaign/Actor Tags", meta.get("campaign_actor_tags", "N/A")],
    ]
    # Optional analyst-role rows — only rendered if any role is explicitly provided.
    role_keys = ("hunt_lead", "scribe", "ti_threatq", "crowdstrike", "proofpoint", "splunk")
    labels = {"hunt_lead": "Hunt Lead", "scribe": "Scribe", "ti_threatq": "TI (ThreatQ)",
              "crowdstrike": "CrowdStrike", "proofpoint": "Proofpoint", "splunk": "Splunk"}
    rows += [[labels[k], meta[k]] for k in role_keys if meta.get(k)]
    t = doc.add_table(rows=0, cols=2); t.style = "Table Grid"
    _table_borders(t)
    for label, val in rows:
        cells = t.add_row().cells
        for cell, v, bold in ((cells[0], label, True), (cells[1], val, False)):
            _cell_shade(cell, META_LABEL if bold else WHITE)
            cell.paragraphs[0].text = ""
            r = cell.paragraphs[0].add_run(v); r.font.name = FONT; r.font.size = Pt(9); r.font.bold = bold
    for row in t.rows:
        row.cells[0].width = Inches(1.9); row.cells[1].width = Inches(5.0)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def build(spec, template_path, out_path):
    # The branded template is not shipped in the sanitized build; an unbranded
    # document still lets the pipeline deliver the content for review.
    if os.path.exists(template_path):
        doc = Document(template_path)
    else:
        print(f"template not found ({template_path}); building unbranded", file=sys.stderr)
        doc = Document()
    set_base_style(doc)
    hid = spec.get("hunt_id", "TH-26-XX")
    # header line
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run(f"{hid}  |  {spec.get('date','')}")
    r.font.name = FONT; r.font.size = Pt(9); r.font.bold = True
    h_title(doc, "Threat Hunt Package")
    _p(doc, f"Derived from the CTI daily scan run of {spec.get('run_date', spec.get('date',''))}",
       size=10, italic=True, color=GREY, after=4)
    meta_table(doc, hid, spec.get("meta", {}))

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
            grid_table(doc, ["ATT&CK", "Tactic / Technique", "D3FEND", "Defense Concept"],
                       [[a.get("id", ""), a.get("tactic_technique", ""), a.get("d3fend", ""),
                         a.get("defense", "")] for a in hyp["attack"]],
                       widths=[0.9, 2.6, 1.2, 2.1])

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
        grid_table(doc, ["ATT&CK", "Tactic / Technique", "D3FEND", "Defense Concept"],
                   [[a.get("id", ""), a.get("tactic_technique", ""), a.get("d3fend", ""),
                     a.get("defense", "")] for a in spec["attack_summary"]],
                   widths=[0.9, 2.6, 1.2, 2.1])



    _p(doc, "", before=8)
    footer = ("Generated from the CTI daily scan. CQL queries target CrowdStrike Falcon telemetry; "
              "any Splunk SPL saved searches target the accelerated data models. Validate field/event "
              "names and index macros against production before running.")
    _p(doc, footer, size=8, italic=True, color=GREY)
    build_footer(doc, spec.get("hunt_id", ""), spec.get("tlp", DEFAULT_TLP),
                 _copyright(spec.get("date") or spec.get("run_date")))
    cp = doc.core_properties
    cp.title = "%s %s" % (spec.get("hunt_id", ""), (spec.get("meta") or {}).get("hunt_title", ""))
    cp.category = "Threat Hunt Package"
    cp.comments = "GeneLabs Enterprise Information Security | Cyber Threat Intelligence"
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    template = sys.argv[3] if len(sys.argv) > 3 else \
        __file__.rsplit("/", 2)[0] + "/assets/hunt_template.docx"
    print("wrote", build(spec, template, sys.argv[2]))
