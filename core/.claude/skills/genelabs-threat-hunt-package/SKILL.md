---
name: "genelabs-threat-hunt-package"
description: "Build an GeneLabs-branded Threat Hunt PACKAGE .docx — the prospective, not-yet-executed hunt WORK ORDER in April's CTI2602 house style: a five-row metadata header, ABLE hypotheses, CrowdStrike Falcon CQL (LogScale) hunt queries, REQUIRED supporting Splunk SPL (data model first, raw index fallback, linted via the genelabs-splunk-spl skill), IOC Inventory, MITRE ATT&CK & D3FEND mappings and recommended Splunk saved searches. Use when developing hunt hypotheses, writing hunt queries, or turning CTI scan/bulletin findings into a runnable hunt plan. Contains NO findings, verdicts, classifications, Coverage & Gaps or blank execution sections — once the hunt has been RUN, use genelabs-threat-hunt-report instead."
---

# GeneLabs Threat Hunt Package Builder

> **A package is a WORK ORDER, not a report.** It is the input a human analyst or
> an AI agent picks up in order to RUN a hunt. Everything that is an OUTPUT of
> running one — verdicts, findings, classifications, coverage gaps, execution
> logs — belongs to **genelabs-threat-hunt-report**, not here.

Generates a downloadable, branded threat hunt document matching April's CTI2602
structure, with Splunk queries against GeneLabs's real accelerated data
models. Branding comes from `assets/hunt_template.docx` (same GeneLabs banner as
the bulletin skill) — clone it, never rebuild the banner.

## WHAT CHANGED ON 2026-08-24 — read this before adding anything back

April removed five things from the package. Each was removed for a stated reason.
Do not reintroduce any of them.

| Removed | Why |
| --- | --- |
| `status`, `start_date`, `end_date`, `reviewed_by` in the metadata header | All four were emitted as placeholders — "Proposed", an empty end date, "[Pending Review]". They are outcomes of running the hunt, recorded by the report skill. Furniture, not information. |
| The metadata table's 4-column layout | With those four fields gone the right-hand pair was empty. The header is now a straight 2-column label/value table. |
| Findings, Investigation Result, findings index | A package has no findings. Filling them was the single largest fabrication risk in the document. |
| Findings Classification Key | Nothing in a package is classified, so the key had nothing to key. |
| Coverage & Gaps roll-up | Auto-built from findings classified as gaps. No findings, no roll-up. Gaps get recorded by the report skill after the hunt has run. |
| Blank "Execution Log" and "Outcome & Classification" sections | Ruled lines for someone to write on. The hunt is executed by the CTI Threat Hunting Automation task or by an analyst working in Falcon and Splunk, and the result is written into a report, not back into the package. |
| The **Coverage** column in the MITRE ATT&CK & D3FEND table | **Nothing sourced it.** It was being written from the author's own judgement about GeneLabs's telemetry — "Yes", "Partial", "No" — and rendered in a table alongside real ATT&CK IDs, so it read as a measured fact. It was not. The table is now four columns. **Never reintroduce a coverage, confidence or maturity rating in this document in any form.** |

If a future task prompt still asks for any of the above, **this file wins** — and
say so in the run output rather than silently complying.

## Where the builder lives

```
CTI Deliverables\CTI Threat Hunts\Threat Hunt Packages\_tools\build_hunt.py
```

Not in this skill directory. A saved skill stores only `SKILL.md`; its directory
is a read-only cache, so a builder kept there cannot be changed. The workspace
copy is authoritative and carries the 2026-08-24 edits. The copy still sitting at
`scripts/build_hunt.py` in the skill cache is the OLD version — do not run it.

```
python3 "<PACKAGES>/_tools/build_hunt.py" spec.json out.docx "<skill>/assets/hunt_template.docx"
```

If `python-docx` is missing: `pip install python-docx --break-system-packages`.

Two traps in that builder, both already fixed, both easy to reintroduce:
`_set_grid()` and `_fixed_layout()` take **`Inches(...)` Length objects, not bare
floats** — passing a float raises `AttributeError: 'float' object has no
attribute 'twips'`. `grid_table()` is the opposite and takes bare floats.

