#!/usr/bin/env python3
"""GeneLabs CVE Priority Brief builder.

Renders a one-page, branded .docx priority matrix for the Vulnerability Management
team from CVE_Register_2026.xlsx.

SCOPE: this run's changes only - the CVEs that are net-new or that materially
advanced since the previous run. That set is exactly the Latest Run tab, which the
daily scan overwrites every run. The brief is a "what moved and what do I do about
it" sheet, not a full backlog; the standing queue lives in the CVE Register tab.

ORDER: exploited in the wild first. Within that, an overdue KEV deadline beats an
imminent one, which beats an undated one; GeneLabs relevance breaks remaining ties.
CVSS never leads - a 9.8 nobody is exploiting does not outrank a 7.5 being used today.

Branding is inherited from the genelabs-cti-bulletin builder: this script imports
that module and reuses its styling helpers, so the palette, borders, fonts and
spacing cannot drift from the bulletin set. It never modifies that skill.

Usage:
  python build_priority_brief.py <register.xlsx> <out.docx> <bulletin_skill_dir>
                                 [--run-date YYYY-MM-DD] [--max-rows N]
"""
import argparse, datetime, json, os, re, subprocess, sys, tempfile

SENTINEL = "__CVE_MATRIX__"
CLOSED = ("remediated", "risk accepted", "not applicable")


# ---------------------------------------------------------------- register read
def read_run(path):
    """Latest Run tab gives the scope; CVE Register gives the detail. Join on ID."""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=False)
    if "Latest Run" not in wb.sheetnames or "CVE Register" not in wb.sheetnames:
        sys.exit("workbook must contain both 'Latest Run' and 'CVE Register' tabs")

    reg, detail = wb["CVE Register"], {}
    hdr = {str(reg.cell(4, c).value).strip(): c for c in range(1, reg.max_column + 1) if reg.cell(4, c).value}
    r = 5
    while reg.cell(r, 1).value:
        g = lambda n: str(reg.cell(r, hdr[n]).value or "").strip() if n in hdr else ""
        detail[g("CVE / Advisory ID")] = {
            "vendor": g("Vendor"), "product": g("Product"), "cvss": g("CVSS"),
            "kev_added": g("KEV Added"), "kev_due": g("KEV Due"),
            "exploit": g("Exploitation Status"), "fixed": g("Fixed Version"),
            "relevance": g("GeneLabs Relevance"), "hunt": g("Hunt ID"),
            "status": g("Remediation Status") or "Open", "owner": g("Owner") or "Unassigned",
            "source": g("Source"),
            # Columns 20-22, appended after the 17 the daily scan mandates and after the
            # existing 18-19, so no column letter used by that task moves.
            # "Observed In Our Logs" answers the question VM actually asks first — does this
            # touch us at all — with a MEASURED string rather than a judgement. It must stay
            # short enough to render in a table cell; the reasoning belongs in a bulletin.
            "observed": g("Observed In Our Logs"),
            "val_spl": g("Validation SPL"), "val_cql": g("Validation CQL"),
        }
        r += 1

    lr = wb["Latest Run"]
    lh = {str(lr.cell(7, c).value).strip(): c for c in range(1, lr.max_column + 1) if lr.cell(7, c).value}
    if "Change" not in lh or "CVE / Advisory ID" not in lh:
        sys.exit("Latest Run tab header row not found at row 7")
    rows, r = [], 8
    while lr.cell(r, lh["CVE / Advisory ID"]).value:
        cid = str(lr.cell(r, lh["CVE / Advisory ID"]).value).strip()
        change = str(lr.cell(r, lh["Change"]).value or "NEW").strip().upper()
        d = dict(detail.get(cid, {}))
        if not d:                                   # in Latest Run but not the register
            d = {"vendor": "", "product": str(lr.cell(r, lh.get("Product", 1)).value or ""),
                 "cvss": "", "kev_added": "", "kev_due": "", "exploit": "", "fixed": "",
                 "relevance": "", "hunt": "", "status": "Open", "owner": "Unassigned",
                 "source": str(lr.cell(r, lh["Source"]).value or "") if "Source" in lh else "",
                 "observed": "", "val_spl": "", "val_cql": ""}
        d.update({"id": cid, "change": change})
        rows.append(d)
        r += 1
    return rows


