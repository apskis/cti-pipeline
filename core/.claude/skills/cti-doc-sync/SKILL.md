---
name: cti-doc-sync
description: "Run the monthly GeneLabs CTI documentation sync. Reconciles CTI_Plan.docx, Threat Hunting Plan.docx and CTI_AI_Strategy_Evolving.pptx against the CTI Deliverables folder, which is the source of truth for the portfolio, then updates the state record and writes a run report. Use for the monthly doc sync, the CTI documentation reconciliation, or when asked to bring the plans and the AI strategy deck back in line with what the portfolio actually contains."
---

# CTI Documentation Sync

You maintain April Parker's CTI documentation at GeneLabs. The CTI Deliverables
folder is the evolving source of truth for the CTI portfolio; the plan documents
and the strategy deck are maintained representations of that source. Your job is
to keep those representations accurate, internally consistent, traceable,
strategically current and consistently branded, while making as few edits as
possible.

Read `context/doc-sync-standing-context.md` and `context/preferences.md` in the
repository root before you start. They carry April's standing decisions about
this task and how she wants copy written.

## Step 0: date guard

This skill is scheduled on the 1st, 2nd and 3rd of each month and does work only
on the FIRST WEEKDAY of the month.

```
python scripts/date_guard.py
```

Exit code 0 means proceed. Exit code 10 means stop immediately, change nothing,
and reply only: `Not the first weekday of the month. No action taken.`

Skip this step when a human invoked the skill directly and asked for an
off-schedule run. Say in the run summary that the guard was bypassed.

## Locations

All paths come from `cti.config.json` in the repository root. Never hard code
them; read that file. It resolves to two folders on the local machine:

- `deliverables` — the CTI Deliverables tree, the source of truth
- `documentation` — the CTI Documentation tree

Documents you maintain, all under `documentation/Strategy_and_Plan`:

1. `CTI_Plan.docx` — the CTI program plan. Change history is the "Release
   History" table. Columns: Version, Date, Originator, Description of Change.
   Two digit versions, dates formatted `YYYY.MM.DD`, Originator "April Parker".
2. `Threat Hunting Plan.docx` — change history is the table under
   "12. Revision History". Decimal versions, dates formatted `YYYY-MM-DD`.
3. `CTI_AI_Strategy_Evolving.pptx` — the living AI strategy deck.

Current versions are recorded in the state record, not here. Read them from it.

**NEVER write to `CTI Strategy.pptx` or `CTI Strategy-Reference for April.pptx`.**
They are off limits. Read them only for context.

Supporting locations, all under `documentation/_doc_sync`:

- `portfolio_state.md` — the state record
- `backups/` — timestamped pre-edit backups
- `runs/` — run reports, one per run

## Step 1: read the state record

Read `_doc_sync/portfolio_state.md` in full. It describes the portfolio as of
the last run, records the house branding standard, and carries a "Known drift"
work list plus a run history table. This is your comparison baseline, not file
timestamps.

## Step 2: analyze the deliverables folder

Walk the deliverables tree and inspect it with ordinary shell tools. The folder
is large, so count and grep before you open anything. Read the running logs
`cti-bulletin-log.md` and `CTI Threat Hunts/Threat Hunt Packages/falcon-hunt-log.md`,
which summarize recent output cheaply.

```
python scripts/survey_deliverables.py            # inventory by class, counts, newest per class
python scripts/survey_deliverables.py --since 2026-08-21
```

Compare what you find against the state record and identify:

- New CTI products or deliverable classes
- Removed or deprecated products
- Material changes to existing products
- Changes in capabilities, workflows, architecture, integrations or dependencies,
  for example a change in which platform hunts are authored against, or new
  tooling under `_tools` and `_skill_patches`
- Changes in terminology or product positioning, for example the bulletin
  category taxonomy or the hunt identifier scheme
- New AI capabilities, opportunities, risks or strategic implications
- Documentation statements that have become outdated or inconsistent

Do not treat every file modification as a documentation change. One more weekly
report in an established series is routine. A new artifact type, a changed
cadence, a new platform, or a new automated pipeline is material.

## Step 3: update the documentation in place, with backups

April chose edit in place with backups. For every document you are about to
change:

1. Back it up first. Never skip this.
   ```
   python scripts/backup_doc.py "<full path to the document>" --reason falcon-loop
   ```
   That writes `_doc_sync/backups/<name>_<YYYYMMDD>-pre-<reason>.<ext>` and
   prints the path.
2. Edit the document with `python-docx` or `python-pptx`.
3. Run the branding pass, then render to PDF and look at it before you accept
   the result. Most defects in these documents are visual.

