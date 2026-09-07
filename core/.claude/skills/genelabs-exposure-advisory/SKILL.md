---
name: "genelabs-exposure-advisory"
description: "Produce an GeneLabs-branded CTI Exposure Advisory as a .docx — written when a hunt, an external scan or a connector lookup finds an GeneLabs asset reachable from somewhere it should not be. A ONE PAGE main body of roughly 220 words: summary, a two-sentence Why We Care opener, three bullets, one owned action table. NO FIGURES. Appendix A starts on its own page and carries the reasoning as a Step/Status table, severity as a table, a numbered reproduction walkthrough, and what the advisory does not settle. Use for internet exposed services, open management ports, exposed cloud storage, shadow or unmanaged internet facing assets, accidentally public endpoints, or any Shodan or Censys attack surface finding needing an owner and a fix. Where the finding yields detection logic, issue genelabs-detection-handoff to the SOC as a separate document. For a threat bulletin use genelabs-cti-bulletin; for a hunt use genelabs-threat-hunt-package."
---

# GeneLabs CTI Exposure Advisory Builder

## What this artifact is

*This asset of ours is reachable from somewhere it should not be, here is who closes it,
here is the proof.*

Not an incident report — nothing has necessarily happened. Not a vulnerability alert — the
asset may be fully patched and still wrong. The finding is the reachability itself.

| Artifact | Skill |
| --- | --- |
| Threat and vulnerability bulletins | `genelabs-cti-bulletin` |
| Hunt plans / completed hunts | `genelabs-threat-hunt-package` / `-report` |
| CVE priority briefs | `genelabs-cve-priority-brief` |
| **Detections for the SOC** | **`genelabs-detection-handoff`** |
| **Exposure advisories** | **this skill** |

## Two documents, and the reason is LIFECYCLE not audience

April considered combining this with the detection hand-off and decided against it on
2026-08-27. Keep the reason, because "different audiences" alone is a weak argument that
invites re-litigation:

**An advisory closes when the asset is fixed. A detection outlives it.** A detection gets
tuned, versioned and redeployed for years after the finding that prompted it. On
2026-08-27 the scanner detection written fleet-wide immediately found seven scanning
sources with nothing to do with the asset in the advisory.

Reference the hand-off from the Why We Care callout and the action table. Do not embed it.

## OPEN QUESTION — who receives this

**April is not yet sure of the distribution.** Until she is, page one is written for the
NAMED ASSET OWNER: the functions in the action table. Do not add a severity verdict to page
one to serve a leadership reader, and do not strip internal detail for a wide circulation
list, until the audience is settled. **Raise this when it next comes up rather than
guessing** — it changes what page one is for.

On 2026-09-01 this stopped being theoretical: a finding on a platform with named external
customers, including two US state health departments, had a regulatory dimension that the
named asset owners are not the right readers for. Record it in A.8 and raise it; do not
solve it by quietly widening the tone.

## THE ONE PAGE RULE, AND THE WORD BUDGET

**The main body is ONE PAGE. Everything else is Appendix A, which starts on its own page.**

April, 2026-08-27: *"Current reports are too long and repetitive; the group agreed a concise
one-pager is the better format for stakeholder distribution."*

April, 2026-09-01: *"make it way less words, super direct and concise. Leave the appendix as
is, or add more to it to keep the main content concise and direct."*

**Page one has a word budget: about 220 words** across the summary, the Why We Care opener,
the three bullets and the action Detail column. The 1 September advisory ran 564 words before
this rule and 225 after, with no loss of fact — everything cut moved into the appendix. If
you are over budget, the content is not wrong, it is in the wrong section.

Sentence discipline that gets you there:

- The summary is **four sentences**: what the asset is, what is wrong with it, who else is
  affected, and the one thing you could not establish. Then point at A.1.
