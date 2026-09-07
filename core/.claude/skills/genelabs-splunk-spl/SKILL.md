---
name: "genelabs-splunk-spl"
description: "House rules for every Splunk SPL query GeneLabs CTI runs, and the linter that enforces them. RUN THE LINTER BEFORE EVERY splunk_run_query CALL, and EXECUTE every query before it ships in a document — the linter checks house rules, not syntax. Hard rules: never index= without sourcetype=, never bare index=* over raw events, data model FIRST and raw index only as a reasoned fallback, every search time-bound to 14 days, every aggregation capped. Carries the measured index-to-sourcetype map, the known-empty and non-accelerable data models with their TG-NN gap references, the tstats AND syntax trap, and the traps that have produced false clean negatives. Use whenever writing, reviewing or running SPL, building hunt package queries, or querying the Splunk MCP for any reason."
---

# GeneLabs CTI — Splunk SPL House Rules

**Run the linter before every `splunk_run_query` call. Every time, no exceptions.**

```
python "CTI Deliverables\_tools\splunk_spl_lint.py" "<your SPL>" [--timed]
```

Exit 1 means do not run the query. Pass `--timed` when you are supplying `earliest_time`
and `latest_time` as tool arguments rather than inside the SPL.

**Why a linter and not just this document.** A rule in a document is checked by whoever
remembers it. A linter is checked every time. What it prevents is not a wrong answer — it is
an unscoped search against an estate ingesting roughly 916 million events a day into
`<firewall-index>` alone, which is slow, expensive, and the kind of query that gets a CTI analyst's
search privileges reviewed.

---

## THE LINTER IS NOT A PARSER — read this before trusting an exit code

**Exit 0 means the query obeys April's house rules. It does NOT mean the query runs.**

Measured 2026-09-01, gap **GAP-34**: five of six SPL queries written for a hunt package
returned exit 0 and were rejected by the search head. They would have shipped to an analyst
as work instructions that error on first use, inside a document that had passed every stated
check.

**So there is a sixth hard rule, and it is a process rule:**

### 6. EXECUTE before you ship

Any query that will appear in a delivered document — a hunt package, a priority brief, an
advisory walkthrough — must be **run against live Splunk** before the document is published,
and the result recorded. Extract the queries from the RENDERED file and run those, not the
ones in your draft: that is what catches a rendering or escaping defect too.

This is the mirror image of a false clean negative and is arguably worse for the reader. A
false clean negative gives an analyst a wrong answer; this gives them a work order they
cannot run at all.

### The syntax trap that caused it

```
| tstats ... where earliest=-14d latest=now AND Web.url="*x*" ...     ✘ FATAL
| tstats ... where earliest=-14d latest=now Web.url="*x*" ...         ✔
```

`tstats` where-clause terms are **space-separated with an implicit AND**. A literal `AND`
after a time bound produces:

> `'AND' operator is missing a clause on the left hand side`

It looks completely reasonable, it passes the linter, and it fails every time. The same
applies to `All_Traffic.dest IN (...)` and any other term following `latest=now`.

Grep your own drafts for `latest=now AND` before building anything.

---

## The hard rules

### 1. Never `index=` without `sourcetype=`

An index holds many sourcetypes with different fields. `<firewall-index>` alone carries
`<vendor>:traffic` (~500M/day), `<vendor>:threat` (~300M/day) and `<vendor>:firewall_cloud` (~25M/day) — and
`<vendor>:traffic` has no `url` field while `<vendor>:threat` does. An index-only search scans data you
did not want and returns fields you cannot rely on.

```
index=<web-index> sourcetype=<web-sourcetype> cs_uri_stem="*_layouts*"          ✔
index=<web-index> cs_uri_stem="*_layouts*"                          ✘ ERROR
```

### 2. Never bare `index=*` over raw events

Name the indexes you mean.

**The one narrow exception, and it is deliberate:** `| tstats count where index=* by index`
inside a *generated metadata command* reads the tsidx, not raw events. It is the standard
cheap way to discover which indexes are populated, and it is the query that on 2026-08-27
overturned a wrong conclusion in two issued documents. The linter allows it with a NOTE and
asks you to say why you needed it. **If that exception is unwanted, remove `tstats` from
`METADATA_CMDS` in the linter — it is one line.**