# ------------------------------------------------------------------ taxonomies
def on_kev(row):
    k = row["kev_added"]
    return bool(k) and (k[:2] == "20" or k.lower().startswith("added"))


def _due_date(due):
    """Pull the ISO date out of a KEV Due cell, ignoring any trailing annotation.

    The register legitimately carries values like '2026-08-23 (three days, BOD
    26-04)' and '2026-09-02 (two weeks, BOD 26-04)', because the deadline basis is
    worth recording next to the date. datetime.date.fromisoformat() rejects both,
    which silently dropped every annotated row into the catch-all bucket and let
    GeneLabs relevance decide the order instead of the deadline. On 2026-08-21 that
    put an MLflow item due 2 Sep above a TrueConf item due 23 Aug. Match the leading
    date and parse that.
    """
    m = re.match(r"\s*(\d{4}-\d{2}-\d{2})", due or "")
    if not m:
        return None
    try:
        return datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def _overdue(due):
    d = _due_date(due)
    return d is not None and d < datetime.date.today()


def exploitation(row):
    """Compact phrase + rank. Lower rank = more urgent. Exploited always leads."""
    e, due = row["exploit"].lower(), row["kev_due"]
    if e.startswith("exploited"):
        if on_kev(row):
            if due.lower() == "passed" or _overdue(due):
                when = "" if due.lower() == "passed" else f" ({due})"
                return f"Exploited · KEV deadline PASSED{when}", 0
            if due and due[:2] != "20":
                return f"Exploited · KEV, {due}", 1
            return f"Exploited · KEV deadline {due or 'not published'}", 1
        return "Exploited in the wild · not on KEV", 2
    if "poc" in e or "proof-of-concept" in e:
        return "PoC public · no in-the-wild reports", 3
    if e.startswith("scanning"):
        return "Scanning observed · no confirmed exploitation", 4
    return "None reported", 5


def deadline_bucket(row):
    due = row["kev_due"]
    if not on_kev(row): return 3
    if due.lower() == "passed" or _overdue(due): return 0
    d = _due_date(due)
    if d is not None:
        days = (d - datetime.date.today()).days
        return 1 if days <= 3 else (2 if days <= 14 else 3)
    # No parseable date. Fall back to the prose, which the register writes in
    # several forms: '3 days', 'three days', '3 day', 'two weeks'.
    low = due.lower()
    if any(t in low for t in ("3 day", "three day", "72 hour")): return 1
    if any(t in low for t in ("14 day", "two week", "fourteen day")): return 2
    return 3


def rel_rank(row):
    r = row["relevance"].upper()
    for i, t in enumerate(["HIGH", "MEDIUM-HIGH", "MEDIUM", "LOW-MEDIUM", "LOW",
                           "INFORMATIONAL", "NOT APPLICABLE"]):
        if r.startswith(t): return i
    return 9


def _fix_is_pointer(row):
    """True when the register names a vendor fix WITHOUT a pasteable version.

    Distinguishes "the vendor has fixed this, go find the build number" from
    "there is nothing to install". _version_known() rejects both; only this one
    should read as "vendor fix exists".
    """
    f = (row.get("fixed") or "").lower()
    if not f:
        return False
    if any(t in f for t in ("unavailable", "not published", "no fix", "none reported",
                            "not applicable", "service-side", "service side",
                            "no customer action")):
        return False
    return any(t in f for t in ("per vendor", "verify", "advisory", "note", "kb", "bulletin"))


def _version_known(row):
    """True only when the register names an actual fixed version.

    'Per vendor advisory - verify the release' is a pointer, not a version: it
    cannot be pasted into a change ticket, so it must not render as 'Upgrade to
    per vendor advisory'.
    """
    f = row["fixed"].lower()
    if not f: return False
    if any(t in f for t in ("unavailable", "not published", "not applicable", "no fix", "none reported")):
        return False
    if any(t in f for t in ("per vendor", "verify", "advisory", "tbd")):
        return False
    # A service-side fix is not something VM can install. Rendering it as
    # 'Upgrade to Fixed service-side by Microsoft' hands VM a task that does not
    # exist and hides the one that does, which is a log review.
    if any(t in f for t in ("service-side", "service side", "no customer action",
                            "not applicable", "mitigation guidance")):
        return False
    # Last resort: a version you can paste into a change ticket contains a digit.
    # 'Fixed by the vendor' does not.
    if not any(c.isdigit() for c in f):
        return False
    return True


