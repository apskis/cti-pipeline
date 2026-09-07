---
name: genelabs-cti-bulletin
description: "Produce an GeneLabs-branded Cyber Threat Intelligence bulletin as a .docx, matching GeneLabs's Enterprise Information Security house template (banner, corporate palette, category tags, severity callout, wordmark footer, section layout). Use whenever drafting, formatting, or finalizing a CTI bulletin, threat bulletin, vulnerability alert, malware campaign, threat actor activity, supply chain alert, peer incident, awareness bulletin, or industry alert for GeneLabs, or when turning proposed bulletin ideas into a finished document."
---

# GeneLabs CTI Bulletin Builder

Generates a correctly branded GeneLabs CTI bulletin `.docx`. The banner (the
"Enterprise Information Security / Cyber Threat Intelligence" header) lives in
`assets/bulletin_template.docx` and is applied by cloning that template — never
rebuild the banner by hand. The GeneLabs corporate identity for the body and
footer is applied by `scripts/build_bulletin.py` — never restyle by hand either.

## When to use
Use this any time the deliverable is an GeneLabs CTI bulletin document, whether
starting from a proposed idea, from raw research, or reformatting existing text.
This is the canonical format for April's (CTI Lead) bulletins.

## Report ID and filename format — follow exactly

**Report ID: `CTIYY-NN`** — no hyphen between `CTI` and the year.
Correct: `CTI26-17`, `CTI26-20`, `CTI27-01`.
Wrong: `CTI-26-17`, `CTI-YY-NN`, `CTI2617`.

**Filename: `CTIYY-NN-Title_Case_Slug.docx`** — the report ID, then a hyphen,
then a descriptive slug in which every word starts with a capital letter and
spaces are replaced by underscores.

```
CTI26-17-TwinLoot_Microsoft_365_Command_And_Control.docx
CTI26-18-Medusa_Ransomware_Advisory_Update.docx
CTI26-19-AI_Coding_Agents_In_Intrusions.docx
```

Rules:
- Preserve the natural capitalisation of acronyms, product names and vendor
  names: `AI`, `DNA`, `RCE`, `SSO`, `M365`, `TwinLoot`, `CareCloud`, `GitLab`,
  `vCenter`. Do not flatten them to `Ai` or `Twinloot`.
- **Deprecated, do not produce:** `CTI-26-NN_Title` (hyphen before the year) and
  `CTI26NN_lowercaseslug` (no separator, run-on lowercase). Older bulletins on
  disk use these forms; leave them alone but never create new ones.
- Use the same `CTIYY-NN` string in the spec's `report_id`, so the document body
  and the `DOC #` footer field agree with the filename.

To find the next number, list the bulletin folder and take the highest `CTIYY-NN`
already present, including its `Published` and `Unpublished` subfolders.

## How to build

1. Gather the content for the bulletin. Confirm the facts and source dates before
   writing.
2. Choose the CATEGORY and SEVERITY from the taxonomy below. Be conservative on
   severity — `CRITICAL` means confirmed active targeting of GeneLabs, which is
   rare. If a bulletin sits between two levels, say which level you chose and why
   in the relevance callout, so the reasoning is visible rather than implied.
3. Write a JSON spec (schema below) and run:

   ```
   python scripts/build_bulletin.py spec.json output.docx assets/bulletin_template.docx
   ```

   In a Cowork session, resolve the template path relative to this skill folder.
   The wordmark asset is resolved automatically from `assets/`.
4. Deliver the resulting `.docx` to the user (SendUserFile), named per the
   filename format above.

If `python-docx` is missing, install it (`pip install python-docx
--break-system-packages`).

## Questions to Ask — the house close, use this by default

GeneLabs bulletins END WITH QUESTIONS, NOT INSTRUCTIONS. Use the `questions`
array. Do NOT use `recommended_actions` unless the user explicitly asks for a
directive bulletin — it is the legacy form and renders a "Recommended Actions"
section instead.

Questions land better than directives because the CTI team does not own the
remediation. A question forces the owning team to go and find out, and it
surfaces the answer to April rather than assuming she already knows it.

