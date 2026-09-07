# CTI Weekly Perimeter Scan

You are supporting April, the Cyber Threat Intelligence (CTI) Lead at GeneLabs LLC This runs
on April's workstation as a scheduled local job. Nobody is present to answer questions, so
execute autonomously, make reasonable choices, and note every choice you made in the run output.
Take a write action only where this file asks for that specific action. When in doubt, producing
a report of what you found is the correct output.

Once a week you rebuild the **Open Exposures Team Briefing**: ONE LANDSCAPE PAGE rolling up every
OPEN exposure advisory, one row per exposed asset, which April talks a team through, FOLLOWED BY
**APPENDIX A**, the validation and reasoning pages that let a reader reproduce every row.
Report id `CTI-BRIEF-YYYY-MM-DD`.

`scripts/run_briefing.py` appends a RUN CONTEXT block to the end of this file giving the exact
advisory folder, output path, builder and style directory for this run. Those override any path
written here.

## Repo layout

| Thing | Path |
| --- | --- |
| Builder, and where row content lives | `tools/build_exposure_briefing.py` |
| Clean template and brand assets | `tools/assets/` |
| Orphan link stripper | `tools/strip_orphan_links.py` |
| SPL linter | `tools/splunk_spl_lint.py` |
| Skills | `.claude/skills/` |
| Verification gate | `scripts/verify_briefing.py` |
| Source advisories and output | see `config.yaml`, and the RUN CONTEXT block below |

## STEP 1 - read the skill first

Read `.claude/skills/genelabs-exposure-team-briefing/SKILL.md`. It is the source of truth for the
format, the column widths, the colour rules and the build. Everything below supplements it; where
they disagree the skill wins and you should say so in the run output.

ONE KNOWN DEVIATION, DECIDED BY APRIL ON 2026-08-29. The skill says "one landscape page, a table
and nothing else". That still governs PAGE ONE. Appendix A now follows on pages two onward, the
same shape the exposure advisories use: one page body, then the working. Do not let the appendix
push anything onto page one, and do not let it grow into a second table of findings.

## STEP 2 - preflight

`run_briefing.py` has already checked that the advisory folder is reachable and has listed what is
in it. Read that list. If it is empty or the folder was unreachable the run has already stopped.
Never build from a partial or remembered set: a briefing built from a half synced SharePoint library
reads as complete, which is worse than no briefing.

## STEP 3 - rebuild the row set from the folder

Do not edit last week's rows.

- An advisory whose exposure is CLOSED comes out of the table entirely.
- An advisory whose status moved gets its "Where it stands" cell rewritten, and if the underlying
  finding changed, its risk cell too.
- A new advisory raised during the week gets a new row.
- One row per OPEN advisory. If one asset has more than one advisory, that is an error in the
  advisory set (one asset, one advisory), so report it rather than creating two rows.

**WHERE ROW CONTENT COMES FROM. THE SKILL'S GUIDANCE ON THIS IS STALE AND YOU MUST NOT FOLLOW IT
LITERALLY.** The skill says to read each advisory's "The Risk" section. THAT SECTION NO LONGER
EXISTS: the advisory format was rewritten on 2026-08-27 to a one page body, and the Risk table,
the Bottom Line and the Severity row were all removed. Build each row from what the current format
actually contains:

- the SUMMARY CALLOUT for the asset, what it is, and what was found;
- the THREE "Why We Care" BULLETS for the risk in prose;
- the ACTION TABLE for the next action and its owner function;
- APPENDIX A.6 for the verdict and the open question;
- APPENDIX A.2 and A.3 for the traffic and enrichment numbers behind the two flag columns.

An advisory that still carries a "The Risk" section predates the migration. Use it, and say so in
the run output, because it means the advisory set is inconsistent.

## STEP 4 - the two flag columns are the point of the format

- **EDR** answers "would we see anything if this went wrong". Yes / Partial / No / n/a.
- **KNOWN BAD TRAFFIC ALLOWED** answers "has something our own threat intelligence already
  condemned reached this asset and been permitted". YES / None seen. Where this reads YES it is
  the strongest risk signal on the page and that row should usually lead the discussion.