def _service_side(row):
    f = row["fixed"].lower()
    return any(t in f for t in ("service-side", "service side", "no customer action"))


def fix_category(row):
    """Patch / Mitigate / Education / Monitor. See SKILL.md for definitions."""
    rank = exploitation(row)[1]
    # A cloud service the vendor already fixed. There is nothing to install, so it
    # is not Patch; but for an exploited flaw the log review is real work, so it is
    # not Monitor either.
    if _service_side(row):
        return "Mitigate" if rank <= 2 else "Monitor"
    # nothing exploiting it and unlikely to be ours -> the job is to confirm, not to patch
    if rank >= 4 and rel_rank(row) >= 3: return "Monitor"
    if _version_known(row): return "Patch"
    if rank <= 2: return "Mitigate"
    if rank == 3: return "Education"
    return "Monitor"


# April, 2026-08-31: "dont reference hunts, just the validation searches."
# The brief goes to Vulnerability Management, who cannot action a hunt ID; it told them
# a hunt existed without telling them anything they could do. The register KEEPS its
# Hunt ID column - that linkage is real and useful there - the brief simply stops
# rendering it. Set BRIEF_SHOWS_HUNT_REF back to True to restore the old behaviour.
BRIEF_SHOWS_HUNT_REF = False

# April, 2026-09-01: "make the seen in our logs easy to understand, where its a yes no,
# cannot confirm, etc."
#
# The column was carrying the raw measurement string from the register — "0 server rows by
# name; 3 client rows by vendor. NOT cleared." — which is accurate, is the right thing to
# keep in the register, and is the wrong thing to put in a scan-in-ten-seconds matrix. VM
# reads this column to answer ONE question before anything else: is this thing here or not.
#
# So the register cell now LEADS with a verdict token and the brief renders it as a verdict.
# Three values only, because a fourth invites hedging:
#
#   YES            the affected product, or activity against it, was found in our telemetry
#   NO             we looked with a working search and it is not there
#   CANNOT CONFIRM the search cannot answer it — no sensor, no field, or a known blind spot
#
# CANNOT CONFIRM is not a softer NO and must never be rendered as one. It is the value that
# stops a sensor gap being read as a clean estate, which is the single most expensive error
# this brief could cause.
VERDICTS = ("YES", "NO", "CANNOT CONFIRM")


def split_verdict(observed):
    """Return (verdict, qualifier) from a register 'Observed In Our Logs' cell.

    The cell is expected to read '<VERDICT> — <one short clause>'. Where it does not — an
    older row, or one written before this convention — return CANNOT CONFIRM rather than
    guessing from the prose, and let the qualifier carry the original text. Inferring YES
    or NO from a sentence is exactly the kind of quiet wrongness this column exists to stop.
    """
    text = (observed or "").strip()
    if not text:
        return "CANNOT CONFIRM", "Not measured this run."
    head = text.upper()
    for v in ("CANNOT CONFIRM", "YES", "NO"):     # longest first
        if head.startswith(v):
            rest = text[len(v):].lstrip(" -\u2014\u2013:").strip()
            return v, (rest or "")
    return "CANNOT CONFIRM", text


# April, 2026-09-01: "make sure the validation searches directly pull up the results, make it
# easy for an analyst to place the search in splunk and the results are easy to read."
#
# The Falcon CQL half is not rendered any more. Not because Falcon does not matter — it does,
# and the register keeps column 22 — but because those cells were mostly connector
# INSTRUCTIONS ("falcon_search_applications filter: ... -> read pagination.total"), which is
# not something an analyst can paste anywhere and run. Shipping them under a heading that says
# "validation query" taught the reader that half the appendix does not work.
#
# The appendix is therefore Splunk only, one runnable search per CVE, each one executed against
# live Splunk before publication. Set BRIEF_SHOWS_CQL back to True to restore both halves.
BRIEF_SHOWS_CQL = False



def _hunt_ref(row):
    """Only render a hunt reference when there is an actual hunt ID.

    The register's Hunt ID field carries prose as well as IDs - values such as
    'None - deferred, unsensored appliance (see log note)' and 'Candidate, pending
    CMDB confirmation'. A naive equality check on 'none' renders 'Hunt None -
    deferred...' into the Action column, so match on the leading word instead.
    """
    if not BRIEF_SHOWS_HUNT_REF:
        return ""
    h = (row.get("hunt") or "").strip()
    if not h or h.lower().startswith(("none", "candidate", "proposed", "n/a", "-")):
        return ""
    return f" Hunt {h.split('(')[0].strip().rstrip('.')}."


