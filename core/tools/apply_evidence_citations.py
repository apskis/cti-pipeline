#!/usr/bin/env python3
"""Evidence citation post-pass for GeneLabs CTI documents (hunt reports,
exposure advisories, run summaries).

Converts {{E1}} style markers anywhere in the document (body paragraphs and
table cells) into SUPERSCRIPT citation links (E1) that jump to a generated
appendix section carrying, for each citation: the claim, the exact Falcon CQL /
Splunk SPL / connector queries that support it, the result each returned, and
the chain of reasoning from result to claim.

Spec keys read:
  evidence_appendix        REQUIRED  list of entries:
      {"ref": "E1",
       "claim": "the sentence the citation supports",
       "queries": [{"engine": "Falcon CQL", "query": "...", "result": "one line result"}],
       "reasoning": "chain of thought from result to claim"}
  evidence_appendix_title  optional  heading (default: "Appendix — Evidence and Chain of Reasoning")

Usage:  python3 apply_evidence_citations.py out.docx spec.json
Run LAST, after every other post-pass. Idempotent: markers are consumed.
Exits non zero if a marker survives or cites an undefined ref, so a typo
cannot ship as literal braces.
"""
import json, re, sys, copy
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FONT = "Arial"; MONO = "Consolas"
ABBEY = "444648"; DEEP = "E05F00"; ORANGE = "FF7109"; GREY = "676765"
LINK = "1565C0"; CODE_BG = "F4F4F4"
MARKER = re.compile(r"\{\{(E\d+)\}\}")
_bm_id = [9000]


def _anchor(ref): return "EV_" + ref


def _sup_link(ref):
    h = OxmlElement("w:hyperlink"); h.set(qn("w:anchor"), _anchor(ref))
    r = OxmlElement("w:r"); rPr = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:cs"): fonts.set(qn(a), FONT)
    rPr.append(fonts)
    b = OxmlElement("w:b"); rPr.append(b)
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), "13"); rPr.append(sz)
    col = OxmlElement("w:color"); col.set(qn("w:val"), LINK); rPr.append(col)
    va = OxmlElement("w:vertAlign"); va.set(qn("w:val"), "superscript"); rPr.append(va)
    r.append(rPr)
    t = OxmlElement("w:t"); t.text = ref; t.set(qn("xml:space"), "preserve")
    r.append(t); h.append(r)
    return h


def _clone_run(src_run, text):
    r = copy.deepcopy(src_run)
    for t in r.findall(qn("w:t")): r.remove(t)
    for br in r.findall(qn("w:br")): r.remove(br)
    t = OxmlElement("w:t"); t.text = text; t.set(qn("xml:space"), "preserve")
    r.append(t)
    return r


def _process_paragraph(p):
    """Replace markers in one paragraph, preserving run formatting."""
    if not MARKER.search(p.text): return 0, []
    unknown = []
    n = 0
    for run in list(p.runs):
        if not MARKER.search(run.text): continue
        parts = MARKER.split(run.text)
        rEl = run._element; parent = rEl.getparent(); idx = list(parent).index(rEl)
        new = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                new.append(("link", part)); n += 1
            elif part:
                new.append(("text", part))
        for el in reversed(new):
            kind, val = el
            node = _sup_link(val) if kind == "link" else _clone_run(rEl, val)
            parent.insert(idx + 1, node)
        parent.remove(rEl)
    # marker split across runs: merge and retry once
    if MARKER.search(p.text):
        joined = "".join(r.text for r in p.runs)
        if MARKER.search(joined) and p.runs:
            first = p.runs[0]._element
            for r in list(p.runs)[1:]:
                r._element.getparent().remove(r._element)
            for t in first.findall(qn("w:t")): first.remove(t)
            t = OxmlElement("w:t"); t.text = joined; t.set(qn("xml:space"), "preserve")
            first.append(t)
            n2, _ = _process_paragraph(p)
            n += n2
    return n, unknown


def _iter_paragraphs(doc):
    for p in doc.paragraphs: yield p
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs: yield p


def _run(p, text, size=10, bold=False, color=ABBEY, italic=False, mono=False):
    r = p.add_run(text)
    r.font.name = MONO if mono else FONT
    r.font.size = Pt(size); r.font.bold = bold; r.font.italic = italic
    r.font.color.rgb = RGBColor.from_string(color)
    return r