**A team is named ONCE, with all of its questions bulleted beneath it.** Never
repeat a team label down the section.

```
QUESTIONS TO ASK
SOC:
  ▪ Does hunt TH26-05 return any headless browser activity on a non-engineering endpoint?
  ▪ If Falcon comes back clean, do we treat that as negative or inconclusive?
Identity and Access Management:
  ▪ Which Entra application registrations were created in the last 30 days, and does each have a named owner?
  ▪ Do we baseline Microsoft Graph API call volume per principal today?
Leadership:
  ▪ Which of our current controls would have seen this, and what do we do about the ones that would not?
```

Where every team has exactly one question, the section renders inline instead,
one bullet per team — matching the published CareCloud bulletin:

```
QUESTIONS TO ASK
  ▪ Third Party Risk: Do any GeneLabs vendors or partners rely on CareCloud?
  ▪ Privacy: If any GeneLabs affiliated individuals are affected, what obligations follow?
```

### Grouping is built into the bundled builder

`scripts/build_bulletin.py` groups `questions` by team automatically: each team is
named once in first-appearance order with its questions bulleted beneath. Where
every team has exactly one question the section renders inline instead, one
bullet per team. Nothing to configure — just list a team's questions together in
the spec. Both the flat `[[team, question], ...]` pair form and the grouped
`[{"audience": ..., "items": [...]}, ...]` form are accepted.

The style decision is made once per section, not per team. That matters: if a
single-question team were rendered inline while others were stacked, its bullet
would sit under the previous team's list and read as if it belonged to that team.

### Writing them well
- **Aim for 8-11 questions across 4-6 teams.** List a team's questions together
  in the spec so they group cleanly.
- **A real question has an answer somebody has to go get.** "How many long-lived
  static AWS access keys exist today, and what is the oldest still active?" is a
  question. "Audit your access keys" is an instruction wearing a question mark.
- **Do not disguise an instruction.** "Have you patched CVE-X yet?" is a task with
  punctuation. Ask instead what the current remediation SLA is and how it compares
  with the observed exploitation window.
- **Order operational to strategic.** SOC, Vulnerability Management, IT and
  platform teams first; Third Party Risk, Privacy or Legal where relevant;
  Leadership last.
- **Leadership questions are about posture and policy, never tasks.** Good ones
  ask what a finding means for how GeneLabs decides things — thresholds, budgets,
  risk appetite, whether an assumption still holds.
- **Name the hunt package where one exists**, so the SOC question is answerable:
  "Does hunt TH26-05 return any …".
- Each question stands alone. A reader who only reads this section should still
  know what to go and do.

## Verify before delivering

Cheap checks that catch the failures that actually happen:

- No bracketed citation number exceeds the length of the `sources` list.
- The document ends with a "Questions to Ask" section, not "Recommended Actions"
  (unless a directive bulletin was explicitly requested).
- **No team label appears twice in the Questions section, and no bullet inside a
  team's list starts with a different team's name followed by a colon** — that is
  the signature of the unpatched flat renderer.
- Fonts resolve to Arial only, and the colour set matches
  `assets/example_branded_bulletin.docx` apart from the severity chip, which
  legitimately differs by level.
- The footer carries the wordmark image, the TLP marking, a `DOC #` field and
  `Page X of Y`.
- The section order matches the flow below.

## Section flow (follow this order)

Taken from the published house bulletins (CTI26-07, CTI26-14). The builder emits
it automatically; keep spec content in these buckets rather than reordering:

1. Report ID and date (right aligned)
2. Category tag
3. Title
4. Audience line
5. `Relevance to GeneLabs: <SEVERITY> — ...` callout
6. Threat detail table — sits directly under the callout with **no heading**
7. Why This Matters (bullets)
8. What Happened (narrative paragraphs)
9. Red Flags to Watch (optional lead-in sentence, then bullets)
10. **Questions to Ask** (grouped by team) — the house default close.
    `recommended_actions` renders a "Recommended Actions" section instead, for
    the rare directive bulletin.
11. Abbreviations (optional glossary)
12. Sources (hyperlinked)
13. Contact line