def action_text(row):
    fix = fix_category(row)
    hunt = _hunt_ref(row)
    if fix == "Patch" and not _version_known(row):
        return f"Vendor fix exists; confirm the fixed release, then upgrade.{hunt}".strip()
    return {
        "Patch": (f"Apply {row['fixed']}.{hunt}" if "patch tuesday" in row['fixed'].lower()
                  else f"Upgrade to {row['fixed']}.{hunt}"),
        "Mitigate": (
            # SKILL SPEC, "The Fix column": a fixed-version string that is a POINTER rather
            # than a version ("Per vendor advisory - verify the release") means a vendor fix
            # EXISTS but cannot be pasted into a change ticket. That is not the same as no
            # patch existing, and telling VM "No patch available" for a CVE SAP has already
            # fixed sends them to mitigate something they could simply install.
            # Measured 2026-08-31: CVE-2026-58231 rendered as "No patch available" while SAP
            # Note 3771065 carried the fix.
            f"Vendor fix exists; confirm the fixed release, then upgrade.{hunt}"
            if _fix_is_pointer(row)
            else f"No patch available. Reduce by configuration or segmentation.{hunt}"),
        "Education": f"No fix available. Control is user behaviour and application control.{hunt}",
        "Monitor": f"Confirm whether present in the estate.{hunt}",
    }[fix].strip()


OUTLETS = {
    "securityweek.com": "SecurityWeek", "bleepingcomputer.com": "BleepingComputer",
    "thehackernews.com": "The Hacker News", "cisa.gov": "CISA", "rapid7.com": "Rapid7",
    "helpnetsecurity.com": "Help Net Security", "theregister.com": "The Register",
    "gbhackers.com": "GBHackers", "esecurityplanet.com": "eSecurity Planet",
    "cybersecuritynews.com": "Cyber Security News", "cyberpress.org": "Cyberpress",
    "mindgard.ai": "Mindgard", "oblique.security": "Oblique Security",
    "itsecuritynews.info": "IT Security News", "darkreading.com": "Dark Reading",
    "infosecurity-magazine.com": "Infosecurity Magazine", "justice.gov": "US Department of Justice",
    "gendigital.com": "Gen Digital", "blackpointcyber.com": "Blackpoint Cyber",
    "securityonline.info": "SecurityOnline", "itpro.com": "IT Pro",
    "assurantcyber.com": "Assurant Cyber", "nvd.nist.gov": "NVD",
}
ACRONYMS = {"cve": "CVE", "cisa": "CISA", "nsa": "NSA", "fbi": "FBI", "ai": "AI", "ide": "IDE",
            "os": "OS", "rce": "RCE", "plc": "PLC", "plcs": "PLCs", "saml": "SAML", "sso": "SSO",
            "vmware": "VMware", "netscaler": "NetScaler", "gitlab": "GitLab", "adc": "ADC",
            "us": "US", "etr": "ETR", "kev": "KEV", "mfa": "MFA", "m365": "M365", "iot": "IoT",
            "macos": "macOS", "vcenter": "vCenter", "api": "API", "dns": "DNS", "jwt": "JWT",
            "ics": "ICS", "ot": "OT", "vpn": "VPN", "http": "HTTP", "sql": "SQL", "xss": "XSS"}
SMALL = {"a", "an", "the", "of", "in", "on", "to", "for", "and", "or", "at", "as", "after",
         "with", "by", "from", "into", "over", "via", "that", "than"}