### 3. Data model FIRST, raw index as a reasoned fallback

Run the accelerated model first: it is fast and consistent. **If it returns ZERO, do not
record a clean result** — re-run against the raw index before concluding anything.

**A data model is a mapping over the data, not the data.** On 2026-08-27 a CIM field
rendering as the literal string `unknown` was recorded as "the outcome is unanswerable",
shipped in two documents, and was wrong: the raw index carried the field all along. When you
do fall back, **say so and say why**, so a reader knows it was reasoned rather than habit.

### 4. Bind every search to a maximum 14 day lookback

Either in the SPL or as tool arguments. An unbounded search here is a denial of service
against your own search head.

### 5. Cap every aggregation

`| head N` or `limit=`. No exceptions.

### 6. Execute before you ship

See above. GAP-34.

---

## Writing a search whose ZERO is unambiguous

A search that returns nothing leaves the reader unable to tell "no matches" from "the search
was broken". Three techniques, all measured working on 2026-09-01:

**Aggregate without a `by` clause to guarantee one row.**
`| tstats count as Seen from datamodel=Web where ...` with no `by` returns a single row even
at zero. With a `by` clause it returns nothing at all — which is what silently dropped a
branch of a two-part check and made a two-answer search look like a one-answer search.

**Guard with `appendpipe` where you need the `by`.**
```
| appendpipe [ stats count as n | where n=0
             | eval Server="NO MATCHES IN 14 DAYS", Flows=0 | fields Server Flows ]
```

**End on an `Answer` column that states the finding in words**, not a count to interpret.
And write that eval so it **cannot assert a conclusion the data does not support** — prefer a
classification the analyst reads over a verdict the search declares. A search that produces a
plausible WRONG answer is worse than one that produces none. On 2026-09-01 an `Answer` eval
reading `"YES - a PaperCut service was reached"` fired on 41 flows that turned out to be
destination-port coincidence against unrelated external addresses.

**Rename CIM fields to plain English** in anything a non-CTI reader will run —
`All_Traffic.dest` as `Server`, `dc(All_Traffic.src)` as `Clients`. A column header of
`All_Traffic.dest` leaks our data model onto someone else's screen.

---

## Index to sourcetype map — MEASURE THIS IN YOUR OWN ENVIRONMENT

**This table is a template. The values below are illustrative, not measured.**
Every environment indexes differently, and a borrowed map is worse than no map
because it reads as authoritative. Run the discovery searches in
`reference/discovery.md`, then replace every row here with what you actually
observe. Date each row so a stale claim is visible as stale.

| Index | Sourcetype | Carries | Measured on |
| --- | --- | --- | --- |
| `<firewall-index>` | `<vendor>:traffic` | Session records, allow and block action. Confirm whether a URL field exists. | `<date>` |
| `<web-index>` | `<web-sourcetype>` | Request level fields: status, URI stem, client address, method. | `<date>` |
| `<windows-index>` | `<windows-sourcetype>` | Windows security and system events. | `<date>` |
| `<linux-index>` | `<linux-sourcetype>` | Linux audit and syslog. | `<date>` |
| `<identity-index>` | `<identity-sourcetype>` | Identity governance and access events. | `<date>` |
| `<scm-index>` | `<scm-sourcetype>` | Source control audit events. | `<date>` |

---

## Data models — MEASURE, then override the bundled reference

**This table is a template.** The bundled Splunk CIM documentation describes what a
data model is *supposed* to contain. What it actually contains in your environment
is an empirical question, and the answer changes as feeds are added and removed.

The failure this table exists to prevent: a data model that is empty, partially
accelerated, or sourced from one platform only returns **zero results with no error**.
A zero that means "the model cannot see this" is indistinguishable from a zero that
means "this is not happening" unless you have measured the difference.

Record each finding against your own gap register and give it an id, so a query can
cite the reason it avoids a model rather than silently working around it.

