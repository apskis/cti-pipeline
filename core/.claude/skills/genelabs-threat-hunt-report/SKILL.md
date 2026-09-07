---
name: "genelabs-threat-hunt-report"
description: "Build an GeneLabs-branded Threat Hunt REPORT .docx — the completed, post-execution record of a hunt run against CrowdStrike Falcon and/or Splunk. Titles the document \"Threat Hunt Report\" followed by the hunt's own title, leads with the hypothesis verdict and a linked findings index, renders the findings landscape and a Coverage and Gaps roll-up, carries superscript evidence citations linked to a chain of reasoning appendix, and carries the GeneLabs corporate palette with the CTI bulletin footer. Use when a threat hunt is DONE and you are filing the results, converting a hunt package into its completed report, or recording hypothesis verdicts, findings, affected hosts and recommendations. For a hunt not yet executed use genelabs-threat-hunt-package."
---

# GeneLabs Threat Hunt Report

> **This is the completed-hunt document.** It is the same CTI2602 structure as
> **genelabs-threat-hunt-package**, with three differences: the title is "Threat Hunt Report",
> the footer marking reads "CTI Threat Hunt Report", and the document is expected to carry
> `overall_finding` + `findings`. Building without them emits a warning, because an empty
> report is a package that has not been run yet.

## Report title — name the hunt (April's 2026-08-25 instruction)
The document title must carry the hunt's own title after the words "Threat Hunt Report", so a
reader can tell which hunt a report is from its heading alone. ALWAYS set `doc_title` to the
form "Threat Hunt Report — HUNT TITLE" (use an em dash, never a hyphen). Take the hunt title
from the hunt subject (e.g. the friendly part of `meta.hunt_title`, or the hypothesis
subject). For example a WebLogic bypass hunt gets `doc_title` "Threat Hunt Report — Oracle
WebLogic Proxy Plug-in Access Control Bypass", and a miniOrange hunt gets "Threat Hunt Report
— miniOrange SAML SSO the public web Takeover". If `doc_title` is omitted the builder falls back to
the bare "Threat Hunt Report", which is now considered incomplete — set it on every report.

## When to use
- A hunt has been executed against Falcon (and/or Splunk) and you are filing the result.
- You are converting an existing Threat Hunt Package into its completed report.
- You are recording hypothesis verdicts, findings, affected hosts, recommendations, or
  telemetry/licensing/configuration gaps found while hunting.

Do NOT use this for a hunt that has not been run — use `genelabs-threat-hunt-package`.

## Build — four steps, always in this order
```
python scripts/build_hunt_report.py spec.json out.docx assets/hunt_template.docx
python <PACKAGES>/_tools/append_proposed_hunts_table.py out.docx spec.json   (once, if proposed_hunts present)
python scripts/restyle_report.py out.docx spec.json                          (house layout v2, embedded below)
python <PACKAGES>/_tools/apply_evidence_citations.py out.docx spec.json      (ALWAYS LAST — v3 evidence citations, embedded below)
```
`scripts/restyle_report.py` may not exist yet in the cached skill folder — write it from the
embedded source at the bottom of this file before running it. The evidence citation pass
lives in the workspace `_tools` folders (threat hunt PACKAGES `_tools` first, CTI
Deliverables root `_tools` second — identical copies); if neither is reachable, write it from
the embedded source at the bottom of this file. It must run LAST so no later pass splits the
superscript hyperlink runs.