## Connector-assisted scoping — connector state re-probed 2026-08-27

Scoping a hypothesis against the real estate is the difference between a hunt
that guesses and one that states. But **connector availability moves week to
week, and a scoping step written as mandatory becomes a step that cannot be
performed.** Probe before you rely on one, and where a connector is down, say
what could not be assessed rather than reporting a clean scope.

**`claroty_devices` — the OT/IoT/IT asset inventory. CURRENTLY DOWN.**
Both `claroty_devices` and `claroty_vulnerabilities` return **HTTP 422** as of
2026-08-27; the wrapper requests fields the xDome API no longer accepts, and this
was control-tested three ways (unfiltered, nonsense search, and by cve_id), all
identical. This is **GAP-23**.

- **Consequence for a package: the OT/IoT leg CANNOT be scoped.** Write "OT could
  not be assessed, GAP-23", never "no OT exposure". An unscoped tier is a stated
  gap, not a clean result.
- **The `No EDR` count is not derivable while this is down.** Where a hypothesis
  depends on Falcon telemetry, bound the unsensored tier with what still works:
  `falcon_search_hosts` for sensor state and RFM, `falcon_search_unmanaged_assets`
  for what Falcon can see but does not cover, and Splunk `Network_Traffic` for
  hosts that appear in flows with no sensor at all. Say which method you used.
- **The Claroty VULN SPL FEED IS UNAFFECTED** and remains the device-level
  CVE-to-asset source: `index=claroty sourcetype=claroty:vulnerabilities:json`.
  Not accelerated — keep the CVE keyword tight and widen the window rather than
  broadening the search.
- When the connectors return, the prior limit resumes: `claroty_devices` caps at
  25 rows with no offset, so any `No EDR` count is a SAMPLE (GAP-18), and the
  `search` parameter has always returned 422 — call it unfiltered and filter the
  returned list in your own code.

**`enrich_indicator` and `tq_search_indicator` — IOC validation.** Run both on every
network IOC before it enters the IOC Inventory. `enrich_indicator` fans out across
Shodan, Intel 471 and ThreatQ and independently corroborates or contradicts the
reporting; its Claroty leg returns 401 and it does not accept IPv6 (use
`shodan_host` directly for those). `tq_search_indicator` says whether ThreatQ
already holds the indicator, when it was ingested and from which feed. Record both
in the IOC `notes` column. An indicator already in ThreatQ is already known to
GeneLabs, which changes a recommendation from "load these as Falcon custom IOCs"
to "already covered, hunt the behaviour".

**THE INVERSE IS ITS OWN FINDING.** An indicator that IS in ThreatQ but whose
traffic was still ALLOWED is a blocklist enforcement gap — **GAP-22**, now at three
instances across three workstreams, so it is a confirmed systemic pipeline problem
rather than a fresh discovery. Where a package's IOCs are already held, say
whether their traffic was permitted.

**`nvd_cve`** gives the authoritative CVSS, vector, CWE and affected version ranges
for a vulnerability-driven hunt, **and it returns `kev.due_date`** — take the KEV
deadline from that field rather than inferring one. Where it returns not found,
say "not yet ingested by NVD as of <date>" rather than implying no score exists.

**`falcon_search_applications`** is the product-to-asset join and is licensed where
Spotlight is not — the answer to "do we run this at all". It sees **SENSORED HOSTS
ONLY** (GAP-09), so corroborate with Splunk before writing a zero. It is NOT a
CVE-to-asset join. Its total moves day to day, so read `pagination.total` in your
own run rather than quoting a remembered figure.

**Known broken as of 2026-08-27 — do not read their empty output as a result:**
`claroty_devices` and `claroty_vulnerabilities` (HTTP 422, GAP-23),
`falcon_search_vulnerabilities` (Spotlight unlicensed, HTTP 403, GAP-01),
`ics_advisories` (returns 0 unconditionally, and a real vendor and a nonsense
vendor both return 0 so no control can distinguish working from dead — GAP-19),
`falcon_search_recon_notifications` (returns 0 because no Recon rules are
configured, a CONFIGURATION gap, GAP-17), and there is no CVE-to-asset join for IT
via Rapid7 (GAP-02).

