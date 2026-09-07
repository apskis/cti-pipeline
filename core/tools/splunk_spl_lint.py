#!/usr/bin/env python3
"""Lint an SPL query against GeneLabs CTI house rules BEFORE it is sent to Splunk.

April, 2026-08-27: *"make sure to never use index without sourcetype or index=*"*, and run
this every time before querying the Splunk MCP.

WHY A LINTER AND NOT JUST A WRITTEN RULE. A rule in a document is checked by whoever
remembers it. This is checked every time. The failure it prevents is not a wrong answer —
it is an unscoped search on an estate that ingests roughly 916 million events a day into
<firewall-index> alone, which is slow, expensive, and the kind of query that gets a CTI analyst's
search privileges reviewed.

EXIT CODES
  0  clean, or advisory notes only
  1  one or more ERRORS — do not run the query

Usage:
  python splunk_spl_lint.py "<spl>"
  python splunk_spl_lint.py --file query.spl
"""
import re, sys

# Generated commands that never touch raw events and therefore cannot carry a sourcetype.
# `tstats` reads the tsidx; `metadata`, `eventcount` and `dbinspect` read index metadata.
METADATA_CMDS = ("tstats", "metadata", "eventcount", "dbinspect", "datamodel", "rest",
                 "mstats", "inputlookup", "makeresults")

TIME_TOKENS = ("earliest=", "latest=", "_index_earliest", "_time>", "_time <", "_time>=")


def _strip(spl):
    """Remove ``` comment blocks and // line comments before matching."""
    s = re.sub(r"```.*?```", " ", spl, flags=re.S)
    s = re.sub(r"^\s*//.*$", " ", s, flags=re.M)
    return s


def lint(spl, has_time_args=False):
    s = _strip(spl)
    low = s.lower()
    errors, warns, notes = [], [], []

    is_metadata = bool(re.match(r"\s*\|\s*(" + "|".join(METADATA_CMDS) + r")\b", low))
    # A search can also pipe into tstats-like commands later; what matters for the sourcetype
    # rule is whether raw events are being retrieved, i.e. whether a bare `index=` appears
    # OUTSIDE a generated metadata command.
    idx_terms = re.findall(r"\bindex\s*=\s*([^\s()\]\|,]+)", low)
    idx_in     = re.findall(r"\bindex\s+in\s*\(([^)]*)\)", low)
    st_terms = re.findall(r"\bsourcetype\s*=\s*([^\s()\]\|,]+)", low)
    st_in    = re.findall(r"\bsourcetype\s+in\s*\(", low)

    # ---- RULE 1: never index=* ------------------------------------------------------
    star = [i for i in idx_terms if i.strip('"\'') in ("*", '"*"')]
    if star:
        if is_metadata:
            notes.append(
                "index=* inside a generated metadata command (" + low.split()[1].rstrip("|") +
                "). This reads the tsidx, not raw events, and is the standard cheap way to "
                "enumerate populated indexes. ALLOWED, but say in the run output why you needed it.")
        else:
            errors.append(
                "index=* over RAW EVENTS. Never do this. Name the indexes you mean, or use "
                "`| tstats count where index=* by index` first to find out which are populated, "
                "then query those by name.")

    # ---- RULE 2: index= must be paired with sourcetype= ------------------------------
    real_idx = [i for i in idx_terms if i.strip('"\'') not in ("*",)] + \
               [t.strip() for grp in idx_in for t in grp.split(",") if t.strip()]
    if real_idx and not is_metadata and not (st_terms or st_in):
        errors.append(
            "index=%s with no sourcetype. Every raw-event search must name BOTH. An index can "
            "hold dozens of sourcetypes — <firewall-index> alone carries <vendor>:traffic, <vendor>:threat and "
            "<vendor>:firewall_cloud — so an index-only search scans data you did not want and "
            "returns fields you cannot rely on."
            % ", ".join(sorted(set(real_idx))[:3]))

    # ---- RULE 3: data model first ----------------------------------------------------
    if real_idx and not is_metadata and "datamodel=" not in low:
        warns.append(
            "Raw index search with no data model attempted. HOUSE RULE IS DATA MODEL FIRST, "
            "raw index as FALLBACK. If the accelerated model genuinely cannot answer this — an "
            "empty model, or a field the CIM does not carry such as HTTP status — say so "
            "explicitly when you report the result, so a reader knows the fallback was reasoned "
            "and not reached for out of habit.")

    # ---- RULE 4: bound the time window ----------------------------------------------
    if not has_time_args and not any(t in low for t in TIME_TOKENS):
        warns.append(
            "No time bound in the query and none passed as arguments. Every CTI search is bound "
            "to a maximum 14 day lookback; an unbounded search on this estate is a denial of "
            "service against your own search head.")

    # ---- RULE 5: cap the result set --------------------------------------------------
    aggregates = re.search(r"\|\s*(stats|tstats|chart|timechart|top|rare)\b", low)
    if aggregates and not re.search(r"\|\s*head\b|\blimit\s*=", low):
        warns.append("Aggregation with no `| head N` or `limit=`. Cap the result set.")

    # ---- RULE 6: known-empty or non-accelerable models --------------------------------
    for bad, why in (
        (r"datamodel\s*=\s*network_resolution", "Network_Resolution.DNS is EMPTY (GAP-03). Use Web.Web."),
        (r"datamodel\s*=\s*network_sessions",   "Network_Sessions is EMPTY (GAP-04)."),
        (r"datamodel\s*=\s*<firewall-app>",       "<firewall-app>.log.traffic is NOT accelerable. Use Network_Traffic.All_Traffic."),
        (r"successful_authentication",          "Authentication.Successful_Authentication is NOT accelerable. Use the root object with action=\"success\"."),
    ):
        if re.search(bad, low):
            errors.append(why + " This returns a false clean negative, not an error.")

    if re.search(r"datamodel\s*=\s*endpoint\.", low) and "summariesonly=true" in low:
        notes.append("Endpoint.* is accelerated to -1w ONLY (GAP-07), so summariesonly=true returns "
                     "at most 7 days regardless of the picker. State the true window when reporting.")
    if re.search(r"datamodel\s*=\s*endpoint\.ports", low):
        warns.append("Endpoint.Ports returned ZERO under a bare groupBy on 2026-08-25 against 1M+ "
                     "events on 2026-08-20 (GAP-08). CONTROL-TEST IT before trusting a zero.")
    if re.search(r"web\.status|web\.http_user_agent", low):
        notes.append("Web.status and Web.http_user_agent render as the literal string 'unknown' "
                     "(GAP-14). For request OUTCOME use the raw iis index with sourcetype=iis, which "
                     "carries sc_status — subject to per-host onboarding (GAP-25).")

    return errors, warns, notes


def report(spl, has_time_args=False, quiet=False):
    e, w, n = lint(spl, has_time_args)
    if not quiet:
        for x in e: print("ERROR  " + x)
        for x in w: print("WARN   " + x)
        for x in n: print("NOTE   " + x)
        if not (e or w or n):
            print("OK     query satisfies the house rules")
    return 1 if e else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] == "--file":
        spl = open(args[1]).read()
    else:
        spl = args[0]
    sys.exit(report(spl, has_time_args="--timed" in args))