Name the output to April's archive convention and write it to
`...\CTI Deliverables\CTI Threat Hunts\<YEAR>\`:
`<YYYY-MM-DD>-<FriendlyName>-<UID>-Complete.docx`
(e.g. `2026-08-19-WinIKE-RCE-TH2601-Complete.docx`). The trailing `-Complete` is required —
the hunt task skips any filename containing "Complete", so it is the duplicate-prevention
marker. A Splunk rescan of an existing hunt keeps the same UID and carries `Rescan` in the
FriendlyName (e.g. `2026-08-21-WinIKERescan-TH2601-Complete.docx`).

## House layout v2 (April's August 2026 readability update — REQUIRED on every report)
Three conventions, applied by `scripts/restyle_report.py`:

1. **Real execution times + delta row.** `meta.start_date` and `meta.end_date` carry the ACTUAL
   hunt execution start and finish times, not bare dates — format `"2026-08-21  20:45 UTC"`.
   Add `meta.duration` (e.g. `"7 minutes (query wall time, sequential)"`) and `meta.engines`
   (e.g. `"Splunk Cloud (executed) + Falcon (attribution only)"`); the restyler appends a
   `Hunt Duration (Delta) | <duration> | Engines | <engines>` row to the metadata table.

2. **Structured Investigation Summary — never a wall of text.** Instead of one dense
   `overall_finding.explanation` paragraph, supply `overall_finding.blocks`: an array of
   `{"label": "...", "body": "..."}` and set `"explanation": "__BLOCKS__"`. The restyler
   replaces the marker with one paragraph per block — label rendered bold caps in deepened
   orange (E05F00) at 9.5pt, body in Abbey 10pt, 7pt after-spacing. House labels to use:
   `Verdict` (or `Verdict - <component>` when hypotheses split), `Coverage caveat`,
   `What would change the verdict`, plus optional `New Suspicious thread`, `Side finding`,
   `What the rescan changed`, `Remaining caveats`. Keep each body 1-3 sentences.
   Similarly, split the window/method preamble into `investigation_note_lines` (2-4 short
   lines); set `investigation_note` to the FIRST line (the builder renders it) and the
   restyler inserts the rest as matching italic grey 9pt lines after it.

3. **Air between sections.** The restyler sets every orange underlined section heading to
   22pt space-before / 8pt space-after. No spec key needed.

The builder script itself is unchanged; v2 is applied entirely by the restyler so older specs
still build. But every NEW report must ship with all three conventions AND the named title
(`doc_title` = "Threat Hunt Report — HUNT TITLE").

## Evidence citations and the chain of reasoning appendix (v3, April's 2026-08-26 instruction — REQUIRED on every report)

**Every claim about the estate must carry a source citation to the actual query that
supports it, rendered as a superscript link into an appendix that shows the chain of
reasoning.** "We have no Gitea", "all listeners attribute benign", "zero untrust ingress" —
any such sentence, wherever it appears (Investigation Summary blocks, findings evidence,
gaps, IOC notes, the closing note), gets a marker and an appendix entry. A claim with no
citation is treated as unsupported and must be either cited or cut.

How it works:

1. **Write `{{E1}}`, `{{E2}}`, ... immediately after each claim** in the spec text, at the
   sentence that makes the claim. Reuse one ref wherever the same evidence supports the same
   claim in more than one place (summary block and finding, say).
2. **Supply the `evidence_appendix` spec key** — one entry per ref:
   ```json
   "evidence_appendix": [
     {"ref": "E1",
      "claim": "Zero Gitea listeners exist on the sensored estate",
      "queries": [
        {"engine": "Falcon CQL (NG-SIEM)",
         "query": "#event_simpleName=NetworkReceiveAcceptIP4 | in(LocalPort, values=[\"3000\",\"3001\"]) | groupBy([ContextBaseFileName, LocalPort], ...)",
         "result": "22 rows over 63.0M accept events; node, grafana, postgrest and peers; zero gitea"},
        {"engine": "Splunk SPL (control)",
         "query": "| tstats summariesonly=true count from datamodel=...",
         "result": "control populated, so the zero is real"}
      ],
      "reasoning": "Accept events name the owning process on every listener, so if any sensored host ran Gitea it would appear in this attribution. It does not, and the paired control proves the event stream was populated, so the zero is a real negative rather than a broken query."}
   ]
   ```
   `queries` carries the VERBATIM CQL / SPL / connector call actually run — an analyst must
   be able to rerun it unchanged. `result` is the one line outcome. `reasoning` is the chain
   of thought: how the result, plus any control, produces the claim, including what the
   result CANNOT prove.
3. **Run `apply_evidence_citations.py out.docx spec.json` LAST.** It appends an
   "Appendix — Evidence and Chain of Reasoning" section (override the heading with spec key
   `evidence_appendix_title`), bookmarks each entry, and converts every `{{En}}` marker into
   a small bold superscript `En` hyperlinked to its entry. It exits non zero if any marker
   survives or cites an undefined ref, so a typo cannot ship as literal braces. It is
   idempotent — markers are consumed.
4. **Controls belong in the entry.** Where a claim rests on a zero, the entry must carry the
   control query alongside, because the zero is only evidence with the control next to it.
5. Reports that predate v3 are not retrofitted; every NEW report ships with citations.

## Branding
Body palette and footer furniture are shared with **genelabs-cti-bulletin**: GeneLabs orange
`FF7109` rule, deepened orange `E05F00` for small text, Abbey `444648` body, corporate grey
`676765`, and the grey wordmark in `assets/genelabs_wordmark_grey.png`. The footer carries the
wordmark, `TLP: <level>  |  CTI Threat Hunt Report`, the copyright line, `DOC # <hunt_id>` and
live `Page X of Y` fields. Override per document with `tlp`, `copyright_line`, `doc_title`,
`subtitle` and `closing_note`.