**Working as of 2026-08-27**, contrary to older notes in this file's history:
`nvd_search` (substring search over descriptions; single distinctive token only),
`tq_recent_indicators`, `tq_events`, `intel471_reports`, `intel471_alerts` and
`intel471_search_indicators`, `rapid7_assets`, `rapid7_vulnerabilities`,
`ics_vendors` and `ics_products`. **Probe rather than trusting this list** — it is
a snapshot, and the reason the list is dated is that it goes stale.

Patch state still has no automated per-CVE exposure answer, so never write a
per-CVE exposure count. Write patch state as a manual InsightVM console step and
name it as a coverage gap in the hypothesis text.

## Hunt ID and filename format — follow exactly

**Hunt ID: `THYY-NN`** — no hyphen between `TH` and the year. Matches the bulletin
series (`CTIYY-NN`) so hunts and bulletins read as one set.
Correct: `TH26-02`, `TH26-14`. Wrong: `TH-26-02`, `TH2602`.

**Filename: `THYY-NN-Title_Case_Slug.docx`** — the hunt ID, a hyphen, then a slug
in which every word starts with a capital and spaces become underscores.

```
TH26-14-SynkLoader_Microsoft_Teams_Helpdesk_Loader.docx
TH26-15-Rust_Crate_Supply_Chain_Sapphire_Sleet.docx
TH26-17-iAuthFlow_Passkey_Enrollment_Persistence.docx
```

- Preserve natural capitalisation of acronyms, products and vendors: `SSH`, `RCE`,
  `DNS`, `IKE`, `M365`, `vCenter`, `macOS`, `iAuthFlow`, `DOUBLECUP`.
- Sequential IDs sort chronologically on their own — never add a date prefix.
- `meta.hunt_title` must equal the filename stem EXACTLY, so the body and the
  `DOC #` footer field agree with the file on disk.
- Saved searches are named `THYYNN_<slug>` (no hyphens, e.g.
  `TH2614_SynkLoader_MSI_To_Python_Chain`), matching the package's own hunt ID.
- **Deprecated, never produce:** `TH-26-NN`, `TH-26-XX_hunt_package.docx`.

To find the next number, list the Threat Hunt Packages folder and take the highest
`THYY-NN` present. **ONE PACKAGE PER HYPOTHESIS** — each hypothesis gets its own
hunt ID so it can be run, assigned and closed independently. Because every package
holds a single hypothesis, **OMIT `attack_summary`**.

## Who runs the package

Either the scheduled CTI Threat Hunting Automation task (weekdays 16:03), or April interactively in
the Claude desktop app with falcon-mcp connected. Set `handoff_note` to exactly:

> Open this package in the Claude desktop app with falcon-mcp connected and reply
> 'investigate' — Claude runs the CQL across the fleet (last 14 days), corroborates
> with the Splunk tstats, checks Falcon detections and custom IOCs, rules on the
> hypothesis, and files the completed record using the genelabs-threat-hunt-report
> skill. Findings are NOT recorded in this package.

If falcon-mcp is available while you are BUILDING the package, you may run the CQL
first to confirm the ABLE Location and Evidence actually exist, and drop a
hypothesis whose telemetry does not exist at all. But do not write results into
the package — a package with results is a report, and there is a skill for that.
**Never invent findings.**

NOTE: GeneLabs does not license Falcon Spotlight — `falcon_search_vulnerabilities`
always returns 403. Never write a query or step that depends on Falcon
vulnerability data.

## Query generation — CrowdStrike CQL is PRIMARY, Splunk SPL is REQUIRED

Lead every hypothesis with **CrowdStrike Falcon CQL (LogScale)** in the `falcon`
array — Falcon is the endpoint source of truth. Write real CQL (groupBy / in() /
regex / table / sort), not Splunk-style Event Search.

**BOTH SETS ARE REQUIRED.** Splunk SPL follows in `queries` as corroboration and
reaches hosts with no Falcon sensor, which is why it earns its place. A package
shipped without a populated `queries` array is incomplete. This reverses an earlier
CQL-only default, at April's instruction on 2026-08-21.

`data_sources` must list BOTH the Falcon events and the Splunk data models used.

