---
name: "genelabs-detection-handoff"
description: "Produce an GeneLabs CTI Detection Hand-off .docx, report id CTI-DET-AssetSlug — the document sent to Security Monitoring and Detection Engineering when a finding yields detection logic worth building. PSEUDO-DETECTIONS ONLY: the behaviour with a contrast picture, the logs and fields needed, the discriminator that separates it from normal with the measurement behind it, known false positives, and what CTI observed when it tested the concept. No exact queries — the analyst writes the search their own way. Includes a \"cannot build yet\" section naming the TG-NN gap blocking each missing detection and what becomes detectable once it closes. Use when handing detections to the SOC, when an exposure advisory or hunt yields reusable detection logic, or when asked what the monitoring team should build. Contains no exposure narrative, risk or severity — for that use genelabs-exposure-advisory."
---

# GeneLabs CTI Detection Hand-off

The document CTI sends to **Security Monitoring / Detection Engineering** when a finding
yields detection logic worth building. Report id `CTI-DET-AssetSlug`.

## Two rules define this document

### 1. No exposure narrative

April, 2026-08-27: *"When sending findings to the monitoring/detection team, the report
should focus on two things: detection recommendations and validation steps — not the
exposure narrative itself."*

No risk assessment, no impact argument, no severity, no business consequence. One paragraph
of context pointing at the advisory, then detections.

### 2. PSEUDO-DETECTIONS, NOT QUERIES

April, 2026-08-27: *"use pseudo detections instead — what logs needed, behavior, dont give
exact detections, allow the analyst to create the search the way they want. Just say whats
needed."*

This is better detection engineering than shipping SPL, and the reasons are worth stating
so nobody helpfully adds the queries back:

- **The SOC owns the search language**, the macros, the allowlists, the naming and the
  tuning conventions. A pasted query arrives with none of that and is either rewritten or
  deployed badly.
- **A query is an answer to a question nobody asked them.** Handing over the behaviour and
  the discriminator lets an engineer choose the cheapest correct implementation in their own
  environment — which may be a different data source entirely.
- **A query goes stale the moment a field is renamed.** A behaviour does not.

**Dropping the query does NOT mean dropping the evidence.** A recommendation nobody has
tested is a guess whether or not it ships as code. CTI runs the concept, records the
numbers, and hands over the numbers — the thresholds are the most valuable thing in the
document and they are worthless unmeasured. The builder refuses to ship a detection with no
`observed` field.

| Artifact | Skill |
| --- | --- |
| The exposure itself, for the asset owner | `genelabs-exposure-advisory` |
| **Detections, for the SOC** | **this skill** |
| Hunt plans | `genelabs-threat-hunt-package` |

## Why it is separate from the advisory — lifecycle, not audience

**An advisory closes when the asset is fixed. A detection outlives it.** On 2026-08-27 a
detection written fleet wide immediately found seven scanning sources with nothing to do
with the asset in the advisory. Bury that in an asset document and it gets closed when the
asset owner closes the asset.

## Where things live

| Item | Path |
| --- | --- |
| Builder | `CTI Deliverables\_tools\build_detection_handoff.py` |
| Behaviour diagrams | `CTI Deliverables\_tools\behaviour_diagram.py` |
| Output | `CTI Deliverables\Exposure Advisories\Detection Hand-offs\YYYY-MM-DD-Asset-Detection-Handoff.docx` |

## Structure

1. **Why you are receiving this** — one short paragraph, plus one saying every number was
   measured before it was written down. Point at the advisory for the story.
2. **What we are asking you to detect** — one block per behaviour.
3. **Detections we cannot build yet, and what unblocks them.**
4. **Validation steps before you deploy.**

### Each detection block

| Field | Carries |
| --- | --- |
| `name` | The behaviour, in behavioural terms |
| `figure` | A behaviour diagram — see below |
| `behaviour` | What the adversary did and why it looks the way it does. Two or three sentences |
| `logs_needed` | A list: which data sources, which FIELDS, and how to bucket. Name both the data model and the raw index |
| `discriminator` | What separates it from normal, **with the measurement behind it** |
| `false_positives` | What will fire that should not, and how to tune it correctly |
| `observed` | **Mandatory.** What happened when CTI tested the concept |

**Prefer fleet-wide to asset-scoped.** A detection written for one host protects one host.

**Derive thresholds from measured data and show the working.** "500 distinct paths per hour"
means nothing alone; "the confirmed scanners ran 3,058 to 4,981 against a background tail of
223 to 418, so it sits in a gap rather than on a slope" tells an engineer whether to trust it
in their environment. Always state the expected alert volume — that is what decides whether
it is deployed or muted. **Tell them to re-derive it in their own data**, and what to do if
your numbers do not reproduce.