## Report-specific spec keys
| Key | Purpose |
|---|---|
| `overall_finding` | `{verdict, explanation, blocks}` — the HYPOTHESIS VERDICT headline. Prefer `blocks` (v2) with `explanation: "__BLOCKS__"`; a plain `explanation` string still works as fallback. Verdict values: SUPPORTED / PARTIALLY SUPPORTED / NOT SUPPORTED / INCONCLUSIVE. |
| `findings` | The findings landscape. Each: `{num, title, type, confidence, classification, evidence, impact_rationale, recommendation[], detection_opportunity}` |
| `gaps` | Extra telemetry / licensing / configuration gaps beyond those auto-derived from findings |
| `investigation_note` | First line of the window/method preamble (exact hunt window in UTC) |
| `investigation_note_lines` | v2: remaining short preamble lines inserted by the restyler |
| `meta.start_date` / `meta.end_date` | ACTUAL execution start/finish, `"YYYY-MM-DD  HH:MM UTC"` |
| `meta.duration` / `meta.engines` | v2: rendered as the Hunt Duration (Delta) / Engines row |
| `doc_title` | REQUIRED: "Threat Hunt Report" plus the hunt's own title after an em dash, so the report names its hunt. Falls back to the bare "Threat Hunt Report" only if omitted (now considered incomplete). |
| `evidence_appendix` | v3 REQUIRED: the citation entries (`ref`, `claim`, `queries[{engine, query, result}]`, `reasoning`) resolved by `{{En}}` markers in the text |
| `evidence_appendix_title` | Optional heading override for the citation appendix |
| `subtitle` / `closing_note` / `tlp` / `copyright_line` | Footer and framing overrides |

Never write "disproven". A hunt can fail to find something; it cannot prove absence.
NOT SUPPORTED means "no evidence in the window with the telemetry available".


# GeneLabs Threat Hunt Report Builder

Generates a downloadable, branded threat hunt document that matches April's
CTI2602 hunt structure and generates Splunk `tstats` queries against GeneLabs's
real accelerated data models. Branding comes from `assets/hunt_template.docx`
(same GeneLabs banner as the bulletin skill) — clone it, never rebuild the banner.
The GeneLabs corporate identity for the body and footer is applied by
`scripts/build_hunt_report.py`; never restyle by hand (the sanctioned
post-passes are `scripts/restyle_report.py` and `apply_evidence_citations.py`).

## When to use
Whenever the deliverable is a threat hunt plan/package for GeneLabs, or when
converting scan findings or a bulletin into testable, runnable hunts. Pairs with
the CTI daily scan.

## Investigate-first workflow (falcon-mcp + splunk-mcp-server)
The intended loop is investigate BEFORE writing a package:
1. For each huntable item, draft the ABLE hypothesis + CQL, then EXECUTE the CQL
   against live Falcon telemetry using the **falcon-mcp** tools (fleet, ~14 days) —
   confirm the ABLE Location and Evidence actually exist. Also check Falcon
   detections and custom IOCs for the item's hashes/domains/IPs. Where
   splunk-mcp-server is connected, EXECUTE the supporting tstats searches too and
   record a one-line result summary in each query's purpose.
2. Only build a hunt package for items that returned TRUE POSITIVES (or genuinely
   suspicious/inconclusive results worth documenting). If nothing is confirmed,
   say so and skip the package.
3. For confirmed items, build the package AND fill the `overall_finding` and
   `findings` (below) from the results — this renders the Investigation
   Result + Findings landscape with the classification/rating.
If neither engine is available in the session, skip execution and build a CQL-only
package with unexecuted CQL, set `handoff_note` telling April to open it in the
Claude desktop app (with falcon-mcp connected) and reply "investigate", and set
`investigation_note` that live validation was not run. Do NOT invent findings.