Preserve existing structure, formatting, tone and level of detail unless a
structural change is genuinely needed. Do not remove historical or contextual
information just because newer material exists. Do not rewrite unchanged
material.

When inserting content into an existing document, clone an existing paragraph of
the target style and replace its text, rather than creating a paragraph from the
style name. Word's heading styles in these documents carry list numbering, and a
paragraph created from the style name picks up a stray automatic number.

## Step 3b: apply the house branding

Every document you edit must leave in the GeneLabs CTI house style, which is
shared with the bulletin and hunt skills: Enterprise Information Security banner
sitting clear of the first body element, GeneLabs orange `FF7109` headings and
rules, Abbey `444648` body, corporate grey `676765` meta text, Arial throughout,
and a footer carrying the wordmark, the marking text, the copyright line, DOC #
and live page fields.

Internal program documentation carries NO TLP marking. TLP is a sharing
designation, not a classification, so it belongs on bulletins and anything
leaving GeneLabs, not on the plans. The restyler defaults to no TLP; do not pass
`--tlp` on these documents.

Use the `genelabs-cti-documentation` skill. Run the restyle AFTER the content
edits, never before.

```
python .cursor/skills/genelabs-cti-documentation/scripts/restyle_cti_doc.py in.docx out.docx \
  --doc-id "CTI-PLAN-10" \
  --marking "CTI Program Documentation" \
  --copyright "© 2026 GeneLabs LLC  |  Proprietary and Confidential — For Internal Use Only"

python scripts/render_pdf.py out.docx        # then open the PDF and look at it
```

Set `--doc-id` to the document slug plus its new version.

## Step 4: maintain document control

For every document you materially changed, append one row to its change history
table using today's actual date and the document's own version and date
conventions. Record the version, the date, the originator, and a concise
description naming the sections affected and the reason or source, for example
"Section 4 Hunt Triggers updated to reflect the automated Falcon hunt loop;
source: TH26-01 through TH26-13".

Do not create a revision entry when no substantive change was made. A branding
pass on its own is not program history. Never edit a document solely so that a
revision entry can be written.

## Step 5: evolve the AI strategy deck

Review `CTI_AI_Strategy_Evolving.pptx` against the current deliverables and
update it only when the evidence supports a change in strategy. Evaluate whether
developments affect: AI strategy and vision, AI enabled CTI capabilities,
automation opportunities, the human and AI operating model, agentic or autonomous
workflows, data and intelligence requirements, integration opportunities,
governance, security and risk, near, medium and long term priorities, and the
strategic roadmap and recommendations.

The deck must evolve strategically, not simply accumulate text. Keep the GeneLabs
layouts, master, palette and slide design intact; reuse existing slide layouts
rather than inventing new visual treatments.

On every slide you touch, keep three things clearly distinguishable:

- Observed facts drawn from the deliverables
- Reasonable strategic implications
- Recommendations or proposed future direction

Label recommendations as recommendations. Never present a speculative
recommendation as an established capability. Every strategic change must trace to
new evidence, a changed assumption or a development in the portfolio, and you
must name that evidence in the run summary.

## Step 6: quality and traceability check

Before you accept anything, verify:

1. Every material claim is supported by something actually present in the
   deliverables.
2. No contradictions exist across the plan documents and the deck.
3. Branding matches the house standard and existing design is preserved.
4. Unchanged material was left alone.
5. Terminology is consistent across all artifacts.
6. Revision histories accurately describe what changed.
7. Each strategic deck change traces back to named evidence.

## Step 7: update the state record

Rewrite `_doc_sync/portfolio_state.md` so it describes the portfolio as it stands
after this run: refresh the deliverable class inventory, remove drift items you
reconciled, add newly found drift, update the document version table, and append
a row to the run history.

## Step 8: run summary

Write the summary to `_doc_sync/runs/<YYYY-MM-DD>-doc-sync.md` and print it.
Cover:

- Deliverables added, removed or materially changed
- Documents updated
- Document control entries created
- PowerPoint slides changed
- Strategic implications identified
- Recommendations introduced or modified
- Items requiring human review
- Ambiguities or conflicts discovered

Then raise it where April will see it:

```
python scripts/notify.py --title "CTI doc sync" --report "<path to the run report>"
```

If nothing material changed, make no edits at all and report exactly:
`No material changes detected. Documentation and strategy remain current.`

## Running unattended

When this runs from the scheduler nobody is watching. Do not ask clarifying
questions. Where a judgment call is needed, make the conservative choice, apply
it, and flag it under items requiring human review. If a configured folder is
missing or unreadable, report that and change nothing.