- The Why We Care opener is **two sentences** (see below).
- Each Why We Care bullet is a **bolded lead-in plus ONE short sentence**. Not three.
- Each action Detail cell is **one short sentence**, ideally under fifteen words.
- Never explain a caveat on page one. State the fact and let the appendix carry the caveat.

### Six things were removed and none should be reinstated

| Removed | Why |
| --- | --- |
| **The Risk table** | By instruction, 27 Aug. Its argument lives at A.6. |
| **Bottom Line** | By instruction, 27 Aug. It restated the summary in different words. |
| **The Severity row** | By instruction, 27 Aug. The verdict is off page one entirely; it lives at A.6. |
| **Technical Detail** | By instruction, 27 Aug. A.1 carries the external record verbatim. The two facts a stakeholder needs moved into the summary. This was the cut that made one page work. |
| **ALL FIGURES** | By instruction, 1 Sep. See below. |
| **Long-form page one** | By instruction, 1 Sep. See the word budget above. |

### Page one, in order

1. **Document control** — five rows: Prepared By, Date, Affected Asset, Source, Document
   Owner Function. One line each. No Severity row.
2. **Summary callout** — four sentences, per the budget above.
3. **Why We Care** — a **two-sentence opening paragraph, THEN three bullets**, then a short
   callout naming the detection hand-off.
4. **What Needs To Be Done** — ONE Action / Owner / Detail table, four or five rows, one
   sentence each, every row owned by a function.

### The Why We Care opener — added 2026-09-01

April: *"give a one-two sentence summary about what is going on under why we care before
going into bullet points."*

Two sentences, in the section's `intro` key so it renders above the bullets. It exists
because three bolded bullets land as three separate facts and the reader has to assemble the
situation themselves. The opener assembles it for them, and the bullets then unpack it.

**Write it as the situation, not as a repeat of the summary.** The summary is addressed to
someone deciding whether to read on; this is addressed to someone who already has. The 1
September example ended on the line the bullets could not carry on their own: *"Nothing
suggests it has been attacked, but nothing would show us if it had."*

If the opener could be deleted without the bullets becoming harder to read, it is a
restatement and should be cut.

### When it will not fit

**Remove a section. Do not shave words.** Learned expensively: one advisory took eight
builds for two pages and five more for one, because prose was trimmed repeatedly before a
structural cut was made. In order:

1. Cut a Why We Care bullet whose content already appears in an action row.
2. Merge action rows sharing an owner — two questions for one team are one conversation.
3. Move argument into A.6 or A.8.
4. Cap the action table at five rows and carry the remainder to A.8, stating they are NOT
   cancelled.

## NO FIGURES — April, 2026-09-01

**The chain-of-reasoning diagram, its legend and the severity figure are all removed.** A
`__FIG:` sentinel is no longer written into the spec and `insert_figures.py` is no longer
run. This mirrors the same instruction given for `genelabs-detection-handoff` on 27 August.

**The information the diagram carried must not be lost with it.** Colour was doing real work
— it encoded how each step was known — so that encoding moves into a Status COLUMN in words.
This is the trade the rest of this section describes, and it is why A.0 is now a table rather
than a paragraph.

Do not reintroduce a figure because a particular finding "would be clearer as a picture".
That argument was made and settled.

## Appendix A — starts on its own page, designed to be SCANNED

April, 2026-09-01: *"make the appendix start on its own page."*

A hard page break goes before the Appendix A heading. Do it as a post-pass with
`CTI Deliverables\_tools\page_break_before.py`, not by editing the plugin-managed builder,
and not with an empty spacer paragraph — a spacer satisfies a visual check and then collapses
differently depending on the heading's space-before.

**Why it matters beyond tidiness.** The one-page rule is about what a stakeholder receives,
and a page one trailing two appendix headings under the action table reads as a document that
ran over. The break makes the contract visible: page one is the whole main body, everything
after it is reference the reader opens on demand.

