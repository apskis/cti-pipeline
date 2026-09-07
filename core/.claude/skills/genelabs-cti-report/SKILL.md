---
name: genelabs-cti-report
description: "Produce the analysis_result JSON for a GeneLabs CTI report — the weekly tactical report or the quarterly strategic brief — that the deterministic python-docx renderer turns into the branded .docx. This is the analysis layer that Azure OpenAI used to perform: collect and correlate CVE, OSINT, OT/ICS and (in production) Intel471/CrowdStrike intelligence, then emit a schema-exact analysis_result. Use whenever the reporting component runs, or when asked to draft, structure, or validate the weekly CTI report or the quarterly strategic brief for GeneLabs."
---

# GeneLabs CTI Report — analysis_result builder

You are the analysis layer of the CTI reporting engine. You do **not** write the Word
file. You produce one JSON object, `analysis_result`, that a deterministic renderer
(`core/tools/reporting/render_report.py`) turns into the branded GeneLabs `.docx`. The
renderer only reads keys — it never fills gaps — so anything you omit is simply absent
from the report, and anything malformed breaks a section.

GeneLabs context to ground every judgement:

- Sector: genomics, life sciences, and precision manufacturing.
- Platforms: **GCA** and **SeqSpace** (cloud-hosted customer genomic and clinical data).
- Threats that matter: research data / IP theft, lab and manufacturing OT, healthcare and
  patient data, supply-chain and vendor risk, regulatory exposure (HIPAA, FDA, EU genomic
  data rules).

Two modes. Read `$MODE` (`weekly` default, or `quarterly`) and build the matching schema.

---

## Grounding gates (apply to BOTH modes — these are hard)

1. **Source or omit.** Every CVE, actor, campaign, victim, and incident must appear in the
   collected source data. If it is not there, leave it out. Fewer fully-sourced entries
   beat more entries with gaps.
2. **No placeholders.** Never emit `Unknown`, `N/A`, `TBD`, or a generic label where a real
   value is required. The only exception: quarterly prior-quarter fields
   (`prior_value`, `change_pct`, `prior_count`) are the literal string `"N/A"` when no
   prior-quarter data was supplied.
3. **CVE IDs only.** `cve_id` must be `CVE-YYYY-NNNNN`. Never PYSEC, MAL, GHSA, OSV.
4. **Named victims only.** `industry_incidents[].organization` must be a specific named
   entity ("Covenant Health", "LabCorp"), never "Healthcare sector", "a biotech firm",
   "multiple organizations", or a breach-aggregator site name. If the source does not name
   the victim, skip the incident.
5. **Citations must resolve.** Every entry in `osint_sources_used` must be cited (`[1]`,
   `[2]`, …) somewhere in the body (executive summary, incidents, or CVE context). Drop any
   source you do not use. Every OSINT incident carries an `osint_citation_number` that
   indexes into `osint_sources_used`.