- Colour: red for `No` and for `YES`, amber for `Partial`, green for `Yes`, grey for `n/a`. Red
  marks a MISSING sensor and PRESENT bad traffic. Both are bad news even though one is a "no" and
  one is a "yes".
- **`n/a` IS NOT `No`.** An external SaaS platform has no endpoint sensor because it is not an
  GeneLabs host, not because a control is missing. Writing `No` there invents a gap.
- **"None seen" IS NOT "No".** Absence of an observed known bad source is not proof none reached
  the asset. Do not tidy that into a cleaner looking `No`.

## STEP 5 - voice

The reader is being briefed, not handed a fix. Say the thing, not the identifier: "WinRM is remote
command execution, not a passive listener", not "TCP 5985 exposed". No MITRE identifiers, no query
language, no data model names, no CVSS vectors; those belong in the advisory the row links to.

NUMBERS STAY. "150,000 allowed connections in a single day" is the argument. Round nothing that is
evidence.

"WHERE IT STANDS" IS WHAT MAKES THE BRIEFING WORTH HOLDING. A list of findings is a status report;
a list with STILL OPEN, LIVE, or "stopped on its own, configuration unchanged" against each row is
a conversation about why they are still here. Where an exposure was re-checked and had not moved,
say so; that fact does more work than any severity rating.

DO NOT PRINT THE ANALYSIS ON PAGE ONE. The analysis is what April says out loud, and printing it
removes her reason to speak. The table is the reference, she is the argument. The REASONING behind
the FORMAT is a different thing and belongs in Appendix A.5.

## STEP 6 - links

Every row's advisory reference is a live hyperlink to the SharePoint copy, and the intro links the
containing folder. USE SHAREPOINT URLS, NEVER `file:///`: a local profile path resolves only on
April's machine and a briefing gets forwarded. Build each from the library folder path in
`config.yaml` plus the percent encoded filename, taking every filename FROM DISK and never typing
one from memory.

python-docx has no hyperlink API. Build the `w:hyperlink` element by hand and give the run its own
`rPr` so it keeps Arial at 6.5pt rather than inheriting Word's Hyperlink style. The builder already
does this; do not reimplement it.

## STEP 7 - refresh what can be refreshed, and be honest about the rest

Before writing any "Where it stands" cell, re-check every EXTERNALLY OBSERVABLE asset listed under
`run.externally_observable` in `config.yaml` with a read only Shodan host lookup on its address,
and let the result rather than the advisory set the status cell. On 2026-08-29 this is how
GLCN-PRD-APPS01 was found to have grown a third exposed service since its advisory was written.

TWO CLASSES CANNOT BE REFRESHED THIS WAY AND YOU MUST NOT TRY. An outbound tunnel host reports
CLOSED to external scanning, so a clean scan there is a FALSE NEGATIVE and not good news; and an
external SaaS platform is not ours to scan. `config.yaml` lists these under `run.not_scannable`
with the reason for each.

**IF THE SHODAN CONNECTOR IS NOT CONFIGURED, DO NOT GUESS AND DO NOT SILENTLY CARRY FORWARD LAST
WEEK'S WORDING.** Say in the run output that no live re-check was possible, mark every row
INHERITED in Appendix A.1 with the date its advisory established it, and make the status cells read
as of that date rather than as of today.

Firewall figures and both flag columns come from Splunk and are INHERITED unless you actually run
the searches. If you do run them, read `.claude/skills/genelabs-splunk-spl/SKILL.md` first and lint
every query with `tools/splunk_spl_lint.py` before executing it.

## STEP 8 - build

Content lives in the builder's own `ROWS` list, with the appendix content in `PROVENANCE`,
`RUN_STEPS` and `VERIFY_STEPS`. **EDIT THOSE LISTS DIRECTLY.** Do NOT patch them with `re.sub`: a
replacement string interprets backslash escapes, so every `\n` in the asset cells becomes a real
newline and the file stops parsing. That has broken the builder once already.

```
python tools/build_exposure_briefing.py "<output .docx>" ".claude/skills/genelabs-exposure-advisory"
```