**Tune by exclusion, not by raising the number.** Raising a threshold to silence one crawler
also silences the attacker sitting one order of magnitude above the noise.

**Name both the data model and the raw index in `logs_needed`.** A data model is a mapping
over the data, not the data. On 2026-08-27 a detection was recorded as impossible because a
CIM field rendered as the literal string "unknown"; the raw index carried the field all
along.

### Behaviour diagrams

`behaviour_diagram.py`. **Every diagram is a CONTRAST — normal beside the behaviour, drawn
to the same scale.** A detection engineer's real problem is never "what does bad look like",
it is "what does bad look like THAT GOOD DOES NOT". A picture of only the malicious case
invites a detection that fires on everything, which then gets muted, which is worse than no
detection.

The existing set: path fan-out (one source, many distinct paths, against a normal client
asking for a few repeatedly) · out of band callback (the target is told to phone a stranger)
· enforcement gap (we hold the intelligence and permit the traffic anyway) · outcome missing
(we record the question and not the answer). Add a scene as a function and register it in
`SCENES`.

### The blocked section is the point of the document

Name it, name the `TG-NN` gap, say in plain terms what capability is lost, and list **what
becomes detectable once the gap closes** — as capabilities, not queries.

This is what turns a gap register row into something somebody will fund. A register entry
says "response status is not retained". This section says "today we can tell you that you
were scanned and we can never tell you whether it worked — that is the difference between an
alert that starts an investigation and one that ends it".

### Validation steps are for the SOC to prove it themselves

Steps the receiving team performs in **their** search head: reproduce the threshold and look
for the discontinuity; check the alert volume matches; deliberately run the noisy variant
once to see the false positive population; confirm any lookup a detection depends on exists.
Include at least one step saying **what to do if CTI's numbers do not reproduce** — a search
head scoped differently is the likeliest reason a good detection is discarded on day one.

## The false positive trap this series exists to remember

At a genomics company, security tool names collide with laboratory vocabulary. A pattern
matching a scanner's name as a loose substring returned a fintech domain, a biotech domain, a
SharePoint deck named for a nuclei repeat assay, and an SAP search for "nuclei extraction".
**"Nuclei" is a laboratory word at GeneLabs before it is a security tool.**

Match the specific artefact, never the bare product name, and say in `false_positives` what
the wide version returns so nobody widens it later. The same class of error has produced
false readings on `UniFi` (chromatography software), `fastlink` (a bank hostname) and
`qtproxycall` (a scanner's own parameter).

## Build

```
python build_detection_handoff.py spec.json out.docx <bulletin skill dir> <figdir>
```

Exits non-zero listing any detection with no `observed` field. Needs `python-docx` and
`Pillow`.

## JSON spec

```json
{
  "report_id": "CTI-DET-PKIW02",
  "tlp": "AMBER+STRICT",
  "title": "Detecting the behaviour, in behavioural terms",
  "subtitle": "Written from CTI-EXP-PKIW02. N behaviours, M blocked. Concepts tested against 14 days of live data.",
  "doc_control": [["Prepared By","Cyber Threat Intelligence"], ["For","Security Monitoring / Detection Engineering"],
                  ["Source finding","CTI-EXP-PKIW02"],
                  ["Format","Pseudo-detections — behaviour and data needed. Build the searches your own way."]],
  "context": ["What was found; the exposure is handled elsewhere.",
              "This is not search code. You own the language. Where a number appears, CTI measured it."],
  "detections": [{"name": "...", "figure": "beh_fanout", "behaviour": "...",
                  "logs_needed": ["...", "..."], "discriminator": "... MEASURED: ...",
                  "false_positives": "...", "observed": "Tested over 14 days: ..."}],
  "blocked": [{"name": "...", "gap": "GAP-25", "figure": "beh_outcome",
               "detail": ["...", "..."], "unblocks": ["...", "..."]}],
  "validation_steps": ["...", "..."],
  "contact": "secops@genelabs.com  |  Cyber Threat Intelligence"
}
```

## Length

Page count is not the constraint. This is a working document for engineers, not stakeholder
distribution. The test is whether every line is something the receiving team acts on.

## Branding

GeneLabs orange `#FF7109` / `#E05F00` for section rules and headings, Abbey `#444648` body,
corporate grey `#676765` meta, `#F4F4F4` label cells, `#D9D9D9` borders, Arial throughout. A
`observed` result renders in green `#2E7D32`; a blocked detection's gap reference in red
`#C62828`. Footer carries the wordmark, TLP with the value as a separate run, the marking
`CTI Detection Hand-off`, `DOC #` and live `Page X of Y` under an orange rule.