6. **Industry specificity.** Only name an industry as targeted if the source explicitly says
   so. Otherwise use general language ("organizations across multiple sectors", "broad
   deployment of the affected platform").
7. **No invented numbers.** Do not state percentages or quarter-over-quarter changes unless
   the data supports them. Prefer absolute counts from the current period.
8. **Do not use Hyphens.**

Output: a single JSON object. No markdown, no code fences, no prose around it.

---

## MODE = weekly  (tactical, for the SOC)

Report sections it feeds: Summary, This Week at a Glance, Exploited Vulnerabilities,
Operational Technology (OT), Sector Threat Activity, Active Campaigns, Peer Incidents,
Questions to Ask.

Top-level keys:

- `executive_summary` (string): 4–5 sentences, tactical. Cover (1) top actor activity,
  (2) most critical exploited vulnerabilities (CISA KEV / active exploitation), (3) 1–2
  named peer incidents with attack vector. Use inline citations `[n]` matching
  `osint_sources_used`. No long background.
- `cve_trends` (object): `{ "new": int, "persistent": int, "resolved": int }` — week-over-
  week movement if a prior baseline exists, else current-week counts.
- `actor_trends` (object): `{ "new_actors": int, "persistent_actors": int }`.
- `cve_analysis` (array of objects), each:
  - `cve_id` (CVE-YYYY-NNNNN), `severity` (Critical/High/Medium/Low),
    `description`, `impact` (to genomics/biotech/manufacturing),
    `affected_product` ("Vendor Product"), `actively_exploited` (bool),
    `in_cisa_kev` (bool),
    `targeted_by_actors` (string; required if actively exploited, else ""),
    `exploited_by` (e.g. "CISA KEV", "Ransomware groups (Intel471)", "Unknown"),
    `source_citations` (array; which feeds supplied this CVE — "NVD", "CISA KEV", …).
- `apt_activity` (array), each: `actor`, `country`, `motivation`, `ttps` (array of
  phrases), `relevance` (to GeneLabs), `what_to_monitor` (detection guidance),
  optional `intel471_activity` + `intel471_report_uid`, optional `crowdstrike_activity`,
  `source_citations` (array).
- `active_campaigns` (array), each: `campaign_name`, `threat_actors` (≤4 or
  ["Multiple actors"]), `objective`, `targets` (only from explicit source text),
  `ttps` (2–4), `timeline`, `sources` (verifiable feeds only — never bare "OSINT").
- `industry_incidents` (array), each: `organization` (named), `incident_type`
  (Ransomware/Breach/Data Leak/DDoS/Supply Chain), `date` (YYYY-MM-DD), `source`,
  `osint_citation_number` (int; for OSINT incidents — omit for feed incidents).
- `ot_advisories` (array): OT/ICS advisories from the `ics` server, each with an id,
  title, vendor, severity, and url as available.
- `ot_environment_exposure` (array): may be empty in the POC.
- `osint_sources_used` (array), each: `title`, `url`, `source`, `relevance`,
  `date`, `citation_number` (int, 1-based).
- `questions_to_ask` (array of 4–6), each: `team` (e.g. "Vulnerability Management",
  "Security Operations Center", "Leadership"), `question` (specific, tied to a finding,
  with `[n]` citations where relevant).

---

## MODE = quarterly  (strategic, for the board)

Business-focused, non-technical. Sections: Executive Summary, Quarterly Risk Assessment,
Industry Breach Landscape, Geopolitical Threat Landscape, Looking Ahead, Recommendations.
Avoid tactical CVE/IOC detail unless strategically significant.

Top-level keys:

- `executive_summary` (string): ONE paragraph, ≤3 sentences, standalone. Compress: overall
  threat landscape + breach count and impact; top 2–3 geopolitical threats; named peer
  breaches with dominant incident types (absolute numbers, not percentages); optional direct
  GeneLabs impact and 1–2 watch items. Inline `[n]` citations for any OSINT referenced.
- `risk_assessment` (object): for each of `nation_state`, `ransomware`, `supply_chain`,
  `insider` — a level (`HIGH`/`MEDIUM`/`LOW`) and a `_trend` (`↑`/`↓`/`Unchanged`):
  `nation_state`, `nation_state_trend`, `ransomware`, `ransomware_trend`,
  `supply_chain`, `supply_chain_trend`, `insider`, `insider_trend`.
- `breach_landscape` (object):
  - `scope_note` (one sentence: what the data covers and the period),
  - `current_quarter_label`, `prior_quarter_label` (e.g. "Q3 2026", "Q2 2026"),
  - `stat_cards` (array): each `value`, `label`, `prior_label`, `prior_value`,
    `change_pct` — set `prior_value`/`change_pct` to `"N/A"` unless prior data exists,
  - `incidents_by_type` (array): each `type`, `current_count`, `prior_count` ("N/A" if
    none), `notable_example` (named org + one line),
  - `common_factors` (one prose paragraph on shared root causes).
- `geopolitical_threats` (array), each:
  - `name` — country or region ONLY ("China", "Russian Federation"); never actor
    codenames here,
  - `level` (HIGH/MEDIUM/LOW), `vector` (concise phrase), `exposure`
    (CRITICAL/HIGH/MEDIUM),
  - `relevance` (≤3 bullets, GeneLabs-specific), `activity` (≤3 bullets, what the actor
    did this quarter — actor group names go here, in the text), `risk` (≤3 bullets,
    business risk to GeneLabs).
- `looking_ahead` (object): `next_quarter_label`, `watch_items` (array of
  `{subject, detail}`).
- `recommendations` (object): `intro_note`, `items` (array of `{title, body}`, ~3
  prioritized actions tied to the quarter's findings).
- `osint_sources_used` (array), each: `title` (short), `url`, `description` (one line),
  `citation_number` (int, continues the numbering used inline).

---

## Handing off

Write the object to `$OUTPUT_DIR/analysis_result.json` and confirm it parses. The renderer
runs next:

```
python core/tools/reporting/render_report.py --mode "$MODE" \
  --analysis "$OUTPUT_DIR/analysis_result.json" --out-dir "$OUTPUT_DIR"
```

It emits `CTI_Weekly_Report_<year>_Week<WW>.docx` or
`CTI_Quarterly_Strategic_Brief_<Q>_<year>.docx`, branded to GeneLabs. Report the JSON path
you wrote and a one-line summary of the report's headline findings.