`saved_searches` are a SEPARATE set from `queries`: 1-3 accelerated tstats that
become production ES detections. `queries` is what the analyst runs during the
hunt; `saved_searches` is what survives it.

OMIT the analyst-role fields (`hunt_lead`, `scribe`, `ti_threatq`, `crowdstrike`,
`proofpoint`, `splunk`). They render only if explicitly supplied.

### Query construction rules — measured against the live tenant, not preferences

1. **Never write an unscoped fleet-wide ProcessRollup2 query.** Fleet process
   volume is roughly 3.8M events per 15 minutes. A fleet-wide ProcessRollup2
   search exceeded the 60s tool timeout at 14 days, at 2 days, and even scoped to
   one host over 14 days. Every ProcessRollup2 query MUST carry
   `in(ComputerName, values=[...])`.
2. **Lead with network or DNS events for fleet-wide scoping.**
   NetworkReceiveAcceptIP4, NetworkConnectIP4 and DnsRequest complete comfortably
   fleet-wide over 14 days. Use them to build a candidate host list, then scope
   process queries to it. Structure every hypothesis as (a) a cheap fleet-wide
   scoping query, then (b) host-scoped follow-ups that explicitly reference (a).
   State the dependency in each query's `purpose`.
3. **Do not query DetectionSummaryEvent.** It returns zero rows in this tenant's
   search-all repository even under a bare groupBy over 14 days, while the
   Detections API returns detections for the same period — so a CQL detection
   query yields a false clean negative rather than an error. Specify
   `falcon_search_detections` with an FQL filter instead.
4. **Qualify detection technique filters.** Falcon Identity Protection maps
   AbnormalCloudApplicationUsage to T1210 and Cloud Security maps AWS mass
   deletion to T1496, so an unqualified technique filter returns unrelated
   identity and cloud anomalies. Add `product:'epp'` or a data_domain qualifier.
   Where identity signal is genuinely on-topic, run the identity query separately
   and keep the two result sets apart.
5. **Include a CONTROL query per hypothesis** proving the event source returns
   data at all in the window. Without it a zero result is indistinguishable from
   a broken query, because the API free-text-matches malformed CQL and returns
   HTTP 200 with no rows.
6. **Include a BASELINE / PREVALENCE query** with a distinct host count, so the
   analyst can tell 2 hosts from 4,000. This is the rule most often missed —
   check for it before finishing.
7. **Cap result size.** End every aggregation with `sort(..., order=desc, limit=N)`.
8. **No Spotlight.** Patch state has no automated source; write it as a manual
   InsightVM step and name it as a gap.
9. Bind every query to a maximum 14 day lookback.
10. Exclude or account for the fleet's top process-volume hosts (build and dev
    infrastructure) in any fleet-wide aggregation: `<host-a>`,
    `<host-b>`, `<host-c>`. Where you must use a placeholder
    hostname prefix, say in the `purpose` that the naming convention must be
    confirmed before running — do not silently guess a pattern and present it as
    fact.
11. **Beware ephemeral source-port collisions.** Two unrelated ports reporting an
    IDENTICAL distinct-destination count is ephemeral allocation, not a finding
    (TH26-04A, TH26-13). THE LOOKALIKE THAT IS NOT THIS: one source hitting many
    destinations on ONE port with an identical per-target count is a scanner's
    fixed probe budget, which IS a real finding. Say which one the query is
    looking for.

## Splunk SPL — the house rules live in `genelabs-splunk-spl`

**Invoke the `genelabs-splunk-spl` skill and lint every SPL query this package
will contain.** That skill is the single source of truth for GeneLabs's SPL rules,
the measured index-to-sourcetype map, and the known-empty and non-accelerable data
models. Do not restate its contents here — a second copy is a copy that goes
stale, and a stale copy of a safety rule is worse than a pointer to a live one.

```
python "CTI Deliverables\_tools\splunk_spl_lint.py" "<your SPL>" [--timed]
```

**Exit 1 means the query does not go in the package.** A package is a work order:
an SPL query written into one will be run later, by someone who reasonably assumes
it was checked. Lint at authoring time, not at execution time.

The four rules that most often shape a package's queries:

1. **Never `index=` without `sourcetype=`, and never bare `index=*` over raw
   events.** An index holds many sourcetypes with different fields — `<firewall-index>`
   alone carries `<vendor>:traffic` (no `url` field) and `<vendor>:threat` (has `url`), so
   the two literally disagree about whether a field exists.
2. **DATA MODEL FIRST, RAW INDEX AS A REASONED FALLBACK.** Lead with the
   accelerated `tstats` because it is fast and consistent.
3. **WRITE THE FALLBACK INTO THE PACKAGE, with its own `name` and `purpose`
   explaining when to reach for it.** This is the package-specific rule and the
   one most often missed. If the accelerated model returns zero at execution time,
   the analyst needs the raw-index query already written and already linted —
   otherwise the zero gets recorded as a clean result. On 2026-08-27 a CIM field
   rendering as the literal string `unknown` was recorded as "unanswerable",
   shipped in two documents, and was wrong: the raw index carried the field all
   along. **A data model is a mapping over the data, not the data.**
4. **Bound every search to the 14 day window and cap every aggregation.**

Where a hypothesis depends on request OUTCOME — served versus rejected — say so
explicitly, because `Web.status` renders as the literal string `unknown` (GAP-14)
and the answer lives in `index=<web-index> sourcetype=<web-sourcetype>` (`sc_status`, `cs_uri_stem`,
`c_ip`, `cs_method`), subject to per-host onboarding (GAP-25).

## Supporting Splunk queries — accelerated tstats

3-6 per hypothesis, spanning every source class the behaviour touches (endpoint,
network, web/proxy, authentication, email) rather than only one. Each needs a
`name`, a `source` naming the data model, and a `purpose` stating the lookback and
the false positives excluded. House pattern:

```
| tstats summariesonly=true count from datamodel=<Model>.<Object>
    where <Prefix>.<field>="..." [NOT (<Prefix>.<field>="<known FP>")]
    by <Prefix>.dest <Prefix>.user _time
| rename <Prefix>.* as *
| sort - _time
```

### MEASURED DATA MODEL FACTS — these override the bundled reference

Validated live against the GeneLabs search head (sh-i-079a654b2fb7e6fbe,
v10.4.2604.9) on 2026-08-20, with the Web corrections of 2026-08-27. The bundled
reference is aspirational in places; these are measurements.

| Model / object | Reality | What to do |
| --- | --- | --- |
| `Network_Resolution.DNS` | **0 events** over 7 and 14 days | EMPTY. Never write a DNS tstats — it returns a false clean negative, not an error. Use `Web.Web` (proxy) instead. |
| `Network_Sessions.All_Sessions` / `.VPN` | **0 events** | EMPTY. Note as a gap; do not build on it. |
| `<firewall-app>.log.traffic` | not accelerable | Use `Network_Traffic.All_Traffic`. |
| `Authentication.Successful_Authentication` | not accelerable | Use the ROOT object with `action="success"`. |
| `Authentication.authentication_method` | numeric Windows logon types (3, 9, 5, 4, 2, 7, 11) | A filter on `="SAML"` or `="FIDO2"` returns nothing and looks like a clean result (GAP-15). |
| `Endpoint.*` | accelerated to **-1w ONLY** | `summariesonly=true` returns at most 7 days regardless of the picker. Say so in the `purpose` of EVERY Endpoint query (GAP-07). |
| `Endpoint.Ports` | returned **ZERO** under a bare groupBy on 2026-08-25 against ~1M events on 2026-08-20 | CONTROL-TEST IT (GAP-08). Never read its empty result as a clean environment. |
| `Web.url` | **carries full URLs WITH paths and query strings** | PATH-BASED HUNTING IS AVAILABLE and is often the query most likely to find an exploitation ATTEMPT. GAP-13, which claimed domain-only, is **RETRACTED**. |
| `Web.status`, `Web.http_user_agent`, `Web.dest` | render as the literal string `"unknown"` | Never group by `Web.dest`. For request OUTCOME use raw `index=<web-index> sourcetype=<web-sourcetype>` (GAP-14 / GAP-25). |
| `Malware.Malware_Attacks` | 7,275 events; `signature` and `action` almost all "unknown" | Low value; prefer Endpoint or the Detections API. |
| `Email.All_Email` | URL fields ABSENT (GAP-12) | "Did the lure arrive by mail" cannot be answered here. Hand a Proofpoint trace to the SOC instead of concluding it did not. |

