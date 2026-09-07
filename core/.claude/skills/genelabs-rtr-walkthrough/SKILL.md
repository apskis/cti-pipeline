---
name: "genelabs-rtr-walkthrough"
description: "Build an GeneLabs-branded RTR / Manual Action Walkthrough .docx — the analyst hand-off sheet for the steps only a human can run in the CrowdStrike Falcon console (Real Time Response and other manual checks) to confirm a hunt finding the automated loop could not close with telemetry alone. Tied to a parent hunt, it lays out target hosts, prerequisites, numbered RTR command steps with expected benign-vs-malicious results and a result line, decision/escalation guidance, and a findings-capture block. Use when a hunt thread needs manual RTR confirmation, an on-host netstat/tasklist/service check, or any hands-on Falcon-console action handed to the analyst."
---

# GeneLabs RTR / Manual Action Walkthrough Builder

Produces the **analyst hand-off sheet** .docx: the steps only a human can run in the
CrowdStrike Falcon console — Real Time Response (RTR) and other manual checks — to
**confirm a hunt finding the automated loop could not close** with Falcon or Splunk
telemetry alone. Each sheet is tied to a parent hunt and carries the GeneLabs house
branding (banner, palette, wordmark / TLP / DOC # / page footer), reused from the installed
`genelabs-threat-hunt-report` skill, so it reads as one set with the reports and run
summaries. File name convention: `<YYYY-MM-DD>-<FriendlyName>-<UID>-RTR.docx` in the year
archive's `RTR Walkthroughs` subfolder.

## When to use
- A completed hunt reached a thread that needs on-host confirmation: an exact service name
  behind a listener, a live `netstat`/`tasklist`, a file hash/signer check, a registry read,
  or a captured artifact — things the automated hunt cannot do from telemetry.
- Any finding whose verdict is gated on a manual Falcon-console action (RTR read-only
  commands, or a write action like `get` under stated authorization).
- The user asks for an "RTR walkthrough", "manual action sheet", or a hand-off to confirm a
  finding by hand.

Do **not** use this for a thread that is still huntable in Falcon/Splunk — hunt it (or pivot)
instead. This sheet is specifically for what only the analyst can do.

## How to build
1. Assemble a `spec.json` from the schema below. Draw the target hosts/users, the finding,
   and the decision logic straight from the parent hunt report so the sheet is self-contained.
2. Write the embedded builder to `scripts/build_rtr_walkthrough.py`.
3. Run:
   ```
   python3 scripts/build_rtr_walkthrough.py spec.json out.docx
   ```
4. Name the output `<YYYY-MM-DD>-<FriendlyName>-<UID>-RTR.docx` and write it into the year
   archive's manual-action subfolder, e.g.
   `...\CTI Threat Hunts\2026\RTR Walkthroughs\`. The `-RTR` suffix (not `-Complete`) keeps
   it out of the hunt task's package scan.
5. Deliver with `present_files`.

If `python-docx` is missing: `pip install python-docx --break-system-packages`.

## Content principles
- **Read-only by default.** List RTR read-only commands (`netstat`, `tasklist`, `ps`,
  `reg query`, `wmic ... get`, `filehash`, `ls`, `cat`) as the walkthrough spine. Call out any
  write action (`get`, `put`, `kill`, `runscript`) explicitly and gate it on stated
  authorization — never present a destructive/irreversible action as routine.
- **Every step earns its place.** Each step states what it *confirms* and what benign vs
  malicious looks like, so the analyst can rule without guessing.
- **Capture the result.** Each step and the closing block leave blank lines for the analyst
  to record what they saw, so the sheet doubles as the evidence record fed back into the hunt.
- Keep April's voice: concise, tight, no hyphenated compound modifiers.

## JSON spec schema
```json
{
  "action_id": "TH26-04A-RTR",
  "date": "2026-08-20",
  "parent_hunt": "TH26-04A",
  "parent_report": "2026-08-19-Port10001Service-TH2604A-Complete.docx",
  "priority": "Medium",
  "action_type": "Real Time Response (RTR) — read-only",
  "why_manual": "One line: exactly what the automated hunt could not do and why this needs a human.",
  "finding": "The finding being confirmed, lifted from the parent report, including the current gated verdict.",
  "targets": [
    {"host": "<host or selection rule>", "user": "assigned user", "note": "how to pick / which host"}
  ],
  "prereq": [
    "Falcon console > Endpoint security > Host management > find the host > Connect to Host (RTR).",
    "Requires the RTR Active Responder (or Administrator) role. Commands below are READ-ONLY.",
    "Confirm the host shows RTR state 'enabled' and is online."
  ],
  "steps": [
    {"n": 1, "goal": "What this step establishes",
     "command": "netstat -ano | findstr :10001",
     "confirms": "Which PID owns the listener.",
     "expect_benign": "What a benign result looks like.",
     "expect_malicious": "What a malicious result looks like."}
  ],
  "decision": [
    "If steps resolve to a known signed service in a system path: classify Benign, record the name, close the hunt.",
    "If the binary is unsigned / in a user-writable path / unrecognised: capture it (get <path>, authorized for triage), preserve output, escalate to IR referencing the parent hunt."
  ],
  "record": ["Host confirmed:", "Owning service / PID:", "Binary path & signer:", "Verdict:", "Follow-up action:", "Analyst & date:"],
  "tlp": "AMBER+STRICT",
  "closing_note": "Optional; a sensible default is used if omitted."
}
```
`prereq`, `decision`, and `record` accept a list (bulleted / line-per-entry) or a single
string. `record` defaults to a standard capture block if omitted. `subtitle`, `doc_title`,
`action_type`, `status`, `tlp`, and `closing_note` are optional overrides.

## Layout produced
1. Right-aligned `action_id | date` header and the "RTR / Manual Action Walkthrough" title.
2. Metadata table (parent hunt, parent report, action type, priority in its severity colour,
   prepared date, status).
3. "Why this needs you" callout in the warm GeneLabs tint.
4. **Finding to Confirm**, **Target Hosts / Users** (table), **Before You Start** (prereqs).
5. **Walkthrough** — one card per step: orange accent bar, the command in a monospace code
   block, Confirms / Benign looks like / Malicious looks like, and a blank Result line.
6. **Decision & Escalation**, then a **Record Your Findings** capture block.
7. Italic closing note, then the shared GeneLabs footer (wordmark, TLP, DOC #, page numbers).

## Builder source
Write this verbatim to `scripts/build_rtr_walkthrough.py`, then run it. It imports the
branding helpers and clones the banner template from the installed
`genelabs-threat-hunt-report` skill, which it locates automatically.

```python
#!/usr/bin/env python3
"""
Build an GeneLabs-branded RTR / MANUAL ACTION WALKTHROUGH .docx from a JSON spec.

This is the analyst hand-off sheet: the steps only a human can run in the
CrowdStrike Falcon console (Real Time Response and other manual checks) to
CONFIRM a finding the automated hunt could not close. It is tied to a parent
hunt and reuses the GeneLabs house branding from the installed
genelabs-threat-hunt-report skill so it reads as one set with the reports.

Usage:
    python build_rtr_walkthrough.py spec.json out.docx
"""
import glob
import json
import os
import sys
import importlib.util

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def _locate_report_skill():
    marker = os.path.join("genelabs-threat-hunt-report", "scripts", "build_hunt_report.py")
    patterns = [
        os.path.join("/sessions", "*", "mnt", ".claude", "skills", marker),
        os.path.join(os.path.expanduser("~"), ".claude", "skills", marker),
        os.path.join("/sessions", "*", "mnt", "*", "skills", marker),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", marker),
    ]
    for pat in patterns:
        hits = glob.glob(pat)
        if hits:
            return os.path.dirname(os.path.dirname(os.path.abspath(hits[0])))
    for root in ("/sessions", os.path.expanduser("~"), os.getcwd()):
        hits = glob.glob(os.path.join(root, "**", marker), recursive=True)
        if hits:
            return os.path.dirname(os.path.dirname(os.path.abspath(hits[0])))
    raise SystemExit("Could not locate the genelabs-threat-hunt-report skill for branding assets.")


SKILL = _locate_report_skill()
_spec = importlib.util.spec_from_file_location(
    "ithr", os.path.join(SKILL, "scripts", "build_hunt_report.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)

TEMPLATE = os.path.join(SKILL, "assets", "hunt_template.docx")
WORDMARK = os.path.join(SKILL, "assets", "genelabs_wordmark_grey.png")


def build(spec, out_path):
    doc = Document(TEMPLATE)
    R.set_base_style(doc)
    date = spec.get("date", "")
    action_id = spec.get("action_id", (spec.get("parent_hunt", "TH") + "-RTR"))

    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run(f"{action_id}  |  {date}")
    r.font.name = R.FONT; r.font.size = Pt(9); r.font.bold = True

    R.h_title(doc, spec.get("doc_title", "RTR / Manual Action Walkthrough"))
    R._p(doc, spec.get("subtitle",
         "Analyst hand-off — steps to run in the CrowdStrike Falcon console to confirm a hunt finding."),
         size=10, italic=True, color=R.GREY, after=4)

    # Metadata
    pr = str(spec.get("priority", "Medium")).split()[0].upper()
    t = doc.add_table(rows=0, cols=4); t.style = "Table Grid"; R._table_borders(t)
    rows = [
        ["Parent Hunt", spec.get("parent_hunt", ""), "Priority", spec.get("priority", "Medium")],
        ["Parent Report", spec.get("parent_report", ""), "Prepared", date],
        ["Action Type", spec.get("action_type", "Real Time Response (RTR)"),
         "Status", spec.get("status", "Awaiting analyst")],
    ]
    for a, b, c, d in rows:
        cells = t.add_row().cells
        specs = [(cells[0], a, True, None), (cells[1], b, False, None),
                 (cells[2], c, True, None),
                 (cells[3], d, False, R.PRIO.get(pr) if c == "Priority" else None)]
        for cell, val, bold, colr in specs:
            R._cell_shade(cell, R.META_LABEL if (bold and val) else R.WHITE)
            cell.paragraphs[0].text = ""
            rr = cell.paragraphs[0].add_run(val); rr.font.name = R.FONT; rr.font.size = Pt(9)
            rr.font.bold = bold or bool(colr)
            if colr:
                rr.font.color.rgb = RGBColor.from_string(colr)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # Why this is manual
    if spec.get("why_manual"):
        p = doc.add_paragraph(); R._shade(p, R.BOX_FILL)
        p.paragraph_format.space_after = Pt(3); p.paragraph_format.space_before = Pt(2)
        r1 = p.add_run("Why this needs you:  "); r1.font.name = R.FONT; r1.font.size = Pt(10); r1.font.bold = True
        r2 = p.add_run(spec["why_manual"]); r2.font.name = R.FONT; r2.font.size = Pt(10)

    # Finding to confirm
    if spec.get("finding"):
        R.h_section(doc, "Finding to Confirm")
        R._p(doc, spec["finding"], size=10)

    # Targets
    if spec.get("targets"):
        R.h_section(doc, "Target Hosts / Users")
        R.grid_table(doc, ["Host", "User", "Note"],
                     [[x.get("host", ""), x.get("user", ""), x.get("note", "")]
                      for x in spec["targets"]], widths=[2.2, 1.6, 3.1])

    # Prerequisites
    if spec.get("prereq"):
        R.h_section(doc, "Before You Start")
        if isinstance(spec["prereq"], list):
            R.bullets(doc, spec["prereq"])
        else:
            R._p(doc, spec["prereq"], size=10)

    # Steps
    R.h_section(doc, "Walkthrough")
    for i, s in enumerate(spec.get("steps", []), 1):
        n = s.get("n", i)
        R._accent_bar(doc, f"Step {n} — {s.get('goal','')}", R.ORANGE_RULE, size=10.5)
        if s.get("command"):
            R._p(doc, "Run:", size=9, bold=True, color=R.GREY, after=1)
            R.code_block(doc, s["command"])
        if s.get("confirms"):
            R.h_label_value(doc, "Confirms", s["confirms"], indent=0.05)
        if s.get("expect_benign"):
            R.h_label_value(doc, "Benign looks like", s["expect_benign"], indent=0.05)
        if s.get("expect_malicious"):
            R.h_label_value(doc, "Malicious looks like", s["expect_malicious"], indent=0.05)
        # result capture line
        p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.left_indent = Inches(0.05)
        rr = p.add_run("Result:  "); rr.font.name = R.FONT; rr.font.size = Pt(9); rr.font.bold = True
        rr.font.color.rgb = RGBColor.from_string(R.GREY)
        u = p.add_run("________________________________________________________________")
        u.font.name = R.FONT; u.font.size = Pt(9); u.font.color.rgb = RGBColor.from_string("BBBBBB")

    # Decision guidance
    if spec.get("decision"):
        R.h_section(doc, "Decision & Escalation")
        if isinstance(spec["decision"], list):
            R.bullets(doc, spec["decision"])
        else:
            R._p(doc, spec["decision"], size=10)

    # Record block
    R.h_section(doc, "Record Your Findings")
    record_lines = spec.get("record") or [
        "Host confirmed:", "Owning process / service / PID:", "Binary path & signer:",
        "Verdict (Confirmed Compromise / Suspicious / Benign / Inconclusive):",
        "Follow-up action taken:", "Analyst & date:",
    ]
    if isinstance(record_lines, str):
        record_lines = [record_lines]
    for ln in record_lines:
        p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(3)
        rr = p.add_run(ln + "  "); rr.font.name = R.FONT; rr.font.size = Pt(10); rr.font.bold = True
        u = p.add_run("__________________________________________")
        u.font.name = R.FONT; u.font.size = Pt(10); u.font.color.rgb = RGBColor.from_string("BBBBBB")

    R._p(doc, "", before=8)
    R._p(doc, spec.get("closing_note",
         "Manual action sheet generated by the automated CTI Threat Hunting Automation loop for a thread it could "
         "not close with Falcon or Splunk telemetry alone. Complete the steps in the CrowdStrike "
         "Falcon console, record the result above, and update the parent hunt report. RTR commands "
         "listed here are read-only unless explicitly noted; run write actions (get, put, kill) only "
         "with the stated authorization."),
         size=8, italic=True, color=R.GREY)

    R.build_footer(doc, action_id, spec.get("tlp", R.DEFAULT_TLP), R._copyright(date),
                   wordmark_path=WORDMARK)
    cp = doc.core_properties
    cp.title = f"RTR Walkthrough {action_id}"
    cp.category = "RTR / Manual Action Walkthrough"
    cp.comments = "GeneLabs Enterprise Information Security | Cyber Threat Intelligence"
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    print("wrote", build(spec, sys.argv[2]))
```

