#!/usr/bin/env python3
"""Replace figure sentinels in a built .docx with images.

The plugin-managed exposure advisory builder has no image support and must not be edited,
so figures are placed the same way the CVE priority brief places its matrix: write a
sentinel paragraph in the spec, then swap it after the build.

Sentinel form:  __FIG:name:width_inches__   e.g.  __FIG:reasoning:6.4__

Anything after the second colon is optional and defaults to 6.4in. The image is looked up
as <figdir>/<name>.png. A sentinel with no matching file is left in place and reported,
rather than silently deleted — a missing figure should be visible, not invisible.

Run AFTER apply_inline_bold.py and BEFORE apply_evidence_citations.py. The citation pass
walks paragraphs and would otherwise have to skip a run containing an image.

Usage:
  python insert_figures.py out.docx figdir
"""
import os, re, sys

from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

SENTINEL = re.compile(r"__FIG:([A-Za-z0-9_\-]+)(?::([0-9.]+))?__")


def insert(docx_path, figdir):
    doc = Document(docx_path)
    placed, missing = [], []

    for p in list(doc.paragraphs):
        m = SENTINEL.search(p.text)
        if not m:
            continue
        name, width = m.group(1), float(m.group(2) or 6.4)
        path = os.path.join(figdir, f"{name}.png")
        if not os.path.exists(path):
            missing.append(name)
            continue
        for r in list(p.runs):
            r._element.getparent().remove(r._element)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = 0
        p.add_run().add_picture(path, width=Inches(width))
        placed.append(name)

    doc.save(docx_path)
    return placed, missing


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    placed, missing = insert(sys.argv[1], sys.argv[2])
    print(f"figures placed: {placed}")
    if missing:
        sys.exit(f"MISSING figure files, sentinels left visible in the document: {missing}")
