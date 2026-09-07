#!/usr/bin/env python3
"""GeneLabs CTI Detection Hand-off builder.

The document CTI sends to Security Monitoring when a finding yields deployable
detection logic. Report id `CTI-DET-<AssetSlug>`.

WHY IT IS NOT A SECTION OF THE EXPOSURE ADVISORY

April, 2026-08-27: "When sending findings to the monitoring/detection team, the report
should focus on two things: detection recommendations and validation steps — not the
exposure narrative itself."

The asset owner and the detection engineer need different documents. The owner needs to
know what is exposed, what it would cost, and what to change. The detection engineer
needs the logic, the threshold, the false positives and the way to prove it works. Each
audience treats the other's content as preamble to scroll past, and a document that tries
to serve both gets skimmed by everybody.

So this carries NO exposure narrative. One line of context, then detections.

STRUCTURE
  1. Context — ONE short paragraph. What was found, one sentence; what this document is
     for, one sentence. Not the story.
  2. Detections — one block each: what it catches, the deployable query, the threshold and
     why, known false positives, and the VALIDATION RESULT.
  3. Blocked detections — what cannot be built today, the gap that blocks it by TG-NN, and
     the exact detection that becomes available once the gap closes. This is the section
     that turns a gap register row into something someone will fund.
  4. Validation steps — how the SOC proves each detection for itself before deploying.

EVERY DETECTION MUST CARRY A VALIDATION RESULT. A detection recommendation that has never
been executed is a guess, and the SOC will find that out at deployment rather than at
review. Run it, record what it returned, and say plainly where it returned nothing.

Usage:
  python build_detection_handoff.py spec.json out.docx <genelabs-cti-bulletin skill dir>
"""
import json, os, sys, glob

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ORANGE, ORANGE_DEEP = "FF7109", "E05F00"
ABBEY, GREY = "444648", "676765"
TINT, LIGHT, RULE = "FFF4E8", "F4F4F4", "D9D9D9"
GREEN, RED = "2E7D32", "C62828"

HERE = os.path.dirname(os.path.abspath(__file__))


def _rgb(h):
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _run(p, text, size=10, bold=False, italic=False, color=ABBEY, font="Arial", caps=False):
    r = p.add_run(text.upper() if caps else text)
    r.font.name = font; r.font.size = Pt(size)
    r.font.bold = bold; r.font.italic = italic
    r.font.color.rgb = _rgb(color)
    rpr = r._element.get_or_add_rPr()
    rf = OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:cs"):
        rf.set(qn(a), font)
    rpr.append(rf)
    if caps:
        sp = OxmlElement("w:spacing"); sp.set(qn("w:val"), "30"); rpr.append(sp)
    return r


def _para(doc, before=0, after=4, indent=0.0):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.12
    if indent:
        p.paragraph_format.left_indent = Inches(indent)
    return p


def _shade(el, fill):
    sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:fill"), fill); el.append(sh)


def _heading(doc, text, before=10):
    p = _para(doc, before=before, after=3)
    _run(p, text, 10.5, bold=True, color=ORANGE_DEEP, caps=True)
    pPr = p._p.get_or_add_pPr()
    b = OxmlElement("w:pBdr"); bot = OxmlElement("w:bottom")
    bot.set(qn("w:val"), "single"); bot.set(qn("w:sz"), "12")
    bot.set(qn("w:space"), "2"); bot.set(qn("w:color"), ORANGE)
    b.append(bot); pPr.append(p_bdr := b)
    return p


def _figure(doc, figdir, name, width_in=5.7):
    """RETAINED BUT NOT CALLED. April removed behaviour pictures from this document on
    2026-08-27 — "remove the pictures from the soc handoff i dont like them". The helper is
    kept because behaviour_diagram.py is still useful elsewhere and reinstating a call is a
    one-line change; deleting it would mean rebuilding it from scratch if the decision moves.
    A `figure` key in a spec is now simply ignored."""
    import os as _os
    path = _os.path.join(figdir, f"{name}.png") if figdir else None
    if not path or not _os.path.exists(path):
        p = _para(doc, after=3, indent=0.02)
        _run(p, f"[figure missing: {name}]", 8, italic=True, color=RED)
        return
    p = _para(doc, before=2, after=4)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(path, width=Inches(width_in))