Working and populated, with measured volumes: `Endpoint.Processes` (1,000,107,684
/ 7d), `Endpoint.Filesystem` (471,583), `Endpoint.Ports` (~1M),
`Endpoint.Services` (20,642), `Network_Traffic.All_Traffic` (4,978,996,762),
`Web.Web` (1,142,178,539), `Authentication.Authentication` (183,369,784),
`Email.All_Email` (9,275,731).

There is **no `Windows` data model** in this tenant; `Change.All_Changes` is AWS
CloudTrail only; the `Vulnerabilities` CIM model is EMPTY.

Include a CONTROL tstats per package proving the model returns data at all, for
the same reason the CQL set needs one: an empty accelerated model and a clean
environment look identical.

Use the correct FIELD PREFIX, which is not always the leaf node:
Endpoint→leaf (Processes/Filesystem/Services/Ports); Malware→Malware_Attacks;
Authentication→Authentication; Network_Traffic→All_Traffic; Web→Web;
Email→All_Email.

The firewall `action` field is `allowed` / `blocked` / `teardown`. **"allowed"
means the firewall PERMITTED the connection** — an allowed inbound flow from
`L3-Untrust` to a DMZ host is real exposure, not a blocked probe. Zones:
`L3-Untrust` = internet, `L3-DMZ`, `L3-Trust` = internal.

## MITRE ATT&CK & D3FEND — four columns, and no rating

`ATT&CK` · `Tactic / Technique` · `D3FEND` · `Defense Concept`. Every value must
be a published identifier or its published name. **Do not add a fifth column and
do not put a coverage, confidence or maturity judgement into the fourth one.**
If you want to say something about whether GeneLabs can see a technique, say it
in the hypothesis text or in `expected`, in prose. An unsensored-host count IS a
measurement and belongs in the hypothesis text — still not in this table.

## IOCs — always include

Populate `iocs` with every indicator the intel yields (domains, URLs, IPs, hashes,
user-agents, sender addresses). Defang externally-sourced network IOCs
(`okta-sso-verify[.]com`, `hxxps://…`). Reference them from the queries. Validate
each one through `enrich_indicator` and `tq_search_indicator` first and record the
result in `notes`.

**Where an indicator is a LEGITIMATE SERVICE BEING ABUSED** — a CDN, a package
mirror, a public key-value store, a vendor's own distribution domain — say so and
do NOT recommend a blanket block. Measure legitimate volume first.

**READ THE ROWS, DO NOT COUNT THEM.** A substring token false-matches benign
things, and at a genomics company the vocabulary collides with the security one:
`*nuclei*` returns `gonuclei.com`, `nucleix.com`, a SharePoint deck about a nuclei
repeat assay and an SAP search for "nuclei extraction"; `*UniFi*` returns 390 rows
of Waters UNIFI chromatography software and zero Ubiquiti. Decompose any hit
before it enters the inventory.

Where the intel published **no** network IOCs, or published indicators that are
useless — per-infection hashes, for example — say so explicitly as a
`NEGATIVE INDICATOR` row and in `ioc_types`, so a thin inventory reads as a
property of the intelligence rather than as an omission in the package.

## How to build

1. Draft an ABLE hypothesis (Actor, Behavior, Location, Evidence), time-bounded
   and ATT&CK-mapped, for the single item this package covers.
2. Scope it against the estate with whichever asset connectors are actually up
   (see the connector section — Claroty is 422 as of 2026-08-27). State the
   unsensored-host position inside the hypothesis scope, **and name the method
   you used to reach it**. Where a tier could not be scoped, say so as a gap
   rather than omitting it.
3. Write the PRIMARY CQL set and the SUPPORTING SPL set — **each SPL query
   linted, and each accelerated query carrying its raw-index fallback** — plus an
   ATT&CK/D3FEND table and `expected` covering benign versus malicious.
4. Validate and collect IOCs, and write 1-3 saved searches named `THYYNN_<slug>`.
5. Fill the metadata header: `hunt_title`, `trigger_source`, `ioc_types`,
   `campaign_actor_tags`. That is all four fields; there are no others.