def _shade(p, fill):
    pPr = p._p.get_or_add_pPr(); shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), fill); pPr.append(shd)


def _bookmark(p, name):
    _bm_id[0] += 1
    s = OxmlElement("w:bookmarkStart"); s.set(qn("w:id"), str(_bm_id[0])); s.set(qn("w:name"), name)
    e = OxmlElement("w:bookmarkEnd"); e.set(qn("w:id"), str(_bm_id[0]))
    p._p.insert(0, e); p._p.insert(0, s)


def _heading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(22); p.paragraph_format.space_after = Pt(8)
    r = _run(p, text.upper(), size=12, bold=True, color=DEEP)
    r.font.name = FONT
    pPr = p._p.get_or_add_pPr(); pBdr = OxmlElement("w:pBdr")
    btm = OxmlElement("w:bottom")
    btm.set(qn("w:val"), "single"); btm.set(qn("w:sz"), "12")
    btm.set(qn("w:space"), "2"); btm.set(qn("w:color"), ORANGE)
    pBdr.append(btm); pPr.append(pBdr)
    return p


def build_appendix(doc, spec):
    entries = spec.get("evidence_appendix") or []
    if not entries: return set()
    title = spec.get("evidence_appendix_title", "Appendix — Evidence and Chain of Reasoning")
    _heading(doc, title)
    intro = doc.add_paragraph()
    _run(intro, "Every superscript citation in this document resolves here. Each entry carries the claim as written, the exact queries executed (engine named), the result each returned, and the reasoning that connects result to claim. Queries are reproduced verbatim so any analyst can rerun them.",
         size=9, italic=True, color=GREY)
    intro.paragraph_format.space_after = Pt(8)
    refs = set()
    for e in entries:
        ref = e.get("ref", "")
        refs.add(ref)
        # entry heading with bookmark
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10); p.paragraph_format.space_after = Pt(3)
        _bookmark(p, _anchor(ref))
        _run(p, ref + "   ", size=10.5, bold=True, color=DEEP)
        _run(p, e.get("claim", ""), size=10, bold=True)
        for q in e.get("queries", []):
            lbl = doc.add_paragraph(); lbl.paragraph_format.space_after = Pt(1)
            _run(lbl, q.get("engine", "Query"), size=8.5, bold=True, color=GREY)
            code = doc.add_paragraph(); _shade(code, CODE_BG)
            code.paragraph_format.left_indent = Inches(0.15)
            code.paragraph_format.space_after = Pt(2)
            _run(code, q.get("query", ""), size=8, mono=True)
            if q.get("result"):
                res = doc.add_paragraph(); res.paragraph_format.left_indent = Inches(0.15)
                res.paragraph_format.space_after = Pt(4)
                _run(res, "Result:  ", size=8.5, bold=True, color=GREY)
                _run(res, q["result"], size=8.5, color=GREY, italic=True)
        if e.get("reasoning"):
            rp = doc.add_paragraph(); rp.paragraph_format.space_after = Pt(6)
            _run(rp, "Reasoning:  ", size=9, bold=True, color=DEEP)
            _run(rp, e["reasoning"], size=9.5)
    return refs


def main(docx_path, spec_path):
    doc = Document(docx_path)
    spec = json.load(open(spec_path, encoding="utf-8"))
    entries = spec.get("evidence_appendix") or []
    defined = {e.get("ref") for e in entries}
    used = set()
    for p in _iter_paragraphs(doc):
        for m in MARKER.finditer(p.text):
            used.add(m.group(1))
    missing = used - defined
    if missing:
        sys.exit("FATAL: markers cite undefined evidence refs: %s" % sorted(missing))
    refs = build_appendix(doc, spec)
    total = 0
    for p in _iter_paragraphs(doc):
        n, _ = _process_paragraph(p)
        total += n
    # verify consumption
    leftover = [p.text for p in _iter_paragraphs(doc) if MARKER.search(p.text)]
    if leftover:
        sys.exit("FATAL: unconsumed markers remain: %s" % leftover[:3])
    unused = refs - used
    doc.save(docx_path)
    print("citations linked: %d markers -> %d appendix entries%s" % (
        total, len(refs),
        ("; NOTE unused entries: " + ", ".join(sorted(unused))) if unused else ""))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    main(sys.argv[1], sys.argv[2])