def _code(doc, text):
    """Consolas block, one paragraph per line so long queries wrap predictably."""
    for line in text.splitlines() or [""]:
        p = _para(doc, after=0, indent=0.14)
        _run(p, line or " ", 7.5, color=ABBEY, font="Consolas")


def _field(p, instr):
    for tag, txt in (("begin", None), (None, instr), ("end", None)):
        if tag:
            f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), tag)
            r = OxmlElement("w:r"); r.append(f); p._p.append(r)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt
            r = OxmlElement("w:r"); r.append(it); p._p.append(r)


def _footer(doc, skill_dir, report_id, tlp, marking="CTI Detection Hand-off"):
    f = doc.sections[0].footer
    for p in list(f.paragraphs):
        p._element.getparent().remove(p._element)
    line = f.add_paragraph()
    line.paragraph_format.space_before = Pt(2); line.paragraph_format.space_after = Pt(0)
    pPr = line._p.get_or_add_pPr()
    b = OxmlElement("w:pBdr"); top = OxmlElement("w:top")
    top.set(qn("w:val"), "single"); top.set(qn("w:sz"), "12")
    top.set(qn("w:space"), "4"); top.set(qn("w:color"), ORANGE)
    b.append(top); pPr.append(b)
    wm = glob.glob(os.path.join(skill_dir, "assets", "*wordmark*.png")) or \
         glob.glob(os.path.join(HERE, "assets", "*wordmark*.png"))
    if wm:
        _run(line, "", 8); line.runs[-1].add_picture(wm[0], width=Inches(0.62)); _run(line, "   ", 8)
    _run(line, "TLP: ", 7.5, color=GREY)
    _run(line, tlp, 7.5, color=ABBEY)
    _run(line, f"  |  {marking}  |  © 2026 GeneLabs LLC", 7.5, color=GREY)
    p2 = f.add_paragraph(); p2.paragraph_format.space_before = Pt(0)
    _run(p2, f"DOC # {report_id}    Page ", 7.5, color=GREY)
    _field(p2, " PAGE "); _run(p2, " of ", 7.5, color=GREY); _field(p2, " NUMPAGES ")


def _kv_table(doc, rows, widths=(1.5, 5.0)):
    t = doc.add_table(rows=len(rows), cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.LEFT; t.autofit = False
    for i, (k, v) in enumerate(rows):
        for j, (val, w) in enumerate(((k, widths[0]), (v, widths[1]))):
            c = t.rows[i].cells[j]; c.width = Inches(w)
            p = c.paragraphs[0]; p.text = ""
            p.paragraph_format.space_before = Pt(1.5); p.paragraph_format.space_after = Pt(1.5)
            _run(p, val, 8.5, bold=(j == 0), color=ABBEY)
        _shade(t.rows[i].cells[0]._tc.get_or_add_tcPr(), LIGHT)
    _borders(t)
    return t


def _borders(t):
    tbl = t._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "6")
        e.set(qn("w:space"), "0"); e.set(qn("w:color"), RULE)
        b.append(e)
    tbl.append(b)


