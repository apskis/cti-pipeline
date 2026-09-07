---
name: "genelabs-exposure-team-briefing"
description: "Build the GeneLabs weekly EXPOSURE ADVISORY team briefing as a LANDSCAPE one page .docx — the roll-up across every OPEN exposure advisory, one row per exposed asset, each row hyperlinked to its full advisory in SharePoint. Carries EDR coverage and a \"known bad traffic allowed\" flag per asset, and a \"Where it stands\" column that turns a status list into a conversation. Run automatically each Friday by the cti-weekly-open-exposures-briefing scheduled task. Use for the weekly open exposures briefing, a team or stand-up roll-up of the exposure advisory set, or a request to put all the exposures on one page to explain them to a team. For a single asset handed to its owner use genelabs-exposure-advisory; for a CVE queue use genelabs-cve-priority-brief; for a hunt roll-up use genelabs-hunt-run-summary."
---

# GeneLabs Exposure Advisory Team Briefing

The weekly **CTI-BRIEF-YYYY-MM-DD** deliverable: one LANDSCAPE page rolling up every
OPEN exposure advisory, one row per exposed asset, that the CTI lead talks a team
through.

> **This is not an advisory with more rows.** An exposure advisory is one asset handed
> to the team that owns it, and it argues its case. This briefing is every open
> exposure at once, and it does not argue — **the analysis is what the presenter says
> out loud.** Printing the analysis removes their reason to speak.

**Scheduled.** The `cti-weekly-open-exposures-briefing` task runs this every Friday at
15:00, deliberately BEFORE the 16:03 CTI Threat Hunting Automation, which can write a new advisory into the
same folder this reads. An advisory raised by Friday's hunt therefore lands in next week's
briefing — a one working day lag on at most one row, which beats building from a
half-written folder.

| Artifact | Skill |
| --- | --- |
| One exposed asset, for its owner | `genelabs-exposure-advisory` |
| **All open exposures, for a team** | **this skill** |
| A CVE queue for Vulnerability Management | `genelabs-cve-priority-brief` |
| A day of hunts | `genelabs-hunt-run-summary` |

## Where things live

| Item | Path |
| --- | --- |
| Builder | `CTI Deliverables\_tools\build_exposure_briefing.py` |
| Clean template and assets | `CTI Deliverables\_tools\assets\` |
| Orphan link stripper | `CTI Deliverables\_tools\strip_orphan_links.py` |
| Source advisories | `CTI Deliverables\Exposure Advisories\` |
| Output | `...\Exposure Advisories\Team Briefings\YYYY-MM-DD-Open_Exposures_Team_Briefing.docx` |

Report id **`CTI-BRIEF-YYYY-MM-DD`**, DERIVED FROM THE OUTPUT FILENAME so a weekly
rebuild cannot ship last week's identifier. Deliver the PDF alongside the .docx: the
.docx is the editable record, the PDF is what gets screen shared.

## Scope — which rows belong

One row per **OPEN** advisory in `Exposure Advisories\`. Rebuild the set from that folder
each week rather than editing last week's rows:

- an advisory whose exposure has been CLOSED comes out of the table entirely;
- an advisory whose status moved gets its "Where it stands" cell rewritten, and if the
  underlying finding changed, its risk cell too;
- a new advisory raised during the week gets a new row.

If one asset has two advisories, that is an error in the advisory set — one asset, one
advisory — so report it rather than creating two rows.

## WHERE ROW CONTENT COMES FROM — updated 2026-08-27

**This skill previously said to read each advisory's "The Risk" section. THAT SECTION NO
LONGER EXISTS.** The exposure advisory format was rewritten on 2026-08-27 to a ONE PAGE
body, and the Risk table, the Bottom Line and the Severity row were all removed. Build
each row from what the current format actually contains:

| Row content | Comes from |
| --- | --- |
| Asset, and one line of what it is | The summary callout |
| What is exposed, and why we care | The three "Why We Care" bullets |
| Next action / owner | The action table (five rows; any overflow is in A.8) |
| The verdict and the open question | **Appendix A.6**, now severity as a figure plus two short paragraphs |
| The two flag columns | **Appendix A.2** perimeter traffic and **A.3** permitted sources and enrichment |

An advisory that still carries a "The Risk" section predates the migration — use it, and
say so in the run output, because it means the advisory set is inconsistent.

The briefing row is that material compressed to what can be read from across a room. **It
must not contradict the advisory it links to.**

## The shape, and why

**ONE LANDSCAPE PAGE. A table, and nothing else.**

Landscape has width to spend and no depth to spend. Every layout problem here is solved by
using width or by removing something — never by dropping below 8pt, which is where a
projected page stops being readable.

| Column | Width | Carries |
| --- | --- | --- |
| Asset / advisory | 1.72 | Name, one line of what it is, and the linked advisory id |
| EDR | 0.62 | Yes / Partial / No / n/a |
| Known bad traffic allowed | 0.78 | YES / None seen |
| What is exposed, and why we care | 3.20 | The exposure named in the opening clause, then the risk |
| Where it stands | 1.48 | Status as at the briefing date |
| Next action / owner | 1.45 | One action, one owner function |

### The two flag columns are the point of the format

**EDR** answers "would we see anything if this went wrong". **KNOWN BAD TRAFFIC ALLOWED**
answers "has something our own threat intelligence already condemned actually reached this
asset and been permitted". Where the second reads YES, that is the strongest risk signal
on the page and that row should usually lead the discussion.

Colour: red for `No` and for `YES`, amber for `Partial`, green for `Yes`, grey for `n/a`.
Red marks a MISSING sensor and PRESENT bad traffic — both are bad news, even though one is
a "no" and one is a "yes".

**`n/a` is not `No`.** An external SaaS platform has no endpoint sensor because it is not
an GeneLabs host, not because a control is missing. Writing `No` there invents a gap.

**"None seen" is not "No".** Absence of an observed known bad source is not proof none
reached the asset. Do not tidy that wording into a cleaner looking `No`.

### "Where it stands" is what makes the briefing worth holding

A list of findings is a status report. A list with **STILL OPEN**, **LIVE**, or **stopped
on its own, configuration unchanged** against each row is a conversation about why they are
still here. Where an exposure was re-checked and had not moved, say so — that fact does
more work than any severity rating.

## Voice

The reader is being briefed, not handed a fix. Say the thing, not the identifier.

- "WinRM is remote command execution, not a passive listener" — not "TCP 5985 exposed".
- "the connection goes outward" — not "egress tunnel over TLS 443".
- No MITRE identifiers, no query language, no data model names, no CVSS vectors. Those
  belong in the advisory the row links to.
- Numbers stay. "150,000 allowed connections in a single day" is the argument; round
  nothing that is evidence.

## Every row links to its advisory

The reference under each asset is a **live hyperlink to the SharePoint copy**, and the
intro links the containing folder. A briefing that names a document without linking it
makes the reader go and find it, which they will not do.

**Use SharePoint URLs, never `file:///`.** A local profile path resolves only on the
author's machine, and a briefing gets forwarded. Build each from the library folder path
plus the percent encoded filename, taking every filename FROM DISK:

```
https://<your-tenant>.sharepoint.com/teams/SecOps/SOC/Shared%20Documents/CTI/CTI%20Deliverables/Exposure%20Advisories/<file>
```

That folder path is the decoded `id=` parameter of the library's own view URL. Derive it
that way if the library ever moves, rather than retyping it.

python-docx has **no hyperlink API**. Build the `w:hyperlink` element by hand and give the
run its own `rPr` so it keeps Arial at 6.5pt instead of inheriting Word's default Hyperlink
style, which would break the house typeface rule.

## The house template carries orphaned links — strip them

`cti_doc_template.docx` was made by taking a finished bulletin, deleting its body and
saving. Word kept the relationship part, so the "blank" template still carries **eleven
external relationships** to news outlets, the SEC, HHS and a ServiceNow catalogue item.
Nothing references them and nothing renders, but they are embedded in every document
cloned from it, and external news links inside a TLP:AMBER+STRICT document look wrong to
anyone inspecting the file or running DLP across it.

A cleaned copy lives at `CTI Deliverables\_tools\assets\cti_doc_template.docx` and the
builder prefers it. If you ever build from the skill's own copy, run
`strip_orphan_links.py` afterwards — it removes only relationships that are BOTH external
AND unreferenced, so images, styles and real links are untouched.

## Build

```
python3 "CTI Deliverables/_tools/build_exposure_briefing.py" \
        "CTI Deliverables/Exposure Advisories/Team Briefings/YYYY-MM-DD-Open_Exposures_Team_Briefing.docx" \
        <genelabs-exposure-advisory skill dir>
```

The skill directory argument supplies the shared style module and the banner, so this
briefing cannot drift from the advisories it summarises.

Content lives in the builder's own `ROWS` list — **edit that list directly.** Do NOT patch
it with `re.sub`: a replacement string interprets backslash escapes, so every `\n` in the
asset cells becomes a real newline and the file stops parsing. That has broken it once.

## Verify before delivering

- **ONE page, landscape.** Convert to PDF, count pages, confirm the page size is
  792 x 612 pt. Do not estimate.
- Every row has an owner function in the last column.
- Every advisory reference is a hyperlink and **every target resolves** — extract the
  relationship targets and check each against the file on disk. A link pointing nowhere
  looks identical to a working one until somebody clicks it in front of an audience.
- Zero external relationships that are not SharePoint; zero orphaned relationships.
- No flag value wraps mid word. `Partial` in a narrow column rendering as "Partia / l"
  reads as a rendering fault and undermines the column it should make prominent.
- Row content does not contradict the advisory it links to.
- Fonts resolve to Arial only; footer carries the wordmark, TLP, `DOC #` and page field.
- Then render page one and LOOK at it.

## When it will not fit

Change the document's shape. Do not shave words — that costs many iterations and gains
almost nothing. In the order that has actually worked:

1. **Delete a column whose values repeat.** A severity column reading HIGH six times
   carries no information, and its width is better spent on prose.
2. **Turn a stacked list into a row.** Three stacked bullets ran to eight lines; the same
   three as table columns took three.
3. **Put a per row reference inline** rather than on its own line — six extra lines across
   a six row table is most of what pushes a page over.
4. **Cut a whole section.** The analysis can usually go, because the presenter is about to
   say it.