April, 2026-08-27: *"We need to know your reasoning but it's a lot of words, maybe a flow
chart using pictures?"* The instinct behind that survives the removal of the pictures:
reviewers do not read an argument end to end, they look for the step they doubt. A table is
scannable the same way a diagram was, and it survives being pasted into an email.

| Subsection | Carries |
| --- | --- |
| **A.0  The argument, step by step** | The reasoning as a three-column table. **First, before any prose.** |
| A.1  External view | The full scanner record and RAW banners, quoted not paraphrased |
| A.2  Perimeter traffic | Allowed and blocked counts, with how to READ them |
| A.3  The legitimate baseline | Per-source attribution WITH the benign baseline, and why it comes first |
| A.4  How this was discovered | Method, and the caveat that stops the trigger being over-read |
| A.5  Visibility gaps | What cannot be seen, cited to `TG-NN` |
| **A.6  Severity** | A Component / Reading / Basis table plus two short paragraphs |
| **A.7  Reproduce this yourself** | The numbered analyst walkthrough, generated by the citation pass |
| **A.8  What this advisory does not settle** | Open questions, un-run checks, deferred actions, distribution, and the issue note |

### A.0 — the argument as a table

Three columns: **Step · Status · What it establishes**. Status is one of four values, in
capitals, and this is where the diagram's colour coding now lives:

| Status | Means |
| --- | --- |
| `MEASURED` | a query produced this number |
| `INFERRED` | a judgement drawn from measured facts |
| `RULED OUT` | a reading that was tested and DISPROVED |
| `OPEN` | the question that would change the conclusion |

**The RULED OUT rows are the point.** An argument showing only what it concluded reads as
advocacy; one showing what it tested and rejected reads as analysis. Expect three or more.
Write each RULED OUT row as the claim that was disproved, not as its negation — "The host is
not GeneLabs's / RULED OUT" is readable; "The host is GeneLabs's / CONFIRMED" is the same
fact with the falsification hidden.

Order the rows as the reasoning ran. Put the OPEN row last, because it is what the actions
turn on. Open with one short paragraph telling the reader to read the Status column first.

### A.6 — severity as a table

A Component / Reading / Basis table, then **two short paragraphs and no more**. The first
version of A.6 justified the verdict in six paragraphs, which was the content removed from
page one, made longer, and put where fewer people look.

Rows: the components that drive it, each with its basis; the exploitation line; and two
conditional rows, "Raises to HIGH if" and "Falls to MEDIUM if", both status OPEN. Severity
that can only go one way is a verdict pretending to be an assessment.

**Where no telemetry exists, list exploitation as RULED OUT AS EVIDENCE** and say in the
prose that its absence is an absence of visibility. "None observed" in a document that also
says nothing could have been observed is the single most misleading line an advisory can
carry.

The two paragraphs are: what the exploitation line does and does not mean, and the sector
base rate, which is what stops a single finding being over-read.

### A.7 — the reproduction walkthrough

April, 2026-08-27: *"For validation there needs to be a step-by-step guide for an analyst
to reproduce themselves to come to the same findings."*

A.7 is generated by the citation pass from `evidence_appendix`, so each entry is written
**as a numbered step**, in the order an analyst should run them, not as a lookup table:

```
"ref":       "E3"
"claim":     "STEP 5 — Measure the scanning itself."
"reasoning": "<what to run>. EXPECT: <the specific numbers>.
              ESTABLISHES <what follows>. DOES NOT ESTABLISH <the limit>."
```

Note the key is `ref`, not `id`. An `id` key produces
`FATAL: markers cite undefined evidence refs`.

**Rules that make the walkthrough worth following:**

- **Order steps by what an analyst should do, not by where the claim appears.** Run the
  legitimate baseline BEFORE the suspicious traffic — an analyst who reaches the scan
  evidence first tends to conclude the service should not be public, which may be wrong.