Useful falcon-mcp capabilities (names vary by server build): LogScale/NG-SIEM
search (run the CQL), detection search, host/device lookup, custom IOC search,
Spotlight vulnerabilities, and RTR for live-host triage. Search for them with
ToolSearch (`mcp__falcon__*` / "falcon") before relying on them.

## Query generation — CrowdStrike CQL is PRIMARY
CrowdStrike Falcon is the endpoint source of truth, so lead every hypothesis with
**CrowdStrike Falcon CQL (LogScale) queries** — see `references/crowdstrike_cql.md`
for syntax and the event/field reference. Write real CQL (groupBy / in() / regex /
table / sort), NOT legacy Splunk-style Event Search. Splunk `tstats` queries are
included as SUPPORTING corroboration, not the lead. EXCEPTION: on a Splunk rescan
of a previously Falcon-only hunt, the `queries` array carries the EXECUTED SPL
with result summaries and the `falcon` array may be omitted or attribution-only.

Put the CQL set in the `falcon` array (rich objects, below).

DEFAULT = CQL ONLY. For the daily scheduled hunt package, produce CrowdStrike CQL
only and OMIT the Splunk `queries` array — unless Splunk was actually executed,
in which case include the executed searches with result summaries in `purpose`.
Make `data_sources` reflect what actually ran.

TWO EXCEPTIONS that stay Splunk even in a CQL-only package:
(1) `saved_searches` (Recommended Production Saved Searches) remain Splunk SPL —
write them as accelerated tstats against the bundled data models
(references/splunk_datamodels.md), because production detections run in Splunk ES.
When a saved search was executed during the hunt, append an "(Executed <date>:
<one-line result>)" annotation to its SPL.
(2) Nothing else.

OMIT the analyst-role metadata fields (hunt_lead, scribe, ti_threatq, crowdstrike,
proofpoint, splunk) — those role rows are dropped from the report by default and
only render if you explicitly provide a role.

## Supporting Splunk queries — accelerated tstats
Write SPL as accelerated `tstats` against the models in
`references/splunk_datamodels.md` (raw model JSON in `references/datamodels/*.json`
for exact field names) and pass them in `queries`. House pattern:

```
| tstats summariesonly=true count from datamodel=<Model>.<Object>
    where <Prefix>.<field>="..." [NOT (<Prefix>.<field>="<known FP>")]
    by <Prefix>.dest <Prefix>.user _time
| rename <Prefix>.* as *
| sort - _time
```

Rules that matter:
- Use the correct FIELD PREFIX (field-owner), which is not always the leaf node:
  Endpoint→leaf (Processes/Filesystem/Services/Ports); Malware→Malware_Attacks;
  Authentication→Authentication; Network_Sessions→All_Sessions;
  Network_Traffic→All_Traffic; Network_Resolution→DNS; Web→Web;
  <firewall-app>→log (nested nodes log.threat.vulnerability etc.);
  Email→All_Email.
- Tenant reality checks learned in production: there is NO "Windows" data model
  (7045 hunting has no accelerated path); Change.All_Changes is AWS CloudTrail
  only; the Web model IS the proxy/web layer and is the busiest accelerated
  source (<vendor>:threat at 1B+ events) — but Web.url stores the DOMAIN only with no
  request path, Web.dest collapses to "unknown", and Web.status/http_user_agent
  render "unknown"; O365 events reach the Authentication model but action/src
  collapse to unknown; Network_Resolution.DNS acceleration has been observed
  EMPTY — always run a bare control before trusting a zero. The M365 unified
  audit log IS available raw at `index=azure sourcetype=o365:management:activity`
  (plus o365:graph:api) — Entra AUDIT questions are Splunk native; only
  interactive SIGN IN questions are not.
- Add `NOT (...)` / `!Field=` exclusions for known false positives and note them
  in the query purpose.
- Keep unexecuted queries as STARTERS — validate field names against production;
  executed queries get a result summary appended to `purpose`.