6. Run the builder, then run the verification below.
7. Save to the Threat Hunt Packages folder and deliver with present_files.

## Verify before delivering — programmatically, not by eye

Extract the document text and the Consolas-font code blocks, then assert:

- Every executable ProcessRollup2 code block contains `in(ComputerName`. Ignore
  commented-out lines so a "do not use" example does not trip the check.
- Every `sort(` has a matching `limit=`.
- A CONTROL query and a BASELINE/PREVALENCE query are both present, and the
  baseline carries a distinct host count.
- `DetectionSummaryEvent` appears only inside "do not use" warnings, never in an
  executable block.
- Only one hypothesis is present, and no cross-reference survives to a hypothesis
  that is not in this document.
- `queries` is populated and a Supporting Splunk Queries section rendered.
- **EVERY executable SPL block passes `splunk_spl_lint.py`.** Extract them and
  lint each one — this catches an `index=` with no `sourcetype=` that survived
  authoring. A raw-index query shipped in TH26-25 was caught exactly this way.
- No `datamodel=Network_Resolution.*`, `datamodel=Network_Sessions.*`,
  `datamodel=<firewall-app>.*` or `Authentication.Successful_Authentication`
  appears in an executable query. Naming one inside a "do not use" note is fine.
- `meta.hunt_title` equals the filename stem, and no foreign hunt ID appears
  except as deliberate prose (`saved_searches` names must all carry THIS hunt's ID).
- **The metadata table has exactly 2 columns.**
- **The ATT&CK table has exactly 4 columns.**
- **None of these strings appears anywhere in the document:** "Status",
  "Start Date", "End Date", "Reviewed By", "Pending Review", "Proposed",
  "Execution Log", "Outcome & Classification", "Findings Classification Key",
  "Coverage & Gaps", "Investigation Result", "Overall Finding", "Coverage".
  This is the regression test for the 2026-08-24 removals — it catches both a
  reverted builder and a spec that still carries the old keys.

Report the check result in the run output.

## GeneLabs corporate branding (applied by the script)

Shared with `genelabs-cti-bulletin` so hunt packages and bulletins read as one set.
Do not override these in a spec.

| Element | Value |
| --- | --- |
| Accent, section headings, rules, bullets | GeneLabs orange `#FF7109` (`#E05F00` for small heading text and table headers) |
| Body and headline text | Abbey `#444648` |
| Meta text, wordmark, captions | Corporate grey `#676765` |
| Callout (handoff note) | Fill `#FFF4E8` |
| Tables | Label fill `#F4F4F4`, `#D9D9D9` borders at 0.75pt, warm `#FFF8F2` row stripe |
| Links | `#1565C0` |
| Typeface | Arial for prose, Consolas for query code blocks |

Section headings render letterspaced in caps with a 1.5pt orange underline.
Borders stay light grey `#D9D9D9`: Word in the browser renders the page dark but
leaves an explicit light border colour light, so it holds up on the dark canvas.
Do NOT darken these to a mid grey — that sinks them into the page. Weight is the
lever if they need to stand out more. Every page carries the footer furniture:
genelabs wordmark in corporate grey, the TLP marking, `CTI Threat Hunt Package`,
the copyright line (year from `date`), a `DOC #` field carrying `hunt_id`, and
live `Page X of Y` fields, beneath an orange rule.

Optional spec key: `tlp` (defaults to `AMBER+STRICT`).

## JSON spec schema

```json
{
  "hunt_id": "TH26-14",
  "date": "August 24, 2026",
  "run_date": "August 24, 2026",
  "handoff_note": "Open this package in the Claude desktop app with falcon-mcp connected and reply 'investigate' — Claude runs the CQL across the fleet (last 14 days), corroborates with the Splunk tstats, checks Falcon detections and custom IOCs, rules on the hypothesis, and files the completed record using the genelabs-threat-hunt-report skill. Findings are NOT recorded in this package.",
  "meta": {
    "hunt_title": "TH26-14-SynkLoader_Microsoft_Teams_Helpdesk_Loader",
    "trigger_source": "CTI daily scan 2026-08-24. Outlet: Headline, date.",
    "ioc_types": "Domains, URLs, IPs, Hashes — or an explicit statement that none were published",
    "campaign_actor_tags": "SynkLoader; unattributed"
  },
  "hypotheses": [{
    "title": "...",
    "priority": "High — possible exposure: Microsoft Teams, Windows 11 endpoints",
    "trigger_type": "Behavior driven",
    "able": {"actor": "...", "behavior": "...", "location": "...", "evidence": "..."},
    "hypothesis": "One paragraph, testable, time-bounded. State the unsensored-host position inside scope and the method used to reach it.",
    "data_sources": ["CrowdStrike Falcon: DnsRequest, NetworkConnectIP4",
                     "Splunk Endpoint.Processes", "Splunk Web.Web (proxy)",
                     "Splunk raw index=<web-index> sourcetype=<web-sourcetype> (fallback)"],
    "falcon": [{"name": "CONTROL — endpoint stream returns data",
                "event": "ProcessRollup2",
                "purpose": "why + lookback + FP note + dependency on a prior query",
                "cql": "(#event_simpleName=ProcessRollup2)\n| in(ComputerName, values=[\"HOST\"])\n| groupBy([ComputerName], function=count(as=events))\n| sort(events, order=desc, limit=10)"}],
    "queries": [{"name": "MSI from a user-writable path",
                 "source": "Endpoint.Processes",
                 "purpose": "why + lookback + FP note. Endpoint is accelerated to -1w only.",
                 "spl": "| tstats ...\n| rename Processes.* as *\n| sort - _time"},
                {"name": "FALLBACK — raw index if the accelerated model returns zero",
                 "source": "index=wineventlog sourcetype=WinEventLog",
                 "purpose": "Reach for this ONLY if the tstats above returns zero. A zero from an accelerated model is not a clean result. Index AND sourcetype are both named, per the SPL house rules.",
                 "spl": "index=wineventlog sourcetype=WinEventLog earliest=-14d ...\n| stats count by host\n| head 50"}],
    "attack": [{"id": "T1566.003",
                "tactic_technique": "Initial Access — Phishing: Spearphishing via Service",
                "d3fend": "D3-MA",
                "defense": "Message Analysis"}],
    "expected": "Benign vs malicious, plus what would change the verdict.",
    "sources": [{"title": "Outlet: Headline (date)", "url": "https://..."}]
  }],
  "iocs": [{"type": "Domain", "value": "okta-sso-verify[.]com", "source": "GTIG",
            "notes": "AitM lookalike. Not in ThreatQ as of 2026-08-24."}],
  "saved_searches": [{"name": "TH2614_SynkLoader_MSI_To_Python_Chain", "spl": "| tstats ..."}],
  "tlp": "AMBER+STRICT"
}
```

**No other top-level keys are valid.** `status`, `include_classifications`,
`blank_sections`, `gaps`, `findings`, `overall_finding` and `investigation_note`
were removed on 2026-08-24 and the builder ignores them. `attack[].coverage` is
removed and must not be supplied. `meta.start_date`, `meta.end_date` and
`meta.reviewed_by` are removed.

## Reference files
- `assets/hunt_template.docx` — branded template (clone this).
- `assets/genelabs_wordmark_grey.png` — footer wordmark, resolved automatically.
- `references/crowdstrike_cql.md` — CQL (LogScale) syntax, events and fields.
- `references/splunk_datamodels.md` — data model to tstats cheat-sheet. The
  MEASURED DATA MODEL FACTS table above overrides it where they disagree.
- `references/datamodels/*.json` — the raw GeneLabs data models (exact fields).
- `scripts/build_hunt.py` — **STALE.** The pre-2026-08-24 builder. Use the
  workspace copy in `_tools` instead.

## Related skills
- **`genelabs-splunk-spl`** — the SPL house rules and the linter. Invoke it
  whenever you write SPL for a package.
- **`genelabs-threat-hunt-report`** — for a hunt that has been RUN.
- **`genelabs-exposure-advisory`** — if scoping a package surfaces an GeneLabs
  asset reachable from somewhere it should not be, raise one. That is a standing
  rule and applies even when the exposure is outside the scope of what you were
  looking for.