- **Run the CONTROL last within its own step**, and say why: two zeros are meaningless until
  the control proves the source returns data at all.
- **Give expected values, not just queries.** "EXPECT roughly 194,854 across six paths" lets
  someone know immediately whether they have reproduced it.
- **Every step states what it does NOT establish.** This is the difference between a
  walkthrough and a demonstration.
- **Include the falsification steps.** "Try to falsify the alarming reading before you
  accept it" is a step, and it earns the document its credibility.
- **Include the step that found the finding.** How it surfaced is often the finding behind
  the finding.
- Where the original did not record a query, SAY SO rather than inventing one.

### A.8 — what this advisory does not settle

Added 2026-09-01, and it is what makes a 225-word page one honest. Everything the old page
one hedged about now lives here as a bulleted list: open questions, checks that were not
run, deferred actions with owners (stating they are NOT cancelled), the distribution
question, and a one-line issue note when the advisory is reissued.

**A page one that is short because it dropped its caveats is worse than a long one. A.8 is
the price of the word budget, and it must be paid.**

## Evidence citations

**Every claim carries a superscript into A.7.** A claim with no citation is unsupported and
must be cited or cut. Set `evidence_appendix_title` to `"Appendix A.7 — Reproduce this
yourself: an analyst walkthrough"`.

**Watch for orphaned entries.** Shortening page one is exactly what orphans a ref: the pass
reports unused entries, and on 1 September the falsification entry E5 was orphaned by the
rewrite. Re-cite it where the claim genuinely sits — usually the A.0 RULED OUT row and the
A.1 paragraph making the same point — rather than cutting it. A falsification step you stop
citing is the one you most need.

## Build

```
python scripts/build_exposure_advisory.py spec.json out.docx
python3 "<PACKAGES>\_tools\apply_inline_bold.py" out.docx
python3 "CTI Deliverables\_tools\page_break_before.py" out.docx "Appendix A"
python3 "<PACKAGES>\_tools\apply_evidence_citations.py" out.docx spec.json   (ALWAYS LAST)
```

**`insert_figures.py` is no longer part of the sequence.** There are no figures.

`page_break_before.py` goes before the citation pass and matches the heading
whitespace-insensitively, because headings render letterspaced. It takes the FIRST match as
the heading and leaves later ones alone — "Appendix A.7" in the citation appendix is a
different heading, and any "see A.1" in prose is a cross-reference. It is idempotent.

The builder's `check()` still encodes the pre-27-August house order and will emit
`warning: missing house section 'Technical Detail'` and `'Bottom Line'` on every correct
build. **Those warnings are wrong, not the document.** Filter them out of build logs so they
do not train the operator to ignore all warnings.

## Where the output goes

`CTI Deliverables\Exposure Advisories\<YYYY-MM-DD>-<Asset>-<Topic>-Explainer.docx`, doc id
`CTI-EXP-<AssetSlug>`. Flat folder. **List it first** — if an advisory exists for that asset,
update in place and bump the issue note in A.8. One asset, one advisory, one file.

## The standing rule that generates these

**If you find an exposure outside the original scope of whatever you were searching for,
always raise an advisory.** On 2026-08-27 a query hunting threat actor infrastructure
returned an GeneLabs host purely because a scanner's parameter was named `qtproxycall`;
reading that row rather than counting it surfaced four complete vulnerability scans no
control had caught. The same query matched a bank hostname on a substring — so read the
hits, confirm the asset is genuinely ours and genuinely exposed, then write it.

On 2026-09-01 the same rule produced a second finding from a routine daily sweep, and the
lesson repeated in a different form: **the count delta was not the finding.** The scan total
moved 2,528 to 2,622, but on the previous run the total had stood still on a day that had a
real finding in it. A NAMED HOST is a finding; a number is not. Say this in A.4 every time,
because the next reader will assume the delta triggered it.

Where the finding **corrects an existing deliverable**, say so.

## Writing standard

