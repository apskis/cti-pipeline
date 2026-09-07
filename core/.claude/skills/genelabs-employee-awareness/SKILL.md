---
name: "genelabs-employee-awareness"
description: "Produce the GeneLabs all-employee security awareness post as a branded .docx for Viva Engage — the AWR-YYYY-MM-DD series written for every employee rather than for the security team. Plain language, directive close, TLP:CLEAR, and a hard sanitisation gate that strips every internal detail. Enforces a topic ledger so the same awareness message is never posted twice unless the attacker's tactics have materially changed. Use for the daily employee post, a security-awareness message, an all-staff phishing or vishing warning, or anything intended to be read by the whole company. For an analytical bulletin aimed at the security team use genelabs-cti-bulletin instead."
---

# GeneLabs Employee Awareness Post

The **AWR-YYYY-MM-DD** series: one short, branded `.docx` per weekday that April posts to Viva
Engage and attaches for the whole company to read.

> **This is not a CTI bulletin with simpler words.** It has a different reader, a different
> disclosure level and a different close. An analytical bulletin asks the security team questions;
> this tells an employee what to do. Everything else this programme produces is TLP:AMBER+STRICT;
> this is TLP:CLEAR and must be *written* to be safe at CLEAR, because a Viva Engage post has no
> access control and is trivially screenshotted.

## Where things live

| Item | Path |
| --- | --- |
| Builder | `CTI Deliverables\_tools\build_awareness.py` |
| Sanitisation gate | `CTI Deliverables\_tools\verify_awareness.py` |
| Topic ledger | `CTI Deliverables\CTI Bulletins\2026\Employee Awareness\_awareness_topic_log.md` |
| Output | `CTI Deliverables\CTI Bulletins\2026\Employee Awareness\AWR-YYYY-MM-DD-Title_Case_Slug.docx` |
| Branding source | the `genelabs-cti-bulletin` skill directory |

The builder and gate live in the workspace, not in this skill directory, because a saved skill
stores only `SKILL.md` — its directory is a read-only cache. If either script is lost, this file
specifies both completely enough to rebuild.

## Identity and format

- **Report ID `AWR-YYYY-MM-DD`**, date-based on purpose. A daily post must never consume the
  `CTIYY-NN` series: it would burn ~250 report IDs a year and break the "highest CTIYY-NN gives the
  next report ID" rule within weeks.
- **Filename** `AWR-YYYY-MM-DD-Title_Case_Slug.docx`, every slug word capitalised, spaces to
  underscores.
- **Its own folder**, `Employee Awareness`, separate from the analytical set April files into
  `Published` and `Unpublished`.
- **Category** `AWARENESS BULLETIN`. **`tlp` must be `CLEAR`** — the builder refuses to run otherwise.
- **Two pages is fine.** April attaches the document rather than pasting it, so readability beats
  brevity. Do not gut the substance to hit one page.

## THE SANITISATION RULE — the thing that matters most

Nothing internal may reach this document. **Never include:**

- internal hostnames, or any `*.genelabs.com` name
- IP addresses
- hunt IDs (`THYY-NN`), bulletin IDs (`CTIYY-NN`), CVE numbers, peer register IDs
- the names of our security tools or platforms
- MITRE technique IDs, query language, data model names
- any statement about what GeneLabs does or does not monitor, detect, license or cover
- any control gap, however phrased

Write it so it would be harmless if it appeared on the public internet tomorrow, because it might.

**Disclosure level (April, 2026-08-25):** you MAY say *"our threat intelligence team is tracking
this"*, or that the team is watching for something. You may NOT say what we run, what we can see,
or what we found. **Reassurance yes, posture no.**

## THE REPETITION RULE — read the ledger before choosing a topic

Nothing kills an awareness programme faster than the same post every week. Employees learn to
scroll past, and then the one that matters gets scrolled past too.

**A topic may not repeat within 90 days unless its tactic fingerprint has materially changed.**
If it has, the new post must be **framed as what changed** — it opens on the difference, not on the
original explanation — and must carry a different title.

**Materially changed** means at least one of: the delivery channel changed; the lure or pretext
changed; the credential-capture mechanism changed; the target population changed; a control that
used to stop it stopped working, or a new one started; or there is now a confirmed case at GeneLabs
where before there was none.

**Not material — do not re-post:** the same campaign named by a new outlet; a new victim
organisation with the same tradecraft; a bigger number on the same story; a vendor report restating
what employees were already told.

Every post appends a ledger row: date, AWR ID, `topic_key`, tactic fingerprint, source dedup key,
notes. The gate reads that ledger and **fails closed** on a same-topic same-fingerprint repeat.

**Fallback rotation** when the day's scan offers nothing employee-relevant: password reuse ·
unexpected MFA prompts · travel and public networks · handling research and patient data ·
tailgating and device security · how and when to report. Take the **least recently used** topic from
the ledger, so the fallback does not itself become repetitive. Say in the run output that you fell
back and why. Never manufacture urgency to fill the slot.

## Voice

