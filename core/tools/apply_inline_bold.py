#!/usr/bin/env python3
"""Convert **marked** spans into real bold runs in a built .docx.

WHY THIS EXISTS
---------------
genelabs_style.bullet() emits exactly two runs: the orange bullet glyph, then the
whole bullet text as ONE run. There is no way to bold part of a bullet from the
spec. Before 2026-08-26 the workaround was to write the lead-in of each Why We
Care bullet in CAPITALS, which April asked to replace with ordinary sentence case
plus bold.

This is a POST-PROCESSOR, run after the plugin-managed builder. The skill
directory is a read-only cache and the bulletin and advisory builders are
plugin-managed, so neither is modified — this reopens the finished document and
rewrites only the runs that carry the ** marker. A paragraph with no marker is
left byte-identical.

    python apply_inline_bold.py out.docx

Idempotent: running it twice is a no-op, because the markers are consumed.
"""
import re
import sys

from docx import Document

MARK = re.compile(r"\*\*(.+?)\*\*", re.S)


def _split_run(run, para):
    """Replace one run containing **spans** with a sequence of runs."""
    text = run.text
    if "**" not in text:
        return 0
    parts, last, out = [], 0, 0
    for m in MARK.finditer(text):
        if m.start() > last:
            parts.append((text[last:m.start()], False))
        parts.append((m.group(1), True))
        last = m.end()
    if last < len(text):
        parts.append((text[last:], False))
    if not parts:
        return 0

    # Reuse the original run for the first part so its font survives untouched,
    # then clone its formatting onto the rest. Cloning by copying the rPr XML is
    # the only reliable way; setting attributes individually silently drops
    # anything not explicitly named, such as the theme colour.
    rpr = run._element.find(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr")
    run.text = parts[0][0]
    run.font.bold = parts[0][1] or None
    anchor = run._element
    for txt, is_bold in parts[1:]:
        new = para.add_run(txt)
        if rpr is not None:
            import copy
            new._element.insert(0, copy.deepcopy(rpr))
        new.font.bold = is_bold or None
        anchor.addnext(new._element)
        anchor = new._element
        out += 1
    return out + 1


def apply(path):
    doc = Document(path)
    changed = 0

    def walk(paras):
        nonlocal changed
        for p in paras:
            for r in list(p.runs):
                changed += _split_run(r, p)

    walk(doc.paragraphs)
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                walk(c.paragraphs)
    for sec in doc.sections:
        for container in (sec.header, sec.footer):
            walk(container.paragraphs)
            for t in container.tables:
                for row in t.rows:
                    for c in row.cells:
                        walk(c.paragraphs)

    if changed:
        doc.save(path)
    return changed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: apply_inline_bold.py <docx>", file=sys.stderr)
        raise SystemExit(2)
    n = apply(sys.argv[1])
    print("inline bold: %d runs rewritten" % n)
    # Assert no marker survived, so a typo cannot ship as literal asterisks.
    d = Document(sys.argv[1])
    txt = "\n".join(p.text for p in d.paragraphs)
    txt += "\n".join(c.text for t in d.tables for r in t.rows for c in r.cells)
    if "**" in txt:
        print("ERROR: unconsumed ** marker remains in the document",
              file=sys.stderr)
        raise SystemExit(1)
