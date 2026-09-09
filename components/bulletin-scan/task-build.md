# Bulletin scan: builder pass

You are the BUILDER pass of the GeneLabs CTI bulletin scan. The scan pass has already
run today: it researched the feeds, updated the CVE register, and assigned IDs in
`state/dedup-log.md` for every deliverable it wants. Your only job is to turn a batch of
those IDs into documents on disk. Nobody replies; there is no time limit; do not defer.

## Input

`state/_work/pending.json` under the output folder lists this batch: for each item an
`id`, a `kind` and the `evidence` (the dedup log entry, which names the sources, KEV
status, exploitation, patch and scale). Today's scan report is
`reports/scan-YYYY-MM-DD.md` and carries the ranked ideas with their why it matters and
sources. The register is `registers/CVE_Register_2026.xlsx`. Read these; use WebFetch only
to confirm a source detail you need for the document.

## How to build each kind

- **bulletin** (`CTI26-NN`): the `genelabs-cti-bulletin` skill. Audience line starts
  "DRAFT for April's review". Save as `bulletins/2026/CTI26-NN-Title_Case_Slug.docx`.
  Builder: `python3 core/.claude/skills/genelabs-cti-bulletin/scripts/build_bulletin.py <spec.json> <out.docx>`.
- **hunt** (`TH26-NN`): the `genelabs-threat-hunt-package` skill, one hypothesis per
  package. Falcon, Splunk, Claroty and InsightVM are not available here: write "could not
  be assessed: connector not available in this runtime" in scoping, still write the CQL
  and SPL queries with CONTROL and BASELINE, and keep every query rule from the skill.
  Save as `hunts/packages/TH26-NN-Title_Case_Slug.docx`.
  Builder: `python3 core/.claude/skills/genelabs-threat-hunt-package/scripts/build_hunt.py <spec.json> <out.docx>`.
- **cve_brief** (`CVE-VM-YYYY-MM-DD`):
  `python3 core/tools/build_priority_brief.py registers/CVE_Register_2026.xlsx registers/CVE-VM-YYYY-MM-DD.docx core/.claude/skills/genelabs-cti-bulletin`
  If the builder rejects the register, fix the register cell it names and rerun.
- **awareness** (`AWR-YYYY-MM-DD`): the `genelabs-employee-awareness-blog` skill with the
  topic named in today's report, `--channel` set, ledger row appended, then rebuild
  `state/awareness-topic-pipeline.md` (STEP 11 of the scan prompt).

## Rules

- The branded templates are not shipped; the builders fall back to an unbranded document.
  That is expected. Say so once.
- Spec JSON and scratch scripts go under `state/_work/`, never the output root.
- The filename must contain the ID exactly as given. Do not renumber, do not invent new
  IDs, do not touch entries in the dedup log other than to correct a filename.
- Build every item in the batch. If one builder call fails, fix the spec and retry; only
  when it cannot be built at all, write `state/_work/<ID>.failed.md` saying why.
- Finish with one line per item: ID, path written, or the reason it failed.