Use `abbreviations` for any acronym too long to expand where it sits — a term
like HHS OCR reads badly spelled out mid-sentence but has to be defined
somewhere. Give the term, the expansion, and a URL where an authoritative one
exists; in the glossary the term renders as that external link. Expand short
acronyms inline instead.

When `abbreviations` is present the builder wires up the cross-references by
itself, so do not hand-build them:

- The Abbreviations heading gets a `CTI_Abbreviations` bookmark.
- A small italic note goes under the relevance callout: "Acronyms used in this
  bulletin are defined under Abbreviations, page N", where Abbreviations is an
  internal link and N is a live `PAGEREF` field.
- The FIRST occurrence of each term anywhere in the body — including inside the
  detail table — becomes an internal link to that section. Later occurrences are
  left as plain text so the page does not fill with blue.

Word shows `PAGEREF` and page-number fields as `1` until they are refreshed:
Ctrl+A then F9 in Word updates them. LibreOffice resolves them on open.

## Citations and links

- Write inline citations in spec content as bracketed numbers: `... in the wild
  [1][3].` The builder removes the space in front of the group and renders it as
  superscript hard against the last character. Never hand-format superscript.
- Every source needs a real URL: give `sources` entries as
  `{"text": "Outlet: Headline (Month D, YYYY)", "url": "https://..."}`. A plain
  string still renders, unlinked — use that only when no public URL exists, and
  never invent one.
- Source list numbering stays at normal size; only in-text citations are
  superscript.
- The contact line links itself: an email becomes a `mailto:` link and
  `ServiceNow` links to the GeneLabs service portal.

## JSON spec schema

Required: `report_id`, `date`, `category`, `severity`, `title`, `relevance`,
`what_happened`, `sources`. Optional: `audience`, `supersedes`, `detail_table`,
`why_this_matters`, `red_flags_intro`, `red_flags`, `questions`,
`recommended_actions` (legacy), `abbreviations`, `footer_contact`, `tlp`.

```json
{
  "report_id": "CTI26-11",
  "date": "August 17, 2026",
  "category": "AWARENESS BULLETIN",
  "severity": "MEDIUM",
  "title": "Short, specific headline",
  "audience": "All Employees, IT Service Desk, SOC, Leadership",
  "supersedes": "CTI26-07",
  "relevance": "One to three sentences on why this matters to GeneLabs; name any affected product from the tech profile. Do not add the 'Relevance to GeneLabs: SEVERITY —' prefix; the script adds it.",
  "detail_table": [["Threat Actor", "..."], ["Technique", "..."], ["MITRE ATT&CK", "T1598.004, T1078"], ["Related Hunt", "TH26-05 (CrowdStrike CQL package)"]],
  "why_this_matters": ["Bullet with a cite [1].", "Bullet [2][3]."],
  "what_happened": ["Narrative paragraph with cites [1][2].", "Second paragraph."],
  "red_flags_intro": "The caller will sound calm, professional, and informed. Watch for these patterns:",
  "red_flags": ["What to watch for [1].", "..."],
  "questions": [
    ["SOC", "Does hunt TH26-05 return any headless browser activity on a non-engineering endpoint?"],
    ["SOC", "Keep a team's questions adjacent; the patched builder groups them under one label."],
    ["IT Service Desk", "Can a password reset, an MFA change and a new device enrollment all be completed during the same inbound call?"],
    ["Leadership", "What does this finding change about how we set the threshold, not what task we run?"]
  ],
  "abbreviations": [
    {"term": "HHS OCR", "definition": "Office for Civil Rights, U.S. Department of Health and Human Services.", "url": "https://ocrportal.hhs.gov/ocr/breach/breach_report.jsf"},
    {"term": "EHR", "definition": "Electronic health record."}
  ],
  "sources": [
    {"text": "BleepingComputer: Headline (August 17, 2026)", "url": "https://www.bleepingcomputer.com/..."},
    {"text": "CISA: Advisory title (August 17, 2026)", "url": "https://www.cisa.gov/..."}
  ],
  "footer_contact": "secops@genelabs.com  |  ServiceNow",
  "tlp": "AMBER+STRICT"
}
```

