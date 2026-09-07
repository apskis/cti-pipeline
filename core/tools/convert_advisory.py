#!/usr/bin/env python3
"""Extract an issued GeneLabs exposure advisory into a spec for the ONE PAGE format.

Written 2026-08-27 to migrate six advisories issued in the two-page format. The originating
specs were not retained, so the rendered .docx is the only source.

WHAT IT CARRIES OVER UNCHANGED, and why that matters: the Appendix A subsections. Those are
the measurements, the banners, the enrichment and the reasoning, and they were written when
the evidence was fresh. Re-authoring them would risk changing findings nobody asked to
change. The migration is a RESHAPE of the front of the document, not a rewrite of the back.

WHAT IT DROPS, per the 2026-08-27 format decision: the Risk table, Bottom Line, Technical
Detail, and the Severity row of the document control block.

WHAT IT CANNOT DO, and must not pretend to: write the A.7 reproduction walkthrough. The
original advisories record the TOOL, the DATA MODEL and the EXPECTED NUMBERS but rarely the
verbatim query. A walkthrough is therefore authored per document from that material, and
where the original did not record how a measurement was obtained THE STEP MUST SAY SO rather
than inventing a query that was never run. Same for the A.0 reasoning diagram: the nodes are
a reading of the argument and cannot be derived mechanically.

Usage:
  python convert_advisory.py <in.docx>        # prints extracted JSON to stdout
"""
import json, re, sys

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def _blocks(doc):
    for child in doc.element.body.iterchildren():
        if child.tag.endswith('}p'):
            yield Paragraph(child, doc)
        elif child.tag.endswith('}tbl'):
            yield Table(child, doc)


DROP_SECTIONS = {"technical detail", "bottom line", "release history", "the risk"}


def extract(path):
    doc = Document(path)
    out = {"source_file": path.split("/")[-1], "doc_control": [], "title": "", "subtitle": "",
           "summary": "", "why_bullets": [], "callout": "", "actions": [], "action_intro": "",
           "external_view": [], "risk_rows": [], "appendix_intro": "", "appendix": [],
           "correction": []}

    section = None          # current Heading 1, lowercased
    sub = None              # current Heading 2 dict
    seen_first_table = False

    for b in _blocks(doc):
        if isinstance(b, Table):
            hdr = [c.text.strip() for c in b.rows[0].cells]
            if not seen_first_table and hdr[:1] == ["Title"]:
                out["doc_control"] = [[r.cells[0].text.strip(), r.cells[1].text.strip()]
                                      for r in b.rows]
                seen_first_table = True
            elif hdr[:1] == ["Action"]:
                out["actions"] = [[c.text.strip() for c in r.cells] for r in b.rows[1:]]
            elif hdr == ["Field", "Value"] and section == "why we care":
                out["risk_rows"] = [[r.cells[0].text.strip(), r.cells[1].text.strip()]
                                    for r in b.rows[1:]]
            elif len(hdr) == 1 and "CORRECTION" in hdr[0].upper():
                out["correction"] = [p.text.strip() for p in b.rows[0].cells[0].paragraphs
                                     if p.text.strip()]
            elif sub is not None:
                sub.setdefault("tables", []).append(
                    [[c.text.strip() for c in r.cells] for r in b.rows])
            continue

        txt = b.text.strip()
        if not txt:
            continue
        st = b.style.name

        if st == "Heading 1":
            section = txt.lower()
            sub = None
            if section.startswith("appendix"):
                out["_in_appendix"] = True
            continue
        if st == "Heading 2":
            if out.get("_in_appendix"):
                sub = {"heading": txt, "paragraphs": []}
                out["appendix"].append(sub)
            else:
                sub = {"heading": txt, "paragraphs": []}
                if "external view" in txt.lower():
                    out["_ext"] = sub
            continue

        if section is None:
            if txt.lower().startswith("summary"):
                out["summary"] = re.sub(r"^summary:\s*", "", txt, flags=re.I)
            elif not out["title"]:
                out["title"] = txt
            elif not out["subtitle"]:
                out["subtitle"] = txt
        elif section == "why we care":
            if txt.lower().startswith(("detection gap", "risk assessment")):
                if txt.lower().startswith("detection gap"):
                    out["callout"] = re.sub(r"^detection gap:\s*", "", txt, flags=re.I)
            elif txt.startswith("▪"):
                out["why_bullets"].append(txt.lstrip("▪ ").strip())
        elif section == "what needs to be done":
            if not out["action_intro"]:
                out["action_intro"] = txt
        elif section == "technical detail" and sub is out.get("_ext"):
            out["external_view"].append(txt)
        elif out.get("_in_appendix"):
            if sub is None:
                out["appendix_intro"] = out["appendix_intro"] or txt
            else:
                sub["paragraphs"].append(txt.lstrip("▪ ").strip())

    out.pop("_in_appendix", None)
    out.pop("_ext", None)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(json.dumps(extract(sys.argv[1]), indent=1, ensure_ascii=False))
