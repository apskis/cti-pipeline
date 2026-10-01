# Bulletin scan: connector rules

Read this only when the session has the matching tools (splunk_, falcon_, rapid7_, tq_,
intel471_, claroty_). The cloud POC enables nvd, enrich and ics only, so a normal cloud
run never needs it. Text below is moved verbatim from `task.md`.

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

CONNECTOR CATALOGUE ENTRIES (moved from the main task's MCP CONNECTORS block):
WORKING:
  falcon_search_applications — THE PRODUCT-TO-ASSET JOIN, licensed. Total moves (274,550 → 278,720 → 278,507 across three days) so read `pagination.total` in your own run. NOT a CVE-to-asset join. Sees SENSORED HOSTS ONLY (GAP-09) — corroborate with Splunk.
  falcon_search_hosts — sensor state, RFM, policies, RTR, criticality. The way to answer "does this asset have working EDR".
  falcon_search_detections — use INSTEAD OF a CQL DetectionSummaryEvent query, which returns a false clean negative (GAP-06). Qualify with product:'epp'. May return a transient 401; retry succeeds.
  rapid7_assets / rapid7_vulnerabilities — IT inventory; CANNOT filter by CVE (GAP-02).
  tq_search_indicator, tq_recent_indicators, tq_events · intel471_reports, intel471_alerts
  splunk_run_query — see the SPL rules above.
  falcon_search_recon_notifications — returns 0 because NO recon rules are configured. A CONFIGURATION gap (GAP-17), never a clean result.

BROKEN, LOUD, SAFE:
  claroty_devices and claroty_vulnerabilities — BOTH HTTP 422; the wrapper requests fields xDome no longer accepts. Control-tested three ways. GAP-23. CONSEQUENCE: the OT/IoT leg CANNOT be scoped. Say "OT could not be assessed", never "no OT exposure".
  falcon_search_vulnerabilities — Spotlight, HTTP 403. GAP-01.

PATCH STATE: no automated PER-CVE exposure answer exists; never write a per-CVE exposure count. But falcon_search_applications gives a PRODUCT join and splunk_run_query reaches the unsensored estate. Run BOTH before writing "possible exposure, verify" — that phrase is for what you could not measure, not what you did not try.

FINISHED INTELLIGENCE — for every named actor or campaign run intel471_reports. Where it disputes or qualifies press reporting, SAY SO and prefer its assessment, carrying hedging words verbatim. Cross-reference actors against the log so a recurring actor reads as continuing activity. THE ABSENCE OF A REPORT IS INFORMATION: where a breach ALERT exists but no finished report does, or where a government disclosure names an actor Intel 471 holds nothing on, say so — it speaks to the coverage GeneLabs buys.

PEER CHECK SOURCE (1), INTEL 471 BREACH ALERTS:
(1) INTEL 471 BREACH ALERTS — every run, filtered to the window then to "Health care equipment and technology", "Health care providers and services industry", "Pharmaceuticals, biotechnology and life sciences industry".
  - Equipment/technology or pharma/biotech alerts are strong PEER INCIDENT candidates and get a STEP 5B row.
  - THE PROVIDERS INDUSTRY IS DIFFERENT. Clinics, dental practices and single hospitals are not peers — carry them in the BACKGROUND RATE line only. Promote one only if its actor recurs against our own two industries.
  - CARRY THE CONFIDENCE FIELD. Never upgrade "possibly compromised" to a confirmed breach.
  - DISTINGUISH THE STAGE. Data POSTED is not LISTED WITH A DEADLINE; the deadline stage is where claims are least reliable.
  - CROSS-REFERENCE THE ACTOR. A covered actor is continuing activity and may warrant REVISING the existing bulletin.
  - RECORD THE BACKGROUND RATE as one line. The base rate stops any single alert being over-read.

*** EIGHTH SOURCE — THREATQ, FOR INDICATORS. *** Check every IOC before treating it as novel. Already in ThreatQ changes "add as a custom IOC" to "already covered, hunt the behaviour". NOTE THE INVERSE: an indicator IN ThreatQ whose traffic was still ALLOWED is a BLOCKLIST ENFORCEMENT GAP and its own finding — GAP-22, now at THREE instances (most recently 198.51.100.7, held since April, allowed 1,318 times in 14 days), so treat it as a confirmed systemic pipeline problem. AND THE CONVERSE: where NONE of a published indicator set is in ThreatQ or Intel 471, the intelligence is genuinely new to GeneLabs and not covered by any feed.

*** ASSET SCOPING BEFORE THE HYPOTHESIS: falcon_search_applications for "do we run this"; falcon_search_hosts for "does it have working EDR"; splunk_run_query for the unsensored estate with a BARE CONTROL first; claroty BOTH DOWN (GAP-23) so say "OT could not be assessed", never "no OT exposure". ***
