#!/usr/bin/env python3
"""Remove ORPHANED external relationships from a built .docx.

The house template `cti_doc_template.docx` was saved from a bulletin that carried
source links, so every document cloned from it inherits eleven external
relationships pointing at BleepingComputer, The Hacker News, Health-ISAC, the SEC,
HHS, NY DFS and a ServiceNow catalogue item. Nothing references them, so nothing
renders - but they are embedded in the file, and external news links sitting inside
a TLP:AMBER+STRICT document look wrong to anyone who inspects it or runs DLP over it.

This removes only relationships that are BOTH external AND unreferenced by any
w:hyperlink in the body, headers or footers. Image and style relationships are
internal and are never touched, and a link the document actually uses is kept.

    python3 strip_orphan_links.py <docx> [<docx> ...]
"""
import sys
from docx import Document
from docx.oxml.ns import qn


def used_rids(doc):
    rids = set()
    containers = [doc.element.body]
    for sec in doc.sections:
        containers += [sec.header._element, sec.footer._element]
    for c in containers:
        for el in c.iter(qn("w:hyperlink")):
            rid = el.get(qn("r:id"))
            if rid:
                rids.add(rid)
    return rids


def strip(path):
    doc = Document(path)
    keep = used_rids(doc)
    orphans = [rid for rid, rel in doc.part.rels.items()
               if rel.is_external and rid not in keep]
    for rid in orphans:
        del doc.part.rels[rid]
    if orphans:
        doc.save(path)
    return orphans


if __name__ == "__main__":
    for p in sys.argv[1:]:
        gone = strip(p)
        print(f"{p.rsplit('/', 1)[-1][:56]:<58} removed {len(gone)}")