## IOCs — always include
Populate the `iocs` array with every indicator the intel yields (domains, URLs,
IPs, hashes, user-agents, sender addresses). Defang externally-sourced network
IOCs (okta-sso-verify[.]com, hxxps://…). These render as the IOC Inventory table
and should be referenced from the queries.

## How to build
1. From the run's items, select every huntable item; draft an ABLE hypothesis for
   each (Actor, Behavior, Location, Evidence), time-bounded, ATT&CK-mapped.
2. For each, write PRIMARY CrowdStrike CQL queries (lead) + SUPPORTING per-source
   tstats queries, an ATT&CK/D3FEND table, and expected benign-vs-malicious notes.
3. Collect IOCs and 1-3 recommended production saved searches (named like
   TH26NN_<slug>) written as Splunk SPL tstats against the bundled data models.
4. Fill the metadata header with v2 keys: trigger source, IOC types, ACTUAL
   start/end times, duration, engines, campaign/actor tags, reviewed by. Set
   `doc_title` to "Threat Hunt Report" plus the hunt title after an em dash.
5. Build `overall_finding.blocks` + `investigation_note_lines` per house layout v2.
6. Mark every estate claim with `{{En}}` and build `evidence_appendix` per v3.
7. Run the four-step build (builder → proposed-hunts appender → restyler →
   evidence citation pass LAST).
8. Deliver with present_files, named `<YYYY-MM-DD>-<FriendlyName>-<UID>-Complete.docx`.

If `python-docx` is missing: `pip install python-docx --break-system-packages`.

## GeneLabs corporate branding (applied by the script)

Shared with the `genelabs-cti-bulletin` skill so hunt packages and bulletins read
as one set. Do not override these in a spec.

| Element | Value |
| --- | --- |
| Accent, section headings, rules, bullets | GeneLabs orange `#FF7109` (`#E05F00` for small heading text and table headers) |
| Body and headline text | Abbey `#444648` |
| Meta text, wordmark, captions | Corporate grey `#676765` |
| Callouts (handoff note, overall finding) | Fill `#FFF4E8` |
| Tables | Label fill `#F4F4F4`, `#D9D9D9` borders at 0.75pt, warm `#FFF8F2` row stripe |
| Links | `#1565C0` |
| Typeface | Arial for prose, Consolas for query code blocks |

Section headings render letterspaced in caps with a 1.5pt orange underline and,
after the restyler, 22pt space-before / 8pt space-after. Borders stay light grey
`#D9D9D9`. Every page carries the footer furniture: genelabs wordmark in corporate
grey, the TLP marking, the copyright line, a `DOC #` field carrying the `hunt_id`,
and live `Page X of Y` fields.

Optional spec key: `tlp` (defaults to `AMBER+STRICT`).


## JSON spec schema (v2 + v3 keys included)
```json
{
  "hunt_id": "TH26-33", "date": "August 18, 2026", "run_date": "August 18, 2026",
  "status": "Complete",
  "doc_title": "Threat Hunt Report — Vishing to Cloned SSO",
  "meta": {"hunt_title": "2026-08-18-VishingSSO-TH2633", "trigger_source": "...",
    "start_date": "2026-08-18  14:05 UTC", "end_date": "2026-08-18  14:19 UTC",
    "duration": "14 minutes (query wall time, sequential)",
    "engines": "Falcon (executed) + Splunk Cloud (executed)",
    "ioc_types": "Domains, URLs, IPs, Hashes",
    "campaign_actor_tags": "UNC6671, ShinyHunters", "reviewed_by": "[Pending Review]"},
  "investigation_note": "Hunt window: 2026-08-04T14:05Z to 2026-08-18T14:05Z - 14 day hard ceiling.",
  "investigation_note_lines": ["Executed via falcon-mcp and splunk-mcp-server against live telemetry.",
    "Queries run sequentially; zero-row results validated with bare controls."],
  "hypotheses": [{
    "title": "...", "priority": "High — possible exposure: GlobalProtect", "trigger_type": "Behavior driven",
    "able": {"actor": "...", "behavior": "...", "location": "...", "evidence": "..."},
    "hypothesis": "One paragraph, testable, time-bounded.",
    "data_sources": ["CrowdStrike Falcon (primary)", "Splunk Network_Traffic.All_Traffic (executed)"],
    "falcon": [{"name": "...", "event": "UserLogon / UserLogonFailed2",
                "purpose": "why + lookback + FP note (+ result summary if executed)",
                "cql": "..."}],
    "queries": [{"name": "...", "source": "Network_Traffic",
                 "purpose": "why + FP note + 'Executed <date>: <result>' when run", "spl": "| tstats ..."}],
    "attack": [{"id": "T1556", "tactic_technique": "...", "d3fend": "D3-AL", "defense": "...", "coverage": "Partial"}],
    "expected": "Benign vs malicious.",
    "sources": [{"title": "Outlet: Headline (date)", "url": "https://..."}]
  }],
  "iocs": [{"type": "Domain", "value": "okta-sso-verify[.]com", "source": "GTIG", "notes": "AitM lookalike"}],
  "saved_searches": [{"name": "TH2633_...", "spl": "| tstats ...  \n(Executed 2026-08-18: zero rows - clean baseline)"}],
  "include_classifications": true,

  "overall_finding": {"verdict": "Not Supported", "explanation": "__BLOCKS__",
    "blocks": [
      {"label": "Verdict", "body": "NOT SUPPORTED, High confidence. ...{{E1}}"},
      {"label": "Coverage caveat", "body": "..."},
      {"label": "What would change the verdict", "body": "..."}]},
  "findings": [{
    "num": 1, "title": "Short finding title", "type": "Identity / Account Takeover attempt",
    "confidence": "Medium", "classification": "Suspicious Activity",
    "evidence": "Concrete result: query, hosts/users, counts, timestamps.{{E1}}",
    "impact_rationale": "Attacker abuse scenario + why this classification.",
    "recommendation": ["Action 1", "Action 2"],
    "detection_opportunity": "Detection/saved-search to build from this."
  }],
  "gaps": [{"title": "...", "category": "Telemetry", "classification": "Environmental Gap",
    "detail": "...", "impact": "...", "remedy": "..."}],
  "proposed_hunts": [{"id": "-", "title": "...", "hypothesis": "...", "source": "F2",
    "telemetry": "...", "priority": "High", "disposition": "Handed to <team>"}],
  "evidence_appendix": [
    {"ref": "E1", "claim": "...", "queries": [{"engine": "Falcon CQL (NG-SIEM)", "query": "...", "result": "..."}],
     "reasoning": "..."}]
}
```
Classification values drive the color: Confirmed Compromise (red), Suspicious
Activity (amber), Benign/False Positive (green), Inconclusive (grey),
Environmental Gap (purple), Detection Engineering Need (blue),
Informational/Context (teal).

## Report layout (investigated hunts)
When `overall_finding` / `findings` are present the document renders as an
OPERATIONAL REPORT: metadata table (with the v2 delta row) → Investigation Summary
(short preamble lines, colour-coded Overall Finding, labeled verdict blocks,
linked findings index with PAGEREF fields) → hypotheses/queries/ATT&CK/expected/
sources → Findings — Detail (accent bars, chip strips, labelled blocks) →
Coverage & Gaps (auto-built from Environmental Gap / Detection Engineering Need
findings plus explicit `gaps`) → IOC Inventory, saved searches, classification
key → Proposed Follow On Hunts table (appender) → Evidence and Chain of
Reasoning appendix (citation pass, always the final section).

Suppressed automatically: blank Execution Log / Outcome sections (executed
reports), and the second MITRE table for single-hypothesis documents.

## Reference files
- `assets/hunt_template.docx` — branded template (clone this).
- `assets/genelabs_wordmark_grey.png` — footer wordmark, resolved automatically.
- `scripts/build_hunt_report.py` — the builder (run it; handles hyperlinks, tables, code).
- `scripts/restyle_report.py` — house layout v2 post-pass (write from the source below if absent).
- `<PACKAGES>/_tools/apply_evidence_citations.py` — v3 citation pass (also in CTI Deliverables `_tools`; write from the source below if both are absent).
- `references/crowdstrike_cql.md` — CrowdStrike CQL syntax + events/fields (PRIMARY).
- `references/splunk_datamodels.md` — data model → tstats cheat-sheet (supporting).
- `references/datamodels/*.json` — the raw GeneLabs data models (exact fields).

## Embedded source — scripts/restyle_report.py
Write this file verbatim into the skill's `scripts/` folder (or a scratch folder)
if it does not exist, then run `python scripts/restyle_report.py <report.docx> <spec.json>`.

```python
#!/usr/bin/env python3
"""House layout v2 post-pass for GeneLabs Threat Hunt Reports.
1. Appends the Hunt Duration (Delta) / Engines row from meta.duration / meta.engines.
2. Replaces the __BLOCKS__ marker (or inserts after the Overall Finding box) with
   labeled verdict paragraphs from overall_finding.blocks.
3. Inserts investigation_note_lines after the investigation_note paragraph.
4. Sets every orange section heading to 22pt before / 8pt after.
Idempotence: safe to run once per report. Running twice duplicates the delta row
and note lines, so run exactly once, after builder + proposed-hunts appender.
"""
import json, sys
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FONT="Arial"; ABBEY="444648"; DEEP="E05F00"; ORANGE="FF7109"; GREY="676765"; META_LABEL="F4F4F4"

def run(p,text,size=10,bold=False,color=ABBEY,italic=False):
    r=p.add_run(text); r.font.name=FONT; r.font.size=Pt(size); r.font.bold=bold
    r.font.italic=italic; r.font.color.rgb=RGBColor.from_string(color); return r

def insert_after(anchor,new_p): anchor._p.addnext(new_p._p)

def delta_row(doc,meta):
    dur=meta.get("duration"); eng=meta.get("engines")
    if not (dur or eng): return
    t=doc.tables[0]; cells=t.add_row().cells
    spec=[("Hunt Duration (Delta)",True),(dur or "",False),("Engines",True),(eng or "",False)]
    for cell,(val,bold) in zip(cells,spec):
        if bold:
            tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement("w:shd")
            shd.set(qn("w:val"),"clear"); shd.set(qn("w:fill"),META_LABEL); tcPr.append(shd)
        cell.paragraphs[0].text=""; run(cell.paragraphs[0],val,size=9,bold=bold)

def summary_blocks(doc,spec):
    ov=spec.get("overall_finding") or {}; blocks=ov.get("blocks")
    if not blocks: return
    target=None
    for p in doc.paragraphs:
        if p.text.strip()=="__BLOCKS__": target=p; break
    if target is None:
        for p in doc.paragraphs:
            if p.text.strip().startswith("Overall Finding:"):
                target=doc.add_paragraph(); insert_after(p,target); break
    if target is None: return
    for r in list(target.runs): r._element.getparent().remove(r._element)
    lbl,body=blocks[0]["label"],blocks[0]["body"]
    run(target,lbl.upper()+"   ",size=9.5,bold=True,color=DEEP); run(target,body,size=10)
    target.paragraph_format.space_before=Pt(6); target.paragraph_format.space_after=Pt(7)
    anchor=target
    for b in blocks[1:]:
        np=doc.add_paragraph()
        run(np,b["label"].upper()+"   ",size=9.5,bold=True,color=DEEP); run(np,b["body"],size=10)
        np.paragraph_format.space_after=Pt(7); insert_after(anchor,np); anchor=np

def note_lines(doc,spec):
    lines=spec.get("investigation_note_lines") or []
    first=(spec.get("investigation_note") or "").strip()
    if not lines or not first: return
    anchor=None
    for p in doc.paragraphs:
        if p.text.strip()==first: anchor=p; break
    if anchor is None: return
    anchor.paragraph_format.space_after=Pt(2)
    for line in lines:
        np=doc.add_paragraph(); run(np,line,size=9,italic=True,color=GREY)
        np.paragraph_format.space_after=Pt(2); insert_after(anchor,np); anchor=np
    anchor.paragraph_format.space_after=Pt(6)

def air(doc):
    for p in doc.paragraphs:
        pPr=p._p.find(qn('w:pPr'))
        if pPr is None or pPr.find(qn('w:pBdr')) is None or not p.runs: continue
        r=p.runs[0]
        col=r.font.color.rgb if (r.font.color and r.font.color.type) else None
        if r.font.bold and str(col) in (DEEP,ORANGE) and p.text.strip()==p.text.strip().upper() and len(p.text.strip())>3:
            p.paragraph_format.space_before=Pt(22); p.paragraph_format.space_after=Pt(8)

if __name__=="__main__":
    doc=Document(sys.argv[1]); spec=json.load(open(sys.argv[2]))
    delta_row(doc,spec.get("meta",{})); summary_blocks(doc,spec); note_lines(doc,spec); air(doc)
    doc.save(sys.argv[1]); print("restyled:",sys.argv[1])
```

## Embedded source — apply_evidence_citations.py (v3 citation pass)
Identical copies live in the threat hunt PACKAGES `_tools` folder and the CTI
Deliverables root `_tools` folder. Prefer those; write this verbatim only if both
are unreachable. Run LAST: `python3 apply_evidence_citations.py <out.docx> <spec.json>`.

```python
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
```