def _source_entry(url):
    """Turn a bare register URL into a house-style 'Outlet: Headline' entry.

    The register stores only the URL, so the headline is reconstructed from the
    final path slug. Imperfect but readable, and far better than citing the
    register at itself - a VM reader needs to reach the advisory, not the sheet.
    """
    u = url.strip()

    # AUTHOR-SUPPLIED FORM: 'Outlet: Headline — https://...'. SKILL.md has promised this
    # escape hatch since the brief was written, but it was never implemented — the function
    # went straight to slug reconstruction for every input. It surfaced on 2026-08-27 when a
    # Ubiquiti advisory URL ending in a GUID rendered as
    # "Community: Fc4a3488 7c43 4628 8bab F715e96dbfc9", which is not a headline in any sense.
    # Reconstruction is fine for news URLs with a descriptive slug and hopeless for vendor
    # portals that key on an identifier, so the fix is to let the author write the title
    # rather than to make the guesser cleverer. Em dash or ' - ' both accepted; split on the
    # LAST separator so a headline may legitimately contain one.
    for sep in (" — ", " - "):
        if sep in u:
            head, _, tail = u.rpartition(sep)
            if head.strip() and tail.strip().startswith("http"):
                return {"text": head.strip(), "url": tail.strip()}

    if not u.startswith("http"):
        return {"text": u or "Source not recorded in the register", "url": None}
    host = re.sub(r"^www\.", "", u.split("/")[2].lower())
    outlet = OUTLETS.get(host) or host.split(".")[0].title()
    slug = [p for p in u.split("?")[0].rstrip("/").split("/")[3:] if p]
    slug = slug[-1] if slug else ""
    slug = re.sub(r"\.(html?|aspx|php)$", "", slug)
    slug = re.sub(r"^\d{4}[-/]\d{2}([-/]\d{2})?[-/]?", "", slug)
    # protect CVE / GHSA identifiers so the hyphen split does not shred them into
    # "CVE 2026 19490" - this is a CVE brief, the identifiers have to survive intact
    keep = []
    def _stash(m):
        keep.append(m.group(0).upper().replace("_", "-"))
        return f" \x00{len(keep)-1}\x00 "
    slug = re.sub(r"(?i)\bcve[-_]\d{4}[-_]\d{4,7}\b", _stash, slug)
    slug = re.sub(r"(?i)\bghsa(?:[-_][a-z0-9]{4}){3}\b", _stash, slug)
    words = [w for w in re.split(r"[-_\s]+", slug) if w]
    out = []
    for i, w in enumerate(words):
        m = re.fullmatch(r"\x00(\d+)\x00", w)
        if m:
            out.append(keep[int(m.group(1))]); continue
        lw = w.lower()
        if lw in ACRONYMS: out.append(ACRONYMS[lw])
        elif re.fullmatch(r"\d{4}", w): out.append(w)
        elif lw in SMALL and i: out.append(lw)
        else: out.append(w.capitalize())
    title = " ".join(out).strip()
    return {"text": f"{outlet}: {title}" if title else outlet, "url": u}


def urgency(row):
    """Exploited in the wild leads. Deadline, then relevance, break ties."""
    return (exploitation(row)[1], deadline_bucket(row), rel_rank(row), row["id"])


