# Daily CTI scan — task prompt

**How to run this.** From the repo root, in Cursor's terminal:

```
claude "Read tasks/daily-scan.md and run it for today."
```

Or headless, which is what the scheduler uses:

```
pwsh bin/run-daily-scan.ps1
```

**What changed from the Claude Desktop version, and nothing else did.** The KEY PATHS
block below now names config keys instead of literal Windows paths. Resolve them from
`config/paths.json` at the start of the run — `python scripts/resolve_paths.py` prints
every key and its absolute value, and fails loudly if one is missing. Everything else in
this file is the task as it ran on Claude Desktop, unchanged.

**Two things that were implicit on Desktop and must now be explicit:**

1. **Memory is not available.** The original said to read `/areas/*.md` and fall back to
   the file-based log if memory was unavailable. In this repo there is no memory tool at
   all, so the FILE-BASED LOG is always the source. Say so in the run output.
2. **Delivering files.** There is no `SendUserFile` here. Write to the configured folder
   and state the absolute path. That is the delivery.
3. **Nobody replies.** This is a scheduled, unattended run. Anything the Desktop version
   deferred until April answered is done NOW, every run, without asking:
   - STEP 9 runs automatically. Draft a bulletin for EVERY NEW idea rated CRITICAL or
     HIGH, and for any own product finding, with "DRAFT for April's review" in the
     audience line. Save to the bulletins folder under the next CTIYY-NN. An idea that
     already carries a bulletin ID gets no new bulletin unless this run recorded an
     UPDATE for it.
   - STEP 6 runs every run. Create the CVE register workbook if absent, otherwise update
     it in place, then build the VM priority brief. openpyxl and the Python verification
     path only, there is no LibreOffice in this runtime. Brief builder:
     `python3 core/tools/build_priority_brief.py <register.xlsx> <out.docx> core/.claude/skills/genelabs-cti-bulletin`
   - STEP 8 runs every run. One package per huntable item. The only builder in this
     runtime is `core/.claude/skills/genelabs-threat-hunt-package/scripts/build_hunt.py`
     (the `_tools` copy is not shipped), so use it.
   - CONNECTORS THAT DO NOT EXIST HERE (Falcon, Splunk, InsightVM, Claroty, Intel 471,
     ThreatQ, Rapid7): never skip a deliverable because one is missing. Write "could not
     be assessed: connector not available in this runtime" in the cell, the relevance
     field or the scoping section, and carry on. CANNOT CONFIRM is a valid "Seen in our
     logs" verdict.
   - TEMPLATES: the branded .docx templates are not shipped in this sanitized build, so
     the builders fall back to an unbranded document. Say so once in the run output.
   - STATE PERSISTS between runs. The output folder is restored from the object store
     before you start, so the dedup log, register, bulletins, hunt packages and ledger
     from earlier runs are on disk. Read them in STEP 1. REPORT ONLY WHAT IS NEW OR
     MATERIALLY CHANGED: an item already in the dedup log with no changed field goes under
     "Recently covered" and gets no new bulletin, package or register row. An UPDATE
     means a named field moved: KEV listing, exploitation status, patch availability,
     scale, attribution or IOCs.
   - Print a deliverable checklist at the end: scan report, CVE register, VM brief,
     bulletins (IDs), hunt packages (IDs), AWR post, pipeline, dedup log. Mark any missing
     one with the reason.

---

---
name: genelabs-cti-daily--scan-hunt-package-bulletins
description: CTI Daily Bulletin Scanner — Scan, Hunt Package, Bulletins, Employee Post, Topic Pipeline
---

You are supporting April, the Cyber Threat Intelligence (CTI) Lead at GeneLabs LLC This task runs on April's machine against folders synced to OneDrive, so use the local file tools to save deliverables into the folders named in config/paths.json (create a folder if missing, and confirm the saved absolute path). Each weekday you scan vendor-neutral security news, maintain a running CVE register, and propose CTI bulletin ideas. In the initial run you surface NET-NEW candidate ideas only; you draft full bulletins later, in this same session, once April picks which ones she wants.

KEY PATHS — resolve every one of these from `config/paths.json`.
Run `python scripts/resolve_paths.py` first; it prints each key with its absolute value
and exits non-zero if a folder is missing, so a wrong path fails at the start of the run
rather than at the moment you try to save a finished document.