def build(spec, out_docx, skill_dir, figdir=None):
    doc = Document()
    for s in doc.sections:
        s.top_margin = Inches(0.6); s.bottom_margin = Inches(0.6)
        s.left_margin = Inches(0.85); s.right_margin = Inches(0.85)

    rid = spec["report_id"]
    if not rid.startswith("CTI-DET-"):
        sys.exit("report_id must be CTI-DET-<AssetSlug>; got %r" % rid)

    k = _para(doc, after=1); _run(k, "CTI DETECTION HAND-OFF", 8.5, bold=True, color=ORANGE_DEEP, caps=True)
    h = _para(doc, after=3); _run(h, spec["title"], 15, bold=True, color=ABBEY)
    if spec.get("subtitle"):
        sp = _para(doc, after=6); _run(sp, spec["subtitle"], 9.5, color=GREY)

    if spec.get("doc_control"):
        _kv_table(doc, spec["doc_control"]); _para(doc, after=2)

    # ONE paragraph of context. Not the story.
    _heading(doc, "Why you are receiving this", before=6)
    for para in spec["context"]:
        p = _para(doc, after=4); _run(p, para, 9.5, color=ABBEY)

    _heading(doc, "What we are asking you to detect")
    intro = _para(doc, after=6)
    _run(intro, "These are behaviours and the data needed to see them, not finished searches. "
                "Build them the way your environment and conventions want them built. Where a "
                "number is given it was measured against 14 days of live data, and the measurement "
                "is the part worth keeping.", 9, italic=True, color=GREY)

    for i, det in enumerate(spec["detections"], start=1):
        p = _para(doc, before=9, after=3)
        _run(p, f"D{i}.  {det['name']}", 10.5, bold=True, color=ABBEY)

        blocks = [("The behaviour", det["behaviour"], ABBEY),
                  ("Logs and fields needed", det["logs_needed"], ABBEY),
                  ("What separates it from normal", det["discriminator"], ORANGE_DEEP),
                  ("Known false positives", det.get("false_positives", "None identified"), ABBEY),
                  ("What CTI observed", det["observed"], GREEN)]
        for lab, val, colour in blocks:
            mp = _para(doc, before=2, after=1, indent=0.02)
            _run(mp, f"{lab}   ", 8.5, bold=True, color=colour)
            if isinstance(val, list):
                for item in val:
                    ip = _para(doc, after=1, indent=0.20)
                    _run(ip, "\u25aa  ", 8.5, bold=True, color=ORANGE)
                    _run(ip, item, 8.5, color=ABBEY)
            else:
                vp = _para(doc, after=1, indent=0.16)
                _run(vp, val, 8.5, color=ABBEY)

    if spec.get("blocked"):
        _heading(doc, "Detections we cannot build yet, and what unblocks them")
        for b in spec["blocked"]:
            p = _para(doc, before=6, after=2)
            _run(p, b["name"], 10, bold=True, color=ABBEY)
            _run(p, f"   blocked by {b['gap']}", 8.5, bold=True, color=RED)
            for para in b["detail"]:
                bp = _para(doc, after=3); _run(bp, para, 9, color=ABBEY)
            if b.get("unblocks"):
                q = _para(doc, before=3, after=1, indent=0.02)
                _run(q, "What becomes detectable once the gap closes   ", 8.5, bold=True, color=ORANGE_DEEP)
                for item in b["unblocks"]:
                    ip = _para(doc, after=1, indent=0.20)
                    _run(ip, "\u25aa  ", 8.5, bold=True, color=ORANGE)
                    _run(ip, item, 8.5, color=ABBEY)

    if spec.get("validation_steps"):
        _heading(doc, "Validation steps before you deploy")
        for i, v in enumerate(spec["validation_steps"], start=1):
            p = _para(doc, after=3, indent=0.02)
            _run(p, f"{i}.  ", 9, bold=True, color=ORANGE)
            _run(p, v, 9, color=ABBEY)

    if spec.get("contact"):
        p = _para(doc, before=8)
        _run(p, "Questions:  ", 9, bold=True, color=ABBEY)
        _run(p, spec["contact"], 9, color=GREY)

    _footer(doc, skill_dir, rid, spec.get("tlp", "AMBER+STRICT"))
    doc.save(out_docx)

    unvalidated = [d["name"] for d in spec["detections"] if not d.get("observed")]
    return {"out": out_docx, "detections": len(spec["detections"]),
            "blocked": len(spec.get("blocked", [])),
            "validation_steps": len(spec.get("validation_steps", [])),
            "unvalidated": unvalidated}


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    figdir = sys.argv[4] if len(sys.argv) > 4 else None
    st = build(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2], sys.argv[3], figdir)
    print(json.dumps(st, indent=1))
    if st["unvalidated"]:
        sys.exit("REFUSING TO SHIP: detections with no observation: %s. Test the concept first — a "
                 "recommendation nobody has tested is a guess, with or without a query." % st["unvalidated"])
