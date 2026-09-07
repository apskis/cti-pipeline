#!/usr/bin/env python3
"""Insert a hard page break before a named heading in a built .docx.

WHY THIS IS A POST-PASS AND NOT A BUILDER CHANGE

The exposure advisory builder is plugin-managed and must not be edited, the same reason
figures and evidence citations are applied afterwards. This does the same thing for the
one structural control the spec cannot express: "Appendix A starts on its own page."

April, 2026-09-01: "make the appendix start on its own page."

WHY IT MATTERS BEYOND TIDINESS

The one-page rule is about what a stakeholder receives, and a page one that trails two
appendix headings underneath the action table reads as a document that ran over. Forcing
the break makes the contract visible: page one is the whole main body, everything after
the break is reference the reader opens on demand.

A PAGE BREAK IS NOT A PARAGRAPH. It is a <w:br w:type="page"/> inside a run at the START
of the heading's own first run, not an empty paragraph before it. An empty spacer
paragraph would satisfy a visual check and then collapse differently depending on the
heading's space-before, which is how this kind of fix usually rots.

Idempotent: if the heading already carries a leading page break, nothing is added.

Usage:  python3 page_break_before.py out.docx "Appendix A"
"""
import re
import sys

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def _norm(s):
    # Headings render LETTERSPACED, so "Appendix A" can extract as "A p p e n d i x  A".
    return re.sub(r"\s+", "", s or "").lower()


def _has_leading_break(p):
    for r in p.runs:
        for child in r._r:
            if child.tag == qn("w:br") and child.get(qn("w:type")) == "page":
                return True
        if (r.text or "").strip():
            break          # a run with text came first; no leading break
    return False


def insert(path, heading_prefix):
    doc = Document(path)
    target_norm = _norm(heading_prefix)
    hits = []
    for p in doc.paragraphs:
        if not p.text.strip():
            continue
        if _norm(p.text).startswith(target_norm):
            hits.append(p)

    if not hits:
        print("page break: NO HEADING MATCHED %r - nothing changed" % heading_prefix)
        return 1

    # The first match is the section heading; later matches are cross-references in prose.
    p = hits[0]
    if _has_leading_break(p):
        print("page break: already present before %r" % p.text.strip()[:60])
        return 0

    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    if p.runs:
        first = p.runs[0]._r
        first.insert(0, br)
    else:
        r = OxmlElement("w:r")
        r.append(br)
        p._p.insert(0, r)

    doc.save(path)
    extra = (" (%d later mentions left alone - they are cross-references, not headings)"
             % (len(hits) - 1)) if len(hits) > 1 else ""
    print("page break: inserted before %r%s" % (p.text.strip()[:60], extra))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    sys.exit(insert(sys.argv[1], sys.argv[2]))