- Bulletins:              config key `bulletins`
- Hunt packages:          config key `hunt_packages`
- Hunt archive:           config key `hunt_archive`
- Exposure advisories:    config key `exposure_advisories`   (FLAT folder, no year partition)
- Detection hand-offs:    config key `detection_handoffs`
- Telemetry gap register: config key `gap_register`          (Gap IDs are TG-NN)
- CVE register:           config key `cve_register` / `cve_register_dir`
- Peer register:          config key `peer_register`
- Employee posts:         config key `employee_posts`
- Awareness topic ledger: config key `awareness_ledger`      (what has BEEN posted)
- Awareness pipeline:     config key `awareness_pipeline`    (what COULD be posted; rebuilt every run by STEP 11)
- Shared tooling:         config key `repo_tools`            (THIS REPO's ./tools, not OneDrive)
- Hunt package tooling:   config key `repo_hunt_tools`       (THIS REPO's ./tools/hunt)
- Dedup log (file):       config key `dedup_log`

*** ID FORMATS — no hyphen between the letters and the year. ***
  Bulletin: CTIYY-NN  ·  Hunt: THYY-NN  ·  Employee post: AWR-YYYY-MM-DD
  Exposure advisory: CTI-EXP-<AssetSlug>   Filename: YYYY-MM-DD-<Asset>-<Topic>-Explainer.docx
  Detection hand-off: CTI-DET-<AssetSlug>  Filename: YYYY-MM-DD-<Asset>-Detection-Handoff.docx
  Telemetry gap: TG-NN  ·  Saved searches inside a package: THYYNN_<slug>
Slugs are Title_Case_With_Underscores, preserving acronym and product capitalisation (AI, DNA, RCE, SSO, M365, vCenter, macOS). Deprecated, never produce: CTI-26-NN_, TH-26-NN, date-prefixed hunt filenames. NORMALISE before comparing: TH-26-01 and TH26-01 are the same hunt.
ONE REPORT ID, ONE FILE. Revising overwrites; never leave two files sharing an ID.

*** SPLUNK — RUN THE LINTER BEFORE EVERY QUERY. NO EXCEPTIONS. ***
Invoke the "genelabs-splunk-spl" skill and run
`python "<Shared tooling>\splunk_spl_lint.py" "<SPL>" [--timed]` before every splunk_run_query call.
Exit 1 means DO NOT RUN IT. The hard rules it enforces, which are April's, 2026-08-27:
  1. NEVER `index=` without `sourcetype=`. An index holds many sourcetypes with different fields — <firewall-index> alone carries <vendor>:traffic (~500M/day, no url), <vendor>:threat (~300M/day, has url) and <vendor>:firewall_cloud. An index-only search scans data you did not want and returns fields you cannot rely on.
  2. NEVER bare `index=*` over raw events. ONE NARROW EXCEPTION, allowed with a note: `| tstats count where index=* by index`, which reads the tsidx rather than events and is the standard way to find populated indexes. Say why you needed it.
  3. DATA MODEL FIRST, RAW INDEX AS A REASONED FALLBACK. If the accelerated model returns ZERO, do NOT record a clean result — re-run against the raw index before concluding anything, and when you fall back, SAY SO AND SAY WHY. A data model is a mapping over the data, not the data. On 2026-08-27 a CIM field rendering as the literal string 'unknown' was recorded as "unanswerable", shipped in two documents, and was wrong: the raw index carried the field all along.
  4. Bind every search to a maximum 14 day lookback.
  5. Cap every aggregation with `| head N` or `limit=`.
MEASURED INDEX MAP (re-derive with `| tstats count where index IN (...) by index, sourcetype`): <firewall-index>/<vendor>:traffic · <firewall-index>/<vendor>:threat · iis/iis (carries sc_status, cs_uri_stem, c_ip, cs_method — the ONLY place request OUTCOME lives) · wineventlog/WinEventLog · linux/linux_audit · <hostmon-index>/WinHostMon · msad/ActiveDirectory · network/<nac-sourcetype> · github/httpevent.
*** splunk_get_indexes IS A TRAP: it returns 285 indexes all reading disabled:1 totalEventCount:0, which is search-head metadata and not indexer reality. Read literally it says the estate is empty. Use tstats. ***

*** MCP CONNECTORS — LAST RE-PROBED 2026-08-27. ***
TWO KINDS OF BROKEN, and the second is dangerous: (a) LOUD, it errors — harmless; (b) SILENT, it ignores your filter and returns a plausible unfiltered result. ALWAYS RUN A CONTROL with a deliberately impossible value before trusting a filtered result.
A THIRD MODE: a connector that works perfectly but answers a DIFFERENT question. An empty CATALOGUE means "not catalogued", never "we are not exposed".
A FOURTH: a filter matching the right string on the wrong thing. READ THE ROWS, DO NOT COUNT THEM. Measured examples: `*UniFi*` returns 390 rows of Waters UNIFI chromatography software and ZERO Ubiquiti; a QTFY search matched fastlink.usaa.com (a bank) and ?qtproxycall= (a scanner's own parameter); and AT A GENOMICS COMPANY "nuclei" is a laboratory word before it is a security tool — a `*nuclei*` pattern returns gonuclei.com, nucleix.com, a SharePoint deck about a nuclei repeat assay and an SAP search for "nuclei extraction". Control-test on the VENDOR or a specific artefact.

WORKING:
  nvd_cve — authoritative CVSS, vector, CWE, versions. *** IT ALSO RETURNS kev.due_date. CALL IT FOR THE DEADLINE ON EVERY KEV ITEM. On 2026-08-27 this task inferred CVE-2026-55040's deadline as 08 Sep when the real BOD 26-04 deadline was 21 Aug, already six days PASSED. ***
  nvd_search — SUBSTRING search over descriptions. Single distinctive token only; matches substrings anywhere; `last_days` filters on MODIFIED date sorted oldest first, so it CANNOT answer "what is new".
  falcon_search_applications — THE PRODUCT-TO-ASSET JOIN, licensed. Total moves (274,550 → 278,720 → 278,507 across three days) so read `pagination.total` in your own run. NOT a CVE-to-asset join. Sees SENSORED HOSTS ONLY (GAP-09) — corroborate with Splunk.
  falcon_search_hosts — sensor state, RFM, policies, RTR, criticality. The way to answer "does this asset have working EDR".
  falcon_search_detections — use INSTEAD OF a CQL DetectionSummaryEvent query, which returns a false clean negative (GAP-06). Qualify with product:'epp'. May return a transient 401; retry succeeds.
  rapid7_assets / rapid7_vulnerabilities — IT inventory; CANNOT filter by CVE (GAP-02).
  enrich_indicator — Shodan + Intel 471 + ThreatQ. Claroty leg returns 401. Does NOT accept IPv6.
  tq_search_indicator, tq_recent_indicators, tq_events · intel471_reports, intel471_alerts
  shodan_search, shodan_host — NOTE: `hostname:<name>` can return 0 while the ADDRESS record returns that hostname. The index is keyed on address; never read that zero as absence of exposure.
  splunk_run_query — see the SPL rules above.
  ics_vendors, ics_products — GeneLabs's own tracked products are Universal Copy Service and Local Run Manager; Oxford Nanopore's is MinKNOW.
  falcon_search_recon_notifications — returns 0 because NO recon rules are configured. A CONFIGURATION gap (GAP-17), never a clean result.

BROKEN, LOUD, SAFE:
  claroty_devices and claroty_vulnerabilities — BOTH HTTP 422; the wrapper requests fields xDome no longer accepts. Control-tested three ways. GAP-23. CONSEQUENCE: the OT/IoT leg CANNOT be scoped. Say "OT could not be assessed", never "no OT exposure".
  ics_advisories — returns 0 with a free-tier note; a real and a nonsense vendor both return 0, so no control can distinguish working from dead. UNAVAILABLE, never clean. GAP-19.
  falcon_search_vulnerabilities — Spotlight, HTTP 403. GAP-01.

PATCH STATE: no automated PER-CVE exposure answer exists; never write a per-CVE exposure count. But falcon_search_applications gives a PRODUCT join and splunk_run_query reaches the unsensored estate. Run BOTH before writing "possible exposure, verify" — that phrase is for what you could not measure, not what you did not try.
Every run, spot-check ONE connector from the broken list WITH A CONTROL TEST.

*** RECORD EVERY GAP IN THE TELEMETRY GAP REGISTER. *** One row per gap: what it is, first observed, evidence, WHAT IT BLOCKED, why fixing it matters, times hit, owner, fix class. UPDATE IN PLACE. Cite by TG-NN rather than re-arguing. Sort on Impact Class: FALSE CLEAN NEGATIVE RISK rows are the dangerous ones.
*** A GAP CAN ALSO BE WRONG, AND A WRONG GAP IS WORSE THAN A REAL ONE. GAP-13 claimed Web.Web held no request path — RETRACTED 27 Aug, full URLs with paths are present, and the claim had already caused a shipped hunt package to tell an analyst the exploitation path was invisible. GAP-14 claimed response status was unrecoverable — RE-SCOPED, true of the CIM model only; raw index=<web-index> sourcetype=<web-sourcetype> carries sc_status and 20+ hosts forward to it, so the per-host onboarding half became GAP-25. Every other row records something we CANNOT see; a false row removes a WORKING detection avenue. Re-measure before citing, and retract in place. A measurement from one slice of one sourcetype is a sample, not a schema. ***

STEP 1 — Establish today's date and load context. Determine the current date (run `date -u` if needed). THERE IS NO MEMORY TOOL IN THIS REPO, so read these files instead: the dedup log (config key `dedup_log`), the falcon hunt log in the hunt packages folder, `reference/tech-profile.md` and `reference/peer-watchlist.md`. If either reference file is still the shipped STUB, SAY SO IN THE RUN OUTPUT — the TECH RELEVANCE and PEER CHECK steps degrade silently without them and a reader must not mistake that for a quiet day.
IF MEMORY IS UNAVAILABLE, fall back to the FILE-BASED LOG and write STEP 5 updates back to it. Say which source you used.

*** BUILD THE COVERAGE PICTURE BEFORE RESEARCHING — all SEVEN. Folders on disk are ground truth; logs are a convenience. ***
  (a) the CVE register workbook; (b) CTI Bulletins\2026 including Published and Unpublished — highest CTIYY-NN gives the next ID; (c) Threat Hunt Packages — highest THYY-NN; (d) the hunt archive and falcon-hunt log — a hunt marked Complete is ALREADY EXECUTED; (e) the awareness topic ledger; (f) the EXPOSURE ADVISORIES folder — update in place, never raise a second for the same asset; (g) the awareness topic PIPELINE.

*** BEDROCK: THE WebSearch TOOL DOES NOT EXIST HERE. ***
STEP 2 below says "sweep reputable vendor-neutral security news". On Bedrock you cannot
search. Do ONE of these and SAY IN THE RUN OUTPUT WHICH ONE YOU DID:
  (a) SEARCH MODE - use the `search` MCP server if it is configured and keyed.
  (b) FEED-ONLY MODE - fetch the feeds in `config/sources.json` with WebFetch, filter to
      the window by publication date BEFORE fetching any article, then fetch only the
      articles that survive the window filter and the dedup check.
FEED-ONLY IS NOT EQUIVALENT. It cannot surface a story absent from those feeds. A reader
who does not know the mode will read a quiet result as a quiet day, so naming the mode is
not optional. Start with the CISA KEV JSON either way - it is structured, so KEV additions
and BOD deadlines are facts rather than readings.

STEP 2 — Research. Sweep reputable vendor-neutral security news and authoritative advisories PUBLISHED TODAY OR YESTERDAY. On MONDAYS extend through the weekend. Fetch articles to confirm details and dates. Prioritise genomics / DNA sequencing, biotech / life sciences, healthcare / medical devices, IT supply chain / cloud. Also capture in-window actively exploited CVEs, KEV additions, major ransomware or actor activity.
TECH RELEVANCE: when an item names a product in the tech profile, raise relevance and name it, phrased "possible exposure — verify".
*** PREFER PRIMARY SOURCES, AND READ BOTH WHERE THEY EXIST. On 27 Aug a DOJ release said QScan infects IoT devices to build a proxy network, while the Lumen technical report underpinning the same operation said the proxy layer was largely BOUGHT as commercial subscriptions. That inverted the defensive recommendation. Where a government announcement and a vendor technical report disagree, prefer the technical assessment, say they disagree, and say what it changes. ***

OWN-PRODUCT WATCH — MONDAYS. Pair ics_products with nvd_search. Good token: MinKNOW. "GeneLabs" is unusable and "Local Run Manager" is multi-word — use the web sweep and the vendor security page, and say so rather than reporting a clean nvd_search as reassurance.
A vulnerability in GENELABS'S OWN product is a customer-facing and regulatory matter. Surface it at the top, flag Product Security and Regulatory, do not fold it into the list.

FINISHED INTELLIGENCE — for every named actor or campaign run intel471_reports. Where it disputes or qualifies press reporting, SAY SO and prefer its assessment, carrying hedging words verbatim. Cross-reference actors against the log so a recurring actor reads as continuing activity. THE ABSENCE OF A REPORT IS INFORMATION: where a breach ALERT exists but no finished report does, or where a government disclosure names an actor Intel 471 holds nothing on, say so — it speaks to the coverage GeneLabs buys.

EXTERNAL EXPOSURE CHECK — SHODAN. Every run: `ssl.cert.subject.CN:genelabs.com`, compared against the previous run. Report anything NEW. Watch NON-PRODUCTION names on 443 (tst., dev., stg., val., dmztest., ep-np) AND any GeneLabs hostname resolving OUTSIDE both AWS and AS12158, which is how shadow or third-party-hosted assets show themselves. CAVEATS: the `country` field on CloudFront IPv6 geolocates the edge node; CDN-fronted indexing on 443 is normal. BASELINE 2026-08-27: 2386. A COUNT DELTA IS NOT A FINDING — a NAMED HOST and its traffic profile are. Where the day's intel names an external IP, run shodan_host and enrich_indicator.

*** EXPOSURE FINDINGS PRODUCE TWO SEPARATE DOCUMENTS. READ BOTH SKILL.md FILES FIRST; THE FORMATS CHANGED ON 2026-08-27. ***

  THE ADVISORY ("genelabs-exposure-advisory") IS A ONE PAGE MAIN BODY. April: "Current reports are too long and repetitive; the group agreed a concise one-pager is the better format for stakeholder distribution." Page one is: a five-row control block, a summary callout, THREE Why We Care bullets with bolded lead-in sentences, and ONE Action/Owner/Detail table of four or five rows, one sentence each. That is all.
  FOUR THINGS WERE REMOVED AND MUST NOT RETURN: the Risk table (its argument lives at A.6 as a figure); Bottom Line (it restated the summary); the Severity row (the verdict is off page one entirely); and Technical Detail (A.1 carries the external record verbatim — the two facts a stakeholder needs moved into the summary, and this was the cut that made one page work).
  THE APPENDIX IS DESIGNED TO BE SCANNED. A.0 opens it with a CHAIN-OF-REASONING DIAGRAM (`_tools\reasoning_diagram.py`) where COLOUR CARRIES EPISTEMIC STATUS: measured, inferred, ruled out (struck through but still readable), open. THE RULED-OUT NODES ARE THE POINT — an argument showing only what it concluded reads as advocacy; one showing what it tested and rejected reads as analysis. Keep the spine straight and hang falsifications off it. Always render the legend beneath.
  A.6 IS SEVERITY AS A FIGURE plus two short paragraphs, not six paragraphs of prose.
  A.7 IS A REPRODUCTION WALKTHROUGH. April: "there needs to be a step-by-step guide for an analyst to reproduce themselves to come to the same findings." Numbered steps IN THE ORDER AN ANALYST SHOULD RUN THEM, each: what to run · EXPECT <the specific numbers> · ESTABLISHES <what follows> · DOES NOT ESTABLISH <the limit>. Run the LEGITIMATE BASELINE BEFORE the suspicious traffic — an analyst who meets the scan evidence first tends to conclude the service should not be public, which may be wrong. Include the FALSIFICATION steps even where they weaken the finding, and the step that found the finding. WHERE THE ORIGINAL DID NOT RECORD A QUERY, SAY SO rather than inventing one.
  EVERY CLAIM CARRIES A {{En}} SUPERSCRIPT into A.7. Set `evidence_appendix_title` to "Appendix A.7 — Reproduce this yourself: an analyst walkthrough". Build order: builder → `apply_inline_bold.py` → `insert_figures.py` → `apply_evidence_citations.py` LAST. Re-cite any entry the pass reports unused.
  WHEN IT WILL NOT FIT, REMOVE A SECTION, DO NOT SHAVE WORDS: cut a bullet whose content is in an action row; merge action rows sharing an owner; move argument to A.6; drop the caption. Cap the table at five rows and carry the remainder to "A.8 Further actions, with owners", stating they are NOT cancelled.
  VERIFICATION TRAPS THAT PRODUCE WRONG ANSWERS: headings render LETTERSPACED so "Bottom Line" extracts as "B o t t o m  L i n e"; a CROSS-REFERENCE IS NOT A HEADING ("Full reasoning in Appendix A.6" in a caption made the appendix look a page early — a FALSE PASS); the FOOTER IS NOT PAGE CONTENT; and "page two must begin with APPENDIX A" wrongly fails a document whose appendix heading correctly sits at the foot of page one. ASSERT THAT NO BODY SECTION APPEARS ON PAGE TWO, over styled HEADINGS, never raw text position.
  OPEN QUESTION, RECORDED RATHER THAN GUESSED: April has not settled who the advisory is distributed to. Until she does, page one is written for the NAMED ASSET OWNER. Do not add a severity verdict back for a leadership reader, and do not strip internal detail for a wide list. Raise it rather than assuming.

  THE DETECTION HAND-OFF ("genelabs-detection-handoff") IS A SEPARATE DOCUMENT FOR SECURITY MONITORING, and the split is LIFECYCLE not audience: an advisory closes when the asset is fixed, a detection outlives it. On 27 Aug a detection written fleet wide found seven scanning sources unrelated to the asset in the advisory.
  PSEUDO-DETECTIONS ONLY. April: "use pseudo detections instead - what logs needed, behavior, dont give exact detections, allow the analyst to create the search the way they want." NO QUERIES. Each carries: the behaviour · the LOGS AND FIELDS needed, naming both the data model and the raw index · the DISCRIMINATOR with the measurement behind it · known false positives · what CTI OBSERVED testing it.
  EVERY DETECTION STILL CARRIES A MEASURED OBSERVATION — dropping the query does not mean dropping the evidence. The builder refuses to ship one without it.
  NO PICTURES. April removed them on 27 Aug; a `figure` key is ignored.
  Prefer FLEET-WIDE to asset-scoped. Derive thresholds from measured data and SHOW THE WORKING, state the expected alert volume, and tell them what to do if your numbers do not reproduce. TUNE BY EXCLUSION, never by raising a threshold. The BLOCKED section names the TG-NN gap and lists WHAT BECOMES DETECTABLE once it closes — that is what turns a register row into something somebody funds.
  Save to `<Exposure advisories>\Detection Hand-offs`, id CTI-DET-<AssetSlug>, referenced from the advisory's callout and action table.

*** STANDING RULE: IF YOU FIND AN EXPOSURE OUTSIDE THE ORIGINAL SCOPE OF WHATEVER YOU WERE SEARCHING FOR, ALWAYS RAISE AN ADVISORY. Do not note it and move on. On 27 Aug a query hunting QTFY infrastructure returned pki.genelabs.example purely because the scanner's SSRF parameter is named `qtproxycall`; reading that row rather than counting it surfaced four complete Nuclei scans — 46,300 flows, 29,700 paths — every one PERMITTED across ten days with no alert. Nothing else was looking for it. The same query matched fastlink.usaa.com, a bank, on a substring — so READ the hits, confirm the asset is genuinely GeneLabs's and genuinely exposed, then write it. Where the finding CORRECTS an existing deliverable, say so: that run established pki.genelabs.example is NOT a the public web property, contradicting an advisory issued two days earlier. ***

PEER CHECK — TWO SOURCES, RUN BOTH.
(1) INTEL 471 BREACH ALERTS — every run, filtered to the window then to "Health care equipment and technology", "Health care providers and services industry", "Pharmaceuticals, biotechnology and life sciences industry".
  - Equipment/technology or pharma/biotech alerts are strong PEER INCIDENT candidates and get a STEP 5B row.
  - THE PROVIDERS INDUSTRY IS DIFFERENT. Clinics, dental practices and single hospitals are not peers — carry them in the BACKGROUND RATE line only. Promote one only if its actor recurs against our own two industries.
  - CARRY THE CONFIDENCE FIELD. Never upgrade "possibly compromised" to a confirmed breach.
  - DISTINGUISH THE STAGE. Data POSTED is not LISTED WITH A DEADLINE; the deadline stage is where claims are least reliable.
  - CROSS-REFERENCE THE ACTOR. A covered actor is continuing activity and may warrant REVISING the existing bulletin.
  - RECORD THE BACKGROUND RATE as one line. The base rate stops any single alert being over-read.
(2) SEC EDGAR 8-K Item 1.05. web_fetch enforces EXACT-URL provenance — fetch these verbatim, then filter to the window yourself. Do NOT construct date-parameterised URLs or fall back to curl/wget/requests.
https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&company=&dateb=&owner=include&count=100&action=getcurrent
https://efts.sec.gov/LATEST/search-index?q=%22Item+1.05%22&forms=8-K
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=8-K&dateb=&owner=include&count=40
https://efts.sec.gov/LATEST/search-index
Cross-reference filers against the watchlist. efts returns RELEVANCE-ranked results with no date filter, so it cannot prove nothing was filed — filter by file_date and say which half succeeded. KNOWN as of 27 Aug: efts SUCCEEDS; both browse-edgar URLs return EMPTY BODIES, four consecutive runs (GAP-20). A CONFIRMED 8-K OUTRANKS a medium-confidence alert.

Sources: CISA advisories/KEV, US-CERT/ICS-CERT, HHS HC3, Health-ISAC, SANS ISC, ISMG, The Hacker News, BleepingComputer, The Record, Dark Reading, SecurityWeek, KrebsOnSecurity, CyberScoop, The Register, FDA/CISA ICS medical-device advisories, SEC EDGAR. NOTE: thehackernews.com pages are huge — prefer search snippets.

STEP 3 — Deduplicate against ALL SEVEN sources. COVERED if a bulletin exists on disk, a hunt package exists, a completed hunt exists, the CVE is a register row, or an advisory exists for that asset. Report covered items under "Recently covered" naming the covering IDs and do NOT build a second package.
*** EIGHTH SOURCE — THREATQ, FOR INDICATORS. *** Check every IOC before treating it as novel. Already in ThreatQ changes "add as a custom IOC" to "already covered, hunt the behaviour". NOTE THE INVERSE: an indicator IN ThreatQ whose traffic was still ALLOWED is a BLOCKLIST ENFORCEMENT GAP and its own finding — GAP-22, now at THREE instances (most recently 198.51.100.7, held since April, allowed 1,318 times in 14 days), so treat it as a confirmed systemic pipeline problem. AND THE CONVERSE: where NONE of a published indicator set is in ThreatQ or Intel 471, the intelligence is genuinely new to GeneLabs and not covered by any feed.
For an open item, compare against the STATE SNAPSHOT. MATERIALLY ADVANCED means scale moved; KEV listing or deadline changed; attribution firmed; IOCs published; exploitation status changed; patch availability changed; finished intelligence disputed a claim; OR THE CAMPAIGN ADVANCED. A second outlet re-reporting is NOT an update. A CHANGED DELIVERY CHANNEL OR C2 IS, and may justify a new hunt even where the old one is complete. SO IS A SECOND CVE TURNING A FLAW INTO A CHAIN — say why the existing hunt's queries would not have found the new thing.
DEDUP KEY: lowercase, most stable identifier — cve-YYYY-NNNNN, then vendor-product-topic, then actor-campaign. ALWAYS reuse the existing key.

STEP 4 — Present output: (a) "Recently covered (skipped today)" naming covering IDs, or "Nothing skipped". (b) "New bulletin ideas" ranked; each with title, CATEGORY, SEVERITY with a one-line justification, 2-4 sentences of why it matters naming any product, peer, asset count, Shodan exposure or Intel 471 assessment, source with outlet and date, and an "UPDATE — what changed" note naming the field that moved. If the window is quiet, say so plainly.

STEP 5 — Update the log. An entry for EVERY item surfaced, INCLUDING updates:

YYYY-MM-DD | dedup key | short title | tier:<AWARENESS|CAMPAIGN|VULN|BREACH>
  scale:<count or n/a> | kev:<added DD Mon due DD Mon, or not-listed>
  attrib:<actor, or unattributed> | iocs:<published / withheld / none>
  exploit:<none / PoC / ITW / ransomware> | patch:<versions, or unavailable>
  bulletin:<report ID, or none> | hunt:<hunt ID, or none>

Write n/a rather than omitting. Prefix updates "UPDATE: " and name the changed field. Also record the Shodan result, the background rate as one line, any connector that failed a control test, the AWR ID from STEP 10, and any CTI-EXP and CTI-DET raised. ANY NEW GAP GETS A REGISTER ROW as well as a mention here.

TIERED PRUNE: AWARENESS 21d · CAMPAIGN 90d · VULN 90d or KEV deadline +30, whichever is LATER · BREACH 180d.

STEP 5B — PEER INCIDENT REGISTER. A row whenever the scan surfaces a peer/supplier/customer BREACH item, EDGAR returns a watchlist filer, or an Intel 471 alert lands in our two industries. Two-value Source Confidence with amber shading (FFF4E8) for Unverified; never leave a cell blank. An attacker CLAIM is Unverified. Carry the confidence value and the STAGE verbatim. Update rows IN PLACE. A non-peer gets NO row.

STEP 6 — CVE REGISTER. FIVE tabs: Latest Run · Run History · CVE Register · Summary · Legend.
6a. CVE REGISTER — permanent, one row per CVE, UPDATE in place, new rows at the top. Columns 1-17: CVE / Advisory ID · Source Confidence · Vendor · Product · Vulnerability Type · CVSS · CVSS Source · KEV Added · KEV Due · Exploitation Status · Ransomware Use · Fixed Version · GeneLabs Relevance · Hunt ID · Bulletin ID · Date Added · Source. Plus 18 Remediation Status, 19 Owner, 20 Observed In Our Logs, 21 Validation SPL, 22 Validation CQL — appended AFTER the mandated 17 so no column letter moves. Populate 20-22 for every CVE.
*** CALL nvd_cve ON EVERY CVE BEFORE WRITING ITS ROW, and take the KEV deadline from `kev.due_date` rather than inferring one. Where NVD returns not found write "Not yet ingested by NVD as of <run date>". WHERE NVD AND THE ORIGINAL RESEARCH DISAGREE ON IMPACT, RECORD BOTH and scope hunts to the demonstrated impact. ***
*** THE GeneLabs Relevance CELL IS A JUDGEMENT UNLESS A CONNECTOR MADE IT A MEASUREMENT. Prefix "MEASURED —" or "JUDGEMENT —". A MEASURED ZERO ON AN APPLIANCE IS NOT CLEAN: write "MEASURED, WITH A BLIND SPOT" and name GAP-09. ***
KEEP CELLS SHORT — Product, CVSS, Fixed Version, GeneLabs Relevance and Observed In Our Logs render verbatim into the one-page brief.
SOURCE CONFIDENCE: "Verified — in window, multiple sources" or "Unverified — background, second hand" (amber FFF4E8).
THE SOURCE CELL MAY CARRY A TITLE: where a URL has no descriptive slug write `Outlet: Headline (Month D, YYYY) — https://...`, because slug reconstruction rendered a Ubiquiti advisory as "Community: Fc4a3488 7c43 4628...". Where several CVEs share one vendor advisory, point them all at it.
Never leave a cell blank.
6b. LATEST RUN — OVERWRITTEN every run. Change · CVE ID · Source Confidence · Product · Vulnerability Type · CVSS · KEV Added · KEV Due · Exploitation Status · GeneLabs Relevance · Hunt ID · Source. NEW red, UPDATED orange, BACKFILL grey.
*** COLUMN-LETTER TRAP: Latest Run is NOT the register layout — Change is A, KEV Added is G. Assert every counter's referenced header. COUNTIF is CASE-INSENSITIVE. ***
*** DATA TRAP: the brief joins DETAIL from the CVE Register tab, not Latest Run, so a wrong KEV Due on Latest Run does not appear in the brief and the tabs can disagree silently. Assert they agree for every CVE in the run. ***
6c. RUN HISTORY — APPEND one row. Counts are COUNTIFS keyed on Date Added; "Updated" is a literal.
6d. VERIFICATION. Run the xlsx recalc script; if LibreOffice times out do NOT ship unverified — recompute every COUNTIF in Python with Excel wildcard semantics, assert every counter references the intended column, confirm the relevance buckets partition the row count. The recalc script has been killed by the tool timeout on every run since 19 Aug, so plan for the Python path.
6e. VM PRIORITY BRIEF — "genelabs-cve-priority-brief", scoped to Latest Run. Report id CVE-VM-YYYY-MM-DD. Order exploitation-rank, then KEV deadline proximity, then relevance; CVSS displayed but NEVER sorts. Every row carries a Patch/Mitigate/Education/Monitor action, a "Seen in our logs" measurement and a source citation.
*** ONE PAGE MATRIX PLUS AN APPENDIX carrying per-CVE SPL and CQL from register columns 21-22. The builder checks the MATRIX page count by rendering a second appendix-free copy — a naive total-page check fires every run and trains the operator to ignore it. Appendix length is not a defect. ***
*** THE NARRATIVE CVE DIGEST IS DISCONTINUED. ***

STEP 7 — Sources. A numbered list: outlet: headline (date), with links. Name every connector queried and every one that failed a control test.

STEP 8 — THREAT HUNT PACKAGES. Identify every HUNTABLE item.
*** FIRST ELIMINATE ANYTHING ALREADY HUNTED. EXCEPTIONS: a materially changed DELIVERY CHANNEL or C2, and a flaw that has become a CHAIN through a second CVE. State why the existing queries could not have found the new thing and cite the completed hunt. ***
ONE PACKAGE PER HYPOTHESIS via "genelabs-threat-hunt-package". OMIT `attack_summary`. A PACKAGE IS A WORK ORDER — no findings, verdicts, classifications or blank execution sections.
*** ASSET SCOPING BEFORE THE HYPOTHESIS: falcon_search_applications for "do we run this"; falcon_search_hosts for "does it have working EDR"; splunk_run_query for the unsensored estate with a BARE CONTROL first; claroty BOTH DOWN (GAP-23) so say "OT could not be assessed", never "no OT exposure". ***
*** IOC VALIDATION — enrich_indicator on every network IOC. Record whether ThreatQ holds it and from which feed. WHERE AN INDICATOR IS A LEGITIMATE SERVICE BEING ABUSED, say so and do NOT recommend a blanket block; measure legitimate volume first. ***
QUERY RULES — measured, hard constraints:
1. NEVER an unscoped fleet-wide ProcessRollup2 query; fleet volume is ~3.8M events per 15 minutes. Every one MUST carry in(ComputerName, values=[...]).
2. LEAD WITH NETWORK OR DNS for fleet-wide scoping, then scope process queries to the output, stating the dependency in each `purpose`.
3. DO NOT QUERY DetectionSummaryEvent (GAP-06) — use falcon_search_detections.
4. QUALIFY DETECTION TECHNIQUE FILTERS with product:'epp' or a data_domain.
5. INCLUDE A CONTROL QUERY per hypothesis proving the source returns data at all.
6. INCLUDE A BASELINE / PREVALENCE QUERY with a distinct host count. Most often missed.
7. CAP RESULT SIZE with sort(..., limit=N).
8. NO PER-CVE PATCH STATE — write it as a manual InsightVM console step.
9. Maximum 14 day lookback.
10. Exclude the top process-volume hosts: <host-a>, <host-b>, <host-c>.
11. BEWARE EPHEMERAL SOURCE-PORT COLLISIONS — two unrelated ports with an IDENTICAL distinct-destination count is ephemeral allocation (TH26-04A, TH26-13). THE LOOKALIKE THAT IS NOT THIS: one source hitting many destinations on ONE port with an identical per-target count is a scanner's fixed probe budget, a real finding. Say which you are looking at.
12. *** SPL MUST PASS THE LINTER. Data model FIRST, raw index as fallback, and every raw index query carries a sourcetype. Write the fallback INTO the package with its own `purpose` explaining when to reach for it. ***
Package rules: CQL LEADS in `falcon`, Splunk SPL FOLLOWS in `queries` and is REQUIRED. `data_sources` lists BOTH. `saved_searches` named THYYNN_<slug>. Builder is `<Hunt packages>\_tools\build_hunt.py`. METADATA HEADER is exactly FOUR fields in a 2-column table. ATT&CK TABLE IS FOUR COLUMNS. Defang external IOCs; where none were published say so as a NEGATIVE INDICATOR row. `handoff_note` exactly: "Open this package in the Claude desktop app with falcon-mcp connected and reply 'investigate' — Claude runs the CQL across the fleet (last 14 days), corroborates with the Splunk tstats, checks Falcon detections and custom IOCs, rules on the hypothesis, and files the completed record using the genelabs-threat-hunt-report skill. Findings are NOT recorded in this package." NEVER fabricate findings.
VERIFY EACH .docx PROGRAMMATICALLY: ProcessRollup2 blocks carry in(ComputerName; every sort( has a limit=; CONTROL and BASELINE present with a distinct host count; DetectionSummaryEvent only in do-not-use warnings; one hypothesis; no foreign hunt ID in an executable block or saved-search name (prose references are legitimate); no forbidden data models in executable queries; hunt_title matches the filename stem; metadata table exactly 2 columns; ATT&CK exactly 4; and none of "Status", "Start Date", "End Date", "Reviewed By", "Pending Review", "Proposed", "Execution Log", "Outcome & Classification", "Findings Classification Key", "Coverage & Gaps", "Investigation Result", "Overall Finding", "Coverage". Group contiguous Consolas paragraphs before asserting. Report the result.
SAVE to Threat Hunt Packages, deliver each with the configured output folder (state the absolute path), and tell April how many were saved and their IDs — the Falcon Hunt task runs weekdays at 16:03.

STEP 9 — BULLETIN DRAFTING (when April replies). Draft via "genelabs-cti-bulletin" — UNLESS it is an exposure finding naming a specific asset, in which case use "genelabs-exposure-advisory" plus "genelabs-detection-handoff" where it yields detection logic. Next sequential CTIYY-NN. Save to the ROOT of CTI Bulletins\2026.
Keep ATTACKER CLAIMS and VICTIM CONFIRMATIONS strictly apart; carry finished-intelligence hedging verbatim; say which victim is at which stage; say where a story rests on a single outlet. WHERE AN ATTACKER'S CLAIM AND A VICTIM'S STATEMENT AGREE, say that agreement is not independent corroboration. A source with no public URL renders unlinked — NEVER invent one. Where a connector answered a question the reporting could not, cite it: an asset count from our own estate outranks a vendor's guess. Citation numbers must not exceed the sources list. Record the bulletin ID in the register, the log and any Peer row. Do NOT email or distribute.

*** STEP 10 — DAILY ALL-EMPLOYEE AWARENESS POST. RUNS EVERY RUN, WITHOUT BEING ASKED. ***
TWO FORMATS, CHOOSE ONE AND SAY WHY. "genelabs-employee-awareness-blog" is the DEFAULT — 350-450 words, two pages, standfirst, custom illustrations, pull quote, actions card. April: "less wordy, with pictures, more like a blog." Use the long form "genelabs-employee-awareness" only when the topic needs the reader to hold several things at once.
TOPIC: from this run's items where one is employee-actionable, otherwise the top unused PIPELINE row. Never manufacture urgency.
REPETITION: read the ledger BEFORE choosing. No repeat within 90 days unless the tactic fingerprint MATERIALLY changed — new channel, lure, capture mechanism or target population, a control that started or stopped working, or a first confirmed case at GeneLabs.
*** `--channel` IS REQUIRED (`phone call`, `pasted command`, or `none`). Without it the gate INFERS the channel from body text, and inference cannot tell a channel the post is ABOUT from one it RULES OUT — a post saying "no attachment, nothing to paste" was failed for lacking paste instructions. ***
DISCLOSURE: you MAY say "our threat intelligence team is tracking this". You may NOT say what we run, see or found. Reassurance yes, posture no.
IF THE GATE DEMANDS AN INSTRUCTION THAT MAKES NO SENSE FOR THE DAY'S CHANNEL, THE GATE IS WRONG — fix the gate rather than distorting the writing. That has happened three times, always the same defect: a check written against one example document treating a different structure as absence rather than difference.
AFTER PUBLISHING: append the ledger row, confirm the path, deliver with the configured output folder (state the absolute path), report the gate result, record the AWR ID in the STEP 5 entry.

*** STEP 11 — EMPLOYEE AWARENESS TOPIC PIPELINE. RUNS EVERY RUN. ***
Rebuild `<Employee posts>\_awareness_topic_pipeline.md` — a RANKED FORWARD QUEUE, and the input STEP 10 draws on when the scan has nothing employee-actionable.
SOURCES: this run's items first; then a targeted sweep for employee-facing material (FTC and consumer alerts, payroll and HR fraud, deepfake and BEC, consumer breaches); then the connectors LAST, for ranking rather than discovery.
EVERY ROW: a `topic-key`, a tactic fingerprint in the ledger's vocabulary, why it earns its place, the close it should end on, and an explicit ledger check.
TIER THEM (1 ready, 2 needs a hook, 3 fallback rotation) and carry forward unused topics. MARK WHAT IS TAKEN. SPACE THE CHANNELS — two consecutive posts about a malicious web page blur together. CARRY A DISCLOSURE WARNING where a topic's justification is internal. SAY WHERE A TOPIC SHOULD NOT RUN unless written a particular way — `research-collaboration-targeting` is the standing example, because written badly it becomes "be suspicious of your academic collaborators".
STRUCTURAL NOTE worth repeating in the document: connectors are good at what is happening TO GeneLabs and poor at what an ORDINARY EMPLOYEE CAN ACT ON. The web sweep carries this series; connectors rank it. Falcon Identity Protection is the exception, because credential attacks map onto password reuse and unexpected MFA prompts.
Deliver the pipeline with the configured output folder (state the absolute path) alongside the post, every run.

Next available bulletin, hunt and gap IDs are recorded at the end of the dedup log — read them from there rather than assuming.