- Written for someone with no technical background. No jargon, no acronyms the reader must look up,
  no abbreviations glossary.
- **Put the action in the title.** The title alone should be useful to someone who reads nothing
  else — "If Someone Phones You Claiming to Be IT, Hang Up and Call Back", not "Vishing Campaign
  Advisory".
- Keep sentences under ~45 words; the gate flags longer ones.
- Say plainly when there is nothing to install and no patch — most of these attacks work on people,
  and pretending there is a technical fix teaches the wrong lesson.
- **Always include:** that reporting is never a waste of anyone's time, and that nobody is in
  trouble for reporting. Under-reporting is the real failure mode, and fear of looking foolish is
  what causes it.
- Where a real victim was fooled despite knowing better, say so kindly and without mockery. It is
  the most persuasive thing in the document and it must not read as blame.

## Close with instructions, not questions

Use `recommended_actions`, **not** `questions`. The bulletin skill makes `questions` the default;
this series is the documented exception, because employees need to be told what to do rather than
asked audit questions they cannot answer.

Pass it as `[{"audience": "All employees", "items": [...]}]`. **The flat list-of-strings form raises
`AttributeError` inside the bulletin builder** — the builder here refuses that shape up front with a
clear message rather than letting it crash mid-build.

## Severity

Mirror the parent analytical bulletin where one exists, so the same threat never carries two
different severities across two documents. Do not explain the taxonomy to employees.

## Sources

2-3 public sources maximum, real URLs only. **Never cite connector-derived intelligence here** — it
is internal by definition. Never invent a URL.

## Build

```
python "CTI Deliverables/_tools/build_awareness.py" spec.json out.docx <genelabs-cti-bulletin skill dir>
```

The builder wraps the plugin-managed bulletin builder rather than reimplementing it, so branding
cannot drift. **Never modify the `genelabs-cti-bulletin` skill — it is plugin-managed; import from
it.** It calls `build_bulletin.build(spec, template, out_path)`; that module has no `main()`.

It refuses to build if `tlp` is not `CLEAR`, if `report_id` is not `AWR-`, if `questions` is
present, or if `recommended_actions` is missing or the wrong shape.

Then it post-processes two house deviations for this series:

1. **The footer TLP value renders in house black `#444648`, regular weight, no italic** — not the
   orange italic severity colour. April, 2026-08-26: the orange read as an alert on a document whose
   whole purpose is to be calm and routine.
2. **The footer label reads "Employee Security Awareness"**, not "CTI Intelligence Bulletin".

Both edits target the run by its **text**, never by index — the bulletin builder may reorder footer
runs, and an index-based edit would silently recolour the wrong thing.

## Verify before delivering — the gate is not optional

```
python "CTI Deliverables/_tools/verify_awareness.py" out.docx \
    --topic-key <key> --fingerprint "<tactics>" \
    --ledger "<Employee Awareness>/_awareness_topic_log.md" --awr AWR-YYYY-MM-DD
```

Exit code 1 means do not deliver. It asserts:

- none of the banned patterns above appears anywhere in the document, including headers and footers
- the required employee instructions are present
- **the TLP marking is CLEAR in the FOOTER specifically**, and the TLP value is not orange
- the topic does not repeat inside 90 days with an unchanged fingerprint
- no sentence runs over 45 words

**Two bugs this gate has already caught in itself, both worth remembering:**

- The first TLP check searched the whole document for "CLEAR" and passed — not because the footer
  was right, but because the word "clear**est**" appeared in a red flag. When that word was edited
  out, the check failed and exposed itself. The footer had been correct all along; the *check* was
  wrong. **A verification that unrelated body text can satisfy is not a verification.**
- The text extractor read footer *paragraphs* but not footer *tables*, which is exactly where this
  builder puts the TLP marking.

Report the gate result in the run output.

## After publishing

Append the ledger row. Record the AWR ID against the source item in the CTI dedup log, so a later
run can see that item was already used for employee messaging.

## JSON spec

Same schema as `genelabs-cti-bulletin`, with these fixed for the series:

```json
{
  "report_id": "AWR-2026-08-25",
  "date": "August 25, 2026",
  "category": "AWARENESS BULLETIN",
  "severity": "MEDIUM",
  "title": "Action-first headline the reader can use on its own",
  "audience": "All GeneLabs Employees and Contractors",
  "relevance": "Plain-language why-this-matters. May say the CTI team is tracking it. No posture.",
  "detail_table": [["What is happening", "..."], ["What to do", "..."]],
  "why_this_matters": ["..."],
  "what_happened": ["..."],
  "red_flags_intro": "You do not need to spot all of these. Any one is enough to stop and verify:",
  "red_flags": ["..."],
  "recommended_actions": [{"audience": "All employees", "items": ["..."]}],
  "sources": [{"text": "Outlet: Headline (Month D, YYYY)", "url": "https://..."}],
  "footer_contact": "secops@genelabs.com  |  ServiceNow",
  "tlp": "CLEAR"
}
```

Omit `abbreviations` — if a term needs a glossary it does not belong in this document.