| Model | What you measured | Do this instead | Gap id |
| --- | --- | --- | --- |
| `<model.dataset>` | Empty, partially populated, or accelerated over a shorter window than the picker suggests | The fallback that does work | `<GAP-NN>` |
| `<model.field>` | Field carries a different type or literal than the CIM reference claims | Derive it from a field you have verified | `<GAP-NN>` |
| `<model.dataset>` | Sourced from one platform only, therefore blind to the others | Name the blindness in the finding, use a raw index for the rest | `<GAP-NN>` |

**Control test every model before you build on it.** Run the aggregation you intend
to use against a window and a host where you already know the answer. If the known
positive does not come back, the model cannot see it, and every later zero from that
model is uninterpretable.

---

## Always control-test a zero

An empty accelerated model and a clean environment look identical, and the API
free-text-matches malformed SPL and returns HTTP 200 with no rows. **Run a bare aggregation
against the same model or index first.** A zero is only evidence when it sits beside a
control that returned data.

**Run the control LAST within a documented walkthrough, and say why.** The two zeros are
meaningless until the control proves the source returns data at all — putting it last is what
makes an analyst read them in the right order.

**A zero beside a very large control can mean the opposite of how it reads.** Measured twice,
31 Aug and 1 Sep (GAP-27): an internet-reachable AWS-hosted GeneLabs endpoint returned 0
events from both `Network_Traffic` and raw `<vendor>:traffic` over 14 days, against controls above
ten billion. That is not a quiet host. It means the perimeter is not on that path at all, so
nothing could ever alert on it.

## Read the rows, do not count them

A filter can match the right string on the wrong thing, and at a genomics company this bites
harder than elsewhere:

- `*nuclei*` returns a fintech domain, a biotech domain, a SharePoint deck about a nuclei
  repeat assay and an SAP search for "nuclei extraction". **"Nuclei" is a laboratory word at
  GeneLabs before it is a security tool.**
- `*UniFi*` returns 390 rows of Waters UNIFI chromatography software and zero Ubiquiti.
- `*fastlink*` returns a bank hostname. `?qtproxycall=` is a scanner's own parameter, not
  actor infrastructure.
- `*Rails*` returns Chrome "Cursor **Trails**" extensions on a substring.

Match a specific artefact, scope to external sources, and read the hits before reporting a
count.

## Two count patterns that look alike and are not

- **Ephemeral port coincidence.** Two unrelated ports reporting an IDENTICAL
  distinct-destination count is ephemeral allocation, not a service. This produced the entire
  false signal in TH26-04A and TH26-13. The same shape appears on the destination side: many
  distinct destinations, one client each, a handful of flows apiece, on a port that happens to
  fall in a commonly reused range — that is coincidence, not a discovered server.
- **A scanner's fixed probe budget.** One source hitting many destinations on ONE port with
  an identical per-target count is a real finding.

Say which one you are looking at.

## Process searches

Never write an unscoped fleet-wide `ProcessRollup2`-equivalent search. Fleet process volume
is roughly 3.8M events per 15 minutes. Lead with network or DNS events to build a candidate
host list, then scope process searches to it. Exclude the top process-volume hosts from
fleet-wide aggregations — measured 2026-08-27: `<host-a>`, `<host-b>`,
`<host-c>`.

## When you report a result

State the data source, the window, and the blind spot. "Falcon Discover shows 0" is not a
finding; "0 of 278,507 sensored applications, and this is an appliance which carries no
sensor (GAP-09)" is. **A measured zero on something the tool cannot see is not a clean
result.**

## Extending the linter

Add a rule when a mistake has actually happened, not when one is imagined, and put the
evidence in the message. Every rule in there traces to a specific wrong answer: the false
clean negatives to GAP-03, GAP-04 and GAP-08; the sourcetype rule to an `index=<web-index>` query that
shipped in a hunt package on 2026-08-27; the data model rule to a conclusion that was
overturned the same day.

**Outstanding, from GAP-34 (2026-09-01):** add a rule rejecting `latest=now AND` and the
equivalent `earliest=... AND` forms inside a `tstats` where clause. It is a cheap regex and
it closes the one case where a clean exit code has shipped a broken query. **But do not treat
that fix as making rule 6 unnecessary** — the linter can never be a parser, and the only
reliable check is running the query.