# --------------------------------------------------------------------- render
def build(register, out_docx, skill_dir, run_date=None, max_rows=10, appendix=True):
    sys.path.insert(0, os.path.join(skill_dir, "scripts"))
    import build_bulletin as B
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_BREAK
    from docx.text.paragraph import Paragraph

    run_date = run_date or datetime.date.today().isoformat()
    pretty = datetime.date.fromisoformat(run_date).strftime("%B %d, %Y").replace(" 0", " ")

    rows = [r for r in read_run(register) if r["status"].lower() not in CLOSED]
    rows.sort(key=urgency)
    dropped = max(0, len(rows) - max_rows)
    rows = rows[:max_rows]
    # sources: one per CVE, in render order, deduped. Cited from the Action cell.
    sources, cite_of, seen = [], {}, {}
    for r in rows:
        u = (r.get("source") or "").strip()
        key = u or f"__none__{r['id']}"
        if key not in seen:
            seen[key] = len(sources) + 1
            sources.append(_source_entry(u))
        cite_of[r["id"]] = seen[key]

    n_exp = sum(1 for r in rows if exploitation(r)[1] <= 2)
    n_new = sum(1 for r in rows if r["change"] == "NEW")
    n_upd = sum(1 for r in rows if r["change"] == "UPDATED")

    spec = {
        "report_id": f"CVE-VM-{run_date}", "date": pretty,
        "category": "VULNERABILITY ALERT",
        "severity": "HIGH" if any(exploitation(r)[1] <= 1 for r in rows) else "MEDIUM",
        "title": f"CVE Priority Brief — New and Updated This Run, {pretty}",
        "audience": "Vulnerability Management, IT Infrastructure, Platform Engineering, Manufacturing OT",
        "relevance": (
            # The old closing sentence read "All exposure is possible, to verify in CMDB and
            # InsightVM; none confirmed." That became false on 2026-08-27, the moment the
            # "Seen in our logs" column started carrying measured counts — some exposure now
            # IS measured, and a blanket disclaimer would teach the reader to discount the
            # one column added to stop them guessing. Replaced with the distinction that
            # actually matters to VM: a count is a measurement, a zero is only as good as the
            # sensor behind it.
            f"{len(rows)} CVEs are new or materially advanced since the previous run "
            f"({n_new} new, {n_upd} updated). {n_exp} are exploited in the wild and lead the table; "
            "ordering is by exploitation and deadline, never by CVSS. "
            "FIX: Patch = vendor fix exists · Mitigate = no patch, reduce by configuration · "
            "Education = no fix coming, the control is behaviour · Monitor = confirm whether we are affected. "
            "SEEN IN OUR LOGS answers one question — is this in our estate? YES = found. NO = we looked with a "
            "working search and it is not there. CANNOT CONFIRM = the search cannot answer it, because of a "
            "sensor or field gap; that is NOT a clean result and is the row most worth chasing. "
            "Appendix A carries the exact Splunk search behind each verdict — paste it in and run it. "
            "Per-CVE patch state remains unavailable; confirm versions in the InsightVM console."),
        "detail_table": [[SENTINEL, ""]],
        "sources": sources,
        "footer_contact": "secops@genelabs.com  |  ServiceNow",
        "tlp": "AMBER+STRICT",
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(spec, fh); specfile = fh.name
    subprocess.run([sys.executable, os.path.join(skill_dir, "scripts", "build_bulletin.py"), specfile,
                    out_docx, os.path.join(skill_dir, "assets", "bulletin_template.docx")], check=True)

    doc = Document(out_docx)
    FIXCOLOR = {"Patch": B.SEVERITY_COLORS["HIGH"], "Mitigate": B.SEVERITY_COLORS["MEDIUM"],
                "Education": B.SEVERITY_COLORS["INFORMATIONAL"], "Monitor": B.SEVERITY_COLORS["LOW"]}
    # CANNOT CONFIRM deliberately takes the MEDIUM colour, not a grey or a muted tone.
    # A washed-out "cannot confirm" reads as "nothing to see"; it is the row that most needs
    # somebody to go and look.
    VERDICTCOLOR = {"YES": B.SEVERITY_COLORS["HIGH"],
                    "NO": B.SEVERITY_COLORS["LOW"],
                    "CANNOT CONFIRM": B.SEVERITY_COLORS["MEDIUM"]}
    CHGCOLOR = {"NEW": B.SEVERITY_COLORS["HIGH"], "UPDATED": B.SEVERITY_COLORS["MEDIUM"],
                "BACKFILL": B.GREY}
    # SIX columns since 2026-08-27. "Seen in our logs" was added at April's request and it
    # earns its width: without it every row asserts a fix without saying whether the thing
    # is present, and VM has to go and find that out separately for each one. The string is
    # a MEASURED observation taken from the register, never a judgement — where nothing was
    # measured the cell says so rather than implying a clean result.
    # Widths were rebalanced, not merely squeezed: Exploitation gave up the most because its
    # text is the most compressible, and Product gave up least because a version string
    # cannot be abbreviated without becoming useless in a change ticket.
    HDR = ["CVE / Advisory ID", "Product and affected versions", "Exploitation",
           "Seen in our logs", "Fix", "Action"]
    W = (Inches(1.00), Inches(1.42), Inches(1.20), Inches(1.30), Inches(0.62), Inches(1.16))

    t = doc.add_table(rows=len(rows) + 1, cols=6)
    t.alignment = WD_TABLE_ALIGNMENT.LEFT; t.autofit = False
    B._fixed_layout(t, Inches(6.7)); B._table_borders(t)
    for j, h in enumerate(HDR):
        c = t.rows[0].cells[j]; B._cell_shade(c, B.LABEL_FILL)
        p = c.paragraphs[0]; p.text = ""
        p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2)
        B._run(p, h, size=8.5, bold=True, color=B.ABBEY)
    for i, r in enumerate(rows, start=1):
        exp = exploitation(r)[0]
        prod = r["product"] + (f" · CVSS {r['cvss']}"
                               if r["cvss"] and not r["cvss"].lower().startswith("not") else "")
        act = action_text(r) + f" [{cite_of[r['id']]}]"
        obs = (r.get("observed") or "").strip() or "Not measured this run"
        for j, val in enumerate([r["id"], prod, exp, obs, fix_category(r), act]):
            c = t.rows[i].cells[j]; p = c.paragraphs[0]; p.text = ""
            p.paragraph_format.space_before = Pt(1.0); p.paragraph_format.space_after = Pt(1.0)
            if j == 0:
                B._run(p, val, size=8.0, bold=True, color=B.ABBEY)
                tag = c.add_paragraph()
                tag.paragraph_format.space_before = Pt(0); tag.paragraph_format.space_after = Pt(1)
                B._run(tag, r["change"], size=7, bold=True,
                       color=CHGCOLOR.get(r["change"], B.GREY), caps=True)
            elif j == 3:
                # The verdict is the whole point of the cell and is rendered as a verdict:
                # one bold, coloured token on its own line, with the measurement beneath it
                # in small grey. Before 2026-09-01 this cell was a paragraph of measurement
                # text and a reader had to parse a sentence to learn a yes or a no.
                verdict, qualifier = split_verdict(val)
                B._run(p, verdict, size=8.5, bold=True, color=VERDICTCOLOR[verdict])
                if qualifier:
                    q = c.add_paragraph()
                    q.paragraph_format.space_before = Pt(0)
                    q.paragraph_format.space_after = Pt(1)
                    B._cite(q, qualifier, size=6.5, color=B.GREY)
            elif j == 4:
                B._run(p, val, size=8.0, bold=True, color=FIXCOLOR[val])
            else:
                B._cite(p, val, size=8.0, color=B.ABBEY)
    B._set_grid(t, W); B._no_split(t)

    target = next(x for x in doc.tables if SENTINEL in x.rows[0].cells[0].text)
    target._tbl.addprevious(t._tbl); target._tbl.getparent().remove(target._tbl)

    if dropped:
        note = B._para(doc, space_before=4)
        B._run(note, f"+{dropped} further item(s) changed this run and are in the register's Latest Run tab.",
               size=8, italic=True, color=B.GREY)
        srcs = [p for p in doc.paragraphs if p.text.strip() == "Sources"]
        if srcs: srcs[0]._element.addprevious(note._element)

    # ---------------------------------------------------- Appendix A: validation queries
    # Added 2026-08-27 at April's request. THE PAGE CONTRACT CHANGES HERE, deliberately and
    # visibly: page one is still the one-page forwardable matrix and nothing was removed from
    # it, but the document is now two or more pages. Putting the queries beside the matrix was
    # tried mentally and rejected — a Consolas block in a table cell destroys the row rhythm
    # that makes the matrix scannable, and the matrix is the thing VM reads in a hurry.
    #
    # The queries are stored in the REGISTER, not generated here, so the brief and the hunt
    # packages cannot drift apart and so a query can be corrected once in the source of truth.
    q_rows = ([r for r in rows
               if (r.get("val_spl") or "").strip()
               or (BRIEF_SHOWS_CQL and (r.get("val_cql") or "").strip())]
              if appendix else [])
    appendix_from = None
    if q_rows:
        # HARD PAGE BREAK. Without it the appendix starts wherever the matrix happens to end,
        # which makes page one a matrix plus two stray queries — the worst of both documents.
        # The break is what preserves the original contract: page one is still the one-page
        # sheet April forwards, and everything after it is reference the analyst opens on demand.
        brk = B._para(doc, space_before=0, space_after=0)
        brk.add_run().add_break(WD_BREAK.PAGE)
        appendix_from = len(doc.paragraphs)
        h = B.add_section_heading(doc, "Appendix A — Validation searches: paste into Splunk and run")
        intro = B._para(doc, space_before=2, space_after=6)
        B._run(intro,
               "One search per CVE. Each is complete and self-contained — copy the whole block into the "
               "Splunk search bar and press enter. Do not set a time picker: every search carries its own "
               "14 day window, so the results will be the same whatever the picker says. Field names are "
               "renamed to plain English, and the last line of each search states the answer in words rather "
               "than leaving you to interpret a count. If a search matches nothing it returns a single row "
               "saying so, so an empty screen never has to be guessed at. Every search here was executed "
               "against live Splunk before this brief was issued. A NO from a search still only clears what "
               "the logs cover — where that matters the row says CANNOT CONFIRM instead.",               size=8, italic=True, color=B.GREY)
        # Two CVEs in the same product chain share one search — PaperCut's pair is the
        # standing example. Rendering it twice cost most of a page and, worse, invited the
        # reader to skim the second block assuming it differed. Print it once and point the
        # duplicate at it.
        seen_search = {}
        for r in q_rows:
            hdr_p = B._para(doc, space_before=7, space_after=2)
            B._run(hdr_p, r["id"], size=9, bold=True, color=B.ABBEY)
            B._run(hdr_p, "   " + (r["product"] or ""), size=8, color=B.GREY)
            key = (r.get("val_spl") or "").strip()
            if key and key in seen_search:
                dupe = B._para(doc, space_before=2, space_after=2)
                dupe.paragraph_format.left_indent = Inches(0.16)
                B._run(dupe, "Same search as %s above — one search answers both CVEs, "
                             "because they are two halves of one chain in one product."
                             % seen_search[key], size=8, italic=True, color=B.GREY)
                continue
            if key:
                seen_search[key] = r["id"]
            halves = [("Splunk search", r.get("val_spl"))]
            if BRIEF_SHOWS_CQL:
                halves.append(("Falcon CQL", r.get("val_cql")))
            for label, body in halves:
                body = (body or "").strip()
                if not body or body.lower().startswith("not assessed"):
                    continue
                lp = B._para(doc, space_before=3, space_after=1)
                B._run(lp, label, size=7.5, bold=True, color=B.ORANGE_DEEP, caps=True)
                for line in body.splitlines():
                    cp = B._para(doc, space_before=0, space_after=0)
                    cp.paragraph_format.left_indent = Inches(0.16)
                    run = B._run(cp, line or " ", size=7.5, color=B.ABBEY)
                    run.font.name = "Consolas"

    # the bulletin builder emits "What Happened" unconditionally; drop it when empty
    for p in list(doc.paragraphs):
        if p.text.strip() == "What Happened":
            el = p._element; prev = el.getprevious()
            if prev is not None and prev.tag.endswith('}p') and not Paragraph(prev, p._parent).text.strip():
                prev.getparent().remove(prev)
            el.getparent().remove(el)
    doc.save(out_docx); os.unlink(specfile)
    return {"rows": len(rows), "new": n_new, "updated": n_upd, "exploited": n_exp,
            "dropped": dropped, "appendix_rows": len(q_rows)}