The report id is DERIVED FROM THE OUTPUT FILENAME, so a weekly rebuild cannot ship last week's
identifier. Use the filename given in the RUN CONTEXT block.

## STEP 9 - Appendix A must be rebuilt, not inherited

It is pages two onward and it is the working behind page one.

- **A.1 Provenance, one entry per row.** For every row state where the row TEXT came from (which
  advisory sections), then mark the exposure state either **MEASURED IN THIS RUN** or
  **INHERITED, ESTABLISHED &lt;date&gt;**, and say what backs it. THIS IS THE WHOLE POINT OF THE
  APPENDIX. A weekly roll-up is assembled mostly from advisories written on earlier dates, while
  page one argues that these exposures are STILL here. Presenting inherited evidence as freshly
  measured is the single way this format can mislead, and it would be worse than having no appendix
  at all. `scripts/verify_briefing.py` fails the run if any entry is unlabelled.
- **A.2 Steps measured in THIS run.** The exact connector calls, verbatim, the results returned,
  and for each one what it ESTABLISHES and, the load bearing part, what it DOES NOT ESTABLISH.
  Carry forward any trap from the source advisory, such as a cached Shodan banner, or a hostname
  search that returns zero because the index is keyed on the address.
- **A.3 Evidence NOT rerun this week, and where its walkthrough lives.** Name which rows could not
  be refreshed and why, distinguishing "not refreshed" from "not refreshable". Point to the linked
  advisory's own Appendix A.7.
- **A.4 How the document itself was verified**, with the method and the result for each check in
  STEP 10, so a reader can repeat them.
- **A.5 The reasoning: why the page is built this way.** Why two flag columns and no severity
  column; why `n/a` is not `No` and `None seen` is not `No`; why the status column earns the
  meeting; and the one unanswered question per row that would move it. This section argues about
  the FORMAT, not about the findings.

Keep the appendix in the house identity: same banner, same footer, Arial only, shaded header rows,
and `cantSplit` plus a repeating header row on every appendix table so no row is orphaned across a
page break.

## STEP 10 - verify programmatically, then look at it

Run the gate and make it pass:

```
python scripts/verify_briefing.py "<output .docx>"
```

It checks: every page 792 x 612 pt; page one carries every asset and no appendix text; every row
has an owner; every row links its advisory and every target resolves against a file on disk; zero
orphaned relationships and zero external targets that are not SharePoint; no `file:///`; Arial
only; footer DOC # matching the filename, TLP, page field and wordmark; no flag value broken mid
word; and A.1 carrying one labelled provenance entry per row.

Then also confirm by reading, which the gate cannot do: that no row contradicts the advisory it
links to, and that A.1 does not contradict the row. **THEN RENDER EVERY PAGE AND LOOK AT THEM.**
Most remaining defects are visual.

## When page one will not fit

Change the document's shape rather than shaving words, in the order that has actually worked:

1. Delete a column whose values repeat. A severity column reading HIGH six times carries no
   information and its width is better spent on prose.
2. Move width from the columns with spare lines (asset, action) into the two prose columns, which
   are what set every row's height.
3. Reduce the side margins, remembering that a wider body makes the banner TALLER because it
   scales to body width. Measure the result rather than assuming it helped.
4. Put a per row reference inline rather than on its own line.
5. Trim only the outlier cells that exceed the line budget, and never a number.

## STEP 11 - report

Save the .docx and the PDF into the Team Briefings folder, confirm both paths, and report in a few
lines:

- how many advisories were open and how many rows the table carries;
- which rows are NEW this week, which CHANGED status, and which CLOSED and were removed;
- any row where KNOWN BAD TRAFFIC ALLOWED reads YES, called out separately because it should lead
  the discussion;
- which rows were MEASURED in this run and which were INHERITED, and if no live re-check was
  possible, say so plainly;
- the verification result including the page size, the page count and the hyperlink check;
- anything that looked wrong in the advisory set itself: two advisories for one asset, a stale
  "The Risk" section, an advisory whose status could not be determined from its own text, or an
  advisory that the live re-check has now overtaken and which therefore needs reissuing.

If there are NO open advisories, do not build an empty document. Say so in one line. That is a
successful no-op run, not a failure.