- **No analogy, no metaphor.** Name the service and what an attacker obtains by reaching it.
- **State risk in security terms**, not "someone could get in".
- **No hyphenated compound modifiers.** Real identifiers keep their hyphens.
- **Separate observation from inference.** "No compromise has been observed" is supportable;
  "the host is clean" is not.
- **Do not soften or inflate severity.** No observed abuse is HIGH, not CRITICAL.
- **Lead with what is legitimate where it is legitimate.** If the exposed service is
  correctly public, say so first and use it to sharpen the finding. An advisory that appears
  to attack a correct design gets argued with instead of actioned.
- **Never quote a scanner's CVE count as a finding.** Shodan's `vulns` array is CPE-inferred
  from a version banner and cloud vendors backport without advancing it. The honest statement
  is "an unsupported branch", not "forty-nine vulnerabilities". Put the count in A.1 as a
  lead and falsify it in A.7.
- Name owner functions, never individuals.

## Verify — and four traps that produce WRONG answers

- **Headings render LETTERSPACED**: "Bottom Line" extracts as `B o t t o m  L i n e`. Match
  whitespace-insensitively, always.
- **The A.7 heading is NOT a styled heading.** The citation pass emits it as a `Normal`
  paragraph, letterspaced. A check that looks for `A.7` among styled headings, or as a raw
  substring, reports it missing on a correct document. This has now produced a false failure
  twice. Normalise whitespace and search the full body text.
- **A cross-reference is not a heading.** "Full record in A.1" in the summary made a
  correctly ordered appendix report as out of order — a FALSE PASS, the dangerous direction.
  **Assert order over styled HEADINGS, never raw text position.** Equally, a cross-reference
  such as "see A.7 STEP 4" in A.1 inflates a naive count of walkthrough steps; count only
  `STEP n` followed by a dash.
- **"Appendix A" appears more than once.** `Appendix A - Evidence and Reasoning` is the
  section; `Appendix A.7 — Reproduce this yourself` is the walkthrough. A page-placement
  assertion must match the FULL section heading, or A.7 will satisfy it from a later page.
- **The footer is not page content.** Slicing page 2's first lines catches `Page 2 of 8` and
  the TLP line, which made a correct one-pager report as a failure.

Assert: **no images embedded at all** · no `__FIG:` sentinel left visible · **no body section
heading on page 2 or later**, proven by extracting per-page PDF text · **the full Appendix A
heading is ABSENT from page one and PRESENT on page two** · opens on Why We Care · the Why We
Care opener renders above the first bullet · no `The Risk`, no `Bottom Line`, no
`Technical Detail`, no Severity row in document control · doc control is exactly the five
house rows · A.0 carrying a three-column Step/Status table with at least three RULED OUT rows
and one OPEN · A.6 carrying a Component/Reading/Basis table · A.7 present with every step
numbered and each stating what it does not establish · A.8 present · exactly ONE owned action
table of four or five rows · no unconsumed `**` or `{{E` · every evidence ref cited, none
reported unused · page one within the word budget.

**RULE CHANGED 2026-09-01 — do not reinstate the old one.** Until the page break was added,
this file said *"do NOT assert that page two begins with Appendix A"*, because a correctly
short page one left room for A.0 to begin on page one and the assertion produced a false
failure. **That is now inverted:** the appendix starts on its own page by instruction, so
page two beginning with Appendix A is the correct state and must be asserted. If you find
A.0 on page one, the page break did not apply.

Then **render page one to PNG and look at it.**

## Branding

GeneLabs orange `#FF7109` (`#E05F00` small headings), Abbey `#444648` body, corporate grey
`#676765` meta, `#FFF4E8` callouts, `#F4F4F4` label columns, `#D9D9D9` borders at 0.75pt,
Arial throughout. Do not darken the rules for dark mode — Word keeps an explicit light
border light, and a mid grey disappears.