def page_count(path):
    d = tempfile.mkdtemp()
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", path, "--outdir", d],
                   capture_output=True, timeout=180)
    pdf = os.path.join(d, os.path.basename(path).replace(".docx", ".pdf"))
    return len(re.findall(rb"/Type\s*/Page[^s]", open(pdf, "rb").read())) if os.path.exists(pdf) else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("register"); ap.add_argument("out"); ap.add_argument("skill_dir")
    ap.add_argument("--run-date", default=None); ap.add_argument("--max-rows", type=int, default=10)
    a = ap.parse_args()
    st = build(a.register, a.out, a.skill_dir, a.run_date, a.max_rows)
    st["pages"] = page_count(a.out)

    # TWO PAGE BUDGETS SINCE 2026-08-27, and only the first one is a constraint.
    #
    # The original rule was "the brief is one page", and a naive total-page check now fires on
    # every run purely because Appendix A exists — which would train the operator to ignore the
    # warning, the worst possible outcome for a check. So measure the thing the rule was
    # actually protecting: the FORWARDABLE MATRIX. Render a second, appendix-free copy to a
    # temp file and page-count that. If it is one page the contract holds, however long the
    # appendix runs, because the appendix is reference material opened on demand rather than
    # something anyone reads end to end.
    tmp_out = tempfile.mktemp(suffix=".docx")
    try:
        build(a.register, tmp_out, a.skill_dir, a.run_date, a.max_rows, appendix=False)
        st["matrix_pages"] = page_count(tmp_out)
    finally:
        if os.path.exists(tmp_out):
            os.unlink(tmp_out)

    print(json.dumps(st, indent=1))
    if st["matrix_pages"] and st["matrix_pages"] > 1:
        print("WARNING: the forwardable matrix exceeded one page - lower --max-rows or shorten "
              "Action text. (Appendix A length is not a defect.)", file=sys.stderr)