Bracketed citation numbers must match the order of the `sources` list. `tlp`
defaults to `AMBER+STRICT`. The footer copyright year is taken from `date`.

## GeneLabs corporate branding (applied by the script)

Do not override these in a spec; they are the house identity.

| Element | Value |
| --- | --- |
| Accent, section headings, rules | GeneLabs orange `#FF7109` (`#E05F00` for small heading text) |
| Body and headline text | Abbey `#444648` |
| Meta text, wordmark, sources | Corporate grey `#676765` |
| Relevance callout | Fill `#FFF4E8` with a solid orange left bar |
| Table label column | Fill `#F4F4F4`, `#D9D9D9` borders at 0.75pt |
| Typeface | Arial throughout (GeneLabs office standard; avoids font substitution on recipient machines) |

Page furniture, rebuilt in the footer on every page: the genelabs wordmark in
corporate grey (`assets/genelabs_wordmark_grey.png`), the TLP marking, the
copyright line, a `DOC #` field carrying the report ID, and live `Page X of Y`
fields, all beneath an orange rule.

Body layout: right-aligned report ID and date, category tag, title, small caps
audience line over a rule, relevance callout, then letterspaced section headings
underlined in orange with orange square bullets beneath them. Source links use
`#1565C0`.

Rules and borders are light grey `#D9D9D9` at 0.75pt; section underlines are
orange at 1.5pt and the callout bar is 3pt. Verified against Word in the browser
in dark mode: Word renders the page dark but leaves an explicit light border
colour light, so `#D9D9D9` stays visible against the dark canvas. A mid grey such
as `#9C9C9C` sits close to the dark page colour and disappears — do NOT darken
these borders to "improve" dark mode, it does the opposite. Weight, not
darkness, is the lever if they need to stand out more.

## Bulletin category types (label — color — criteria)
- THREAT BULLETIN `#C62828` — critical vulns, active exploitation, urgent threats
- VULNERABILITY ALERT `#B71C1C` — high CVSS (9.0+), CISA KEV additions, not yet exploited
- MALWARE CAMPAIGN `#EF6C00` — sector-targeted malware distribution
- THREAT ACTOR ACTIVITY `#E65100` — APT or criminal groups targeting the sector
- SUPPLY CHAIN ALERT `#FF8F00` — vendor compromises, malicious updates, libraries
- PEER INCIDENT `#6A1B9A` — competitor or peer organization breaches
- AWARENESS BULLETIN `#1565C0` — phishing trends, social engineering, general awareness
- INDUSTRY ALERT `#00796B` — broader sector trends, regulatory enforcement

## Severity / reference levels (label — color — criteria)
- CRITICAL `#B71C1C` — confirmed active targeting of GeneLabs; immediate action required
- HIGH `#C62828` — vulnerability in our environment + active exploitation in the wild
- MEDIUM `#EF6C00` — relevant to sector, no confirmed targeting of GeneLabs
- LOW `#2E7D32` — tangentially relevant; good awareness but low immediate risk
- INFORMATIONAL `#1565C0` — no immediate relevance; situational awareness only

These legend colors are published internally and stay fixed; they are not part
of the corporate palette pass above.

## Reference files
- `assets/bulletin_template.docx` — the empty branded template (clone this).
- `assets/genelabs_wordmark_grey.png` — footer wordmark, resolved automatically.
- `assets/example_branded_bulletin.docx` — CTI26-14, built by this script; the
  reference for what correct output looks like, including the Questions to Ask
  close.
- `assets/example_published_bulletin.docx` — CTI26-07 as published; the
  reference for section flow, citation placement and editorial voice.
- `assets/example_filled_bulletin.docx` — CTI26-10, another published bulletin,
  showing the grouped multi-question-per-team pattern.
- `scripts/build_bulletin.py` — the builder; run it, don't reimplement it. Its
  header comment still shows the deprecated `CTI-26-NN` ID form and describes
  `questions` as the "legacy alternative" to `recommended_actions`; both are out
  of date. This file is authoritative: `questions` is the default and groups by
  team.

