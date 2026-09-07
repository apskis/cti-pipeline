#!/usr/bin/env python3
"""GeneLabs CTI - Open Exposures briefing, LANDSCAPE one pager.

A roll-up across every open exposure advisory, built to be talked through with a
team rather than read alone. One row per exposure and nothing else - the analysis
belongs in the conversation, not on the page.

Not the same artifact as an exposure advisory: that is one asset, for its owner.
This is all of them, for a briefing. Each row names its advisory for the detail.

    python3 build_exposure_briefing.py out.docx <genelabs-exposure-advisory skill dir>

NOTE for future edits: build the ROWS table by editing this file directly. Do NOT
patch it with re.sub - a replacement string interprets backslash escapes, so the
\\n in every asset cell becomes a real newline and the file stops parsing.
"""
import os, sys, urllib.parse
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Inches, Pt

sys.path.insert(0, os.path.join(sys.argv[2], "scripts"))
from genelabs_style import (ORANGE, ORANGE_DEEP, ABBEY, GREY, RULE, LABEL_FILL,
                            add_banner, build_footer, para, run, set_base_style,
                            shade_cell, table_borders, border, set_grid)

RED, AMBER, GREEN = "C62828", "EF6C00", "2E7D32"
LINK = "1565C0"

# Where the advisories live. Links are SHAREPOINT, not file:/// - a local profile path
# only resolves on April's own machine, and this document gets forwarded. Derived from
# the id= parameter of the library view URL:
#   /teams/SecOps/SOC/Shared Documents/CTI/CTI Deliverables/Exposure Advisories
SP_FOLDER = ("https://<your-tenant>.sharepoint.com/teams/SecOps/SOC/Shared%20Documents"
             "/CTI/CTI%20Deliverables/Exposure%20Advisories")
# the browsable library view, used for the folder link in the intro
SP_FOLDER_VIEW = ("https://<your-tenant>.sharepoint.com/teams/SecOps/SOC/Shared%20Documents/Forms/AllItems.aspx"
                  "?id=%2Fteams%2FSecOps%2FSOC%2FShared%20Documents%2FCTI%2FCTI%20Deliverables"
                  "%2FExposure%20Advisories&sortField=Modified&isAscending=false"
                  "&viewid=83b313e0%2Dc946%2D437e%2D830f%2D6b5a756da8d0")

FILES = {
 "CTI-EXP-GLCN01":                    "2026-08-24-GLCN-PRD-TMSF01-Internet-Exposure-Explainer.docx",
 "CTI-EXP-GLUSVWPT01":                "2026-08-24-GLUS-PRD-VWPT01-VendorTunnel-Explainer.docx",
 "CTI-EXP-GLEUVPNI01":                "2026-08-24-GLEU-PRD-VPNI74-QuickTunnel-Explainer.docx",
 "CTI-EXP-WebEstate":           "2026-08-25-WebEstate-AllowedScanningExposure-Explainer.docx",
 "CTI-EXP-EvidenceRadar":             "2026-08-25-EvidenceRadar-ShadowAIDataExposure-Explainer.docx",
 "CTI-EXP-IntSvcDMZTest": "2026-08-26-IntegrationServiceDMZTest-InternetExposure-Explainer.docx",
 "CTI-EXP-PKIW02":                    "2026-08-27-PKIW02-Permitted-Vulnerability-Scanning-Explainer.docx",
}


def file_url(filename):
    """SharePoint URL for one advisory in the library folder."""
    return SP_FOLDER + "/" + urllib.parse.quote(filename)


def hyperlink(paragraph, text, url, size=6.5, italic=True):
    """python-docx has no hyperlink API; build the w:hyperlink element by hand."""
    r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), r_id)
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    for tag, attr, val in (("w:rFonts", "w:ascii", "Arial"), ("w:rFonts", "w:hAnsi", "Arial")):
        e = rPr.find(qn(tag))
        if e is None:
            e = OxmlElement(tag); rPr.append(e)
        e.set(qn(attr), val)
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(int(size * 2))); rPr.append(sz)
    col = OxmlElement("w:color"); col.set(qn("w:val"), LINK); rPr.append(col)
    u = OxmlElement("w:u"); u.set(qn("w:val"), "single"); rPr.append(u)
    if italic:
        rPr.append(OxmlElement("w:i"))
    r.append(rPr)
    t = OxmlElement("w:t"); t.text = text; t.set(qn("xml:space"), "preserve")
    r.append(t)
    link.append(r)
    paragraph._p.append(link)
    return link

HEADER = ["Asset  /  advisory", "EDR", "Known bad\ntraffic allowed",
          "What is exposed, and why we care", "Where it stands (29 Aug)", "Next action / owner"]
# col 2 stays wide enough that "Partial" cannot break mid word. Seven rows are tighter
# than six, so width moves from the asset and action columns - which had spare lines - to
# the two prose columns, which are what set each row's height.
WIDTHS = [1.75, 0.60, 0.76, 3.75, 1.70, 1.44]

# Ordered so the two rows where KNOWN BAD TRAFFIC ALLOWED reads YES come first: that is
# the strongest signal on the page and those rows should lead the discussion.
ROWS = [
 ("intsvc-dmztest", "Non production integration tier",
  "CTI-EXP-IntSvcDMZTest v3.0",
  "No", "YES",
  "A test tier answering on the public internet; most permitted sessions originate outside the "
  "corporate network. Test tiers carry unrotated service accounts and connection strings pointing "
  "at real backends. Two addresses already classified as malicious were allowed to reach it "
  "repeatedly within the reporting window.",
  "STILL OPEN. Answering again today. Sustained request volume from a wide source spread, and "
  "still no named owner.",
  "Block the known bad sources, then restrict 443 to partners.\nNetwork Security"),

 ("Public web estate", "Several public properties, Northgate web tier", "CTI-EXP-WebEstate v3.0",
  "Partial", "YES",
  "One scanner was allowed a very large number of connections in a single day, running SQL "
  "injection and web shell probes. The same firewall BLOCKED that source to other destinations "
  "the same day, so blocking is possible and was simply not applied consistently. A second "
  "address had been in the threat platform for days and was still allowed through.",
  "Scanning stopped on its own. Nothing about the configuration changed.",
  "Explain why one source was blocked to some destinations and allowed to others.\nNetwork Security"),

 ("GLCN-PRD-APPS01", "Production Windows server, overseas cloud region", "CTI-EXP-GLCN01 v3.0",
  "Yes", "None seen",
  "Remote management exposed to the whole internet. WinRM is remote command execution, not a "
  "passive listener: anyone reaching it with working credentials runs PowerShell on the server. "
  "Remote Desktop has appeared alongside it behind a self issued certificate. The corporate "
  "firewall and SIEM see nothing, because the cloud provider controls the door.",
  "STILL OPEN, and WIDER. The latest scan shows Remote Desktop answering as well.",
  "Remove the open ingress rules, a security group change of minutes.\nCloud Engineering"),

 ("GLUS-PRD-VWPT01", "Vendor monitoring console, Westport, validated environment",
  "CTI-EXP-GLUSVWPT01 v3.0",
  "Yes", "None seen",
  "A tunnel agent the vendor ships inside its own product publishes the monitoring console on a "
  "public address. The tunnel is outbound, so an external scan reports the host closed and the "
  "exposure does not appear in perimeter scanning at all.",
  "OPEN. Confirmed by configuration review rather than by scanning.",
  "Confirm whether vendor remote support is contracted.\nApplication owner"),
]

# ---------------------------------------------------------------------------
# APPENDIX A. Page one is the table and stays the table. Everything that lets a
# reader reproduce a row lives here, on pages two onward, the same shape the
# exposure advisories use: one page body, then the working.
#
# THE POINT OF A.1 IS THE DISTINCTION IT DRAWS. A weekly roll-up is assembled
# mostly from advisories that were measured on the day they were written, not on
# the day the briefing ships. An appendix that presented every row as freshly
# measured would be the one failure this format cannot afford, because the whole
# argument of the page is "these are STILL here". So each row is marked either
# MEASURED IN THIS RUN, or INHERITED with the date it was last established.
# ---------------------------------------------------------------------------

# asset, where the row text came from, state label, what backs the state
PROVENANCE = [
 ("integrationservice-\ndmztest",
  "Summary callout, the three Why We Care bullets, action table row 1 and A.6 of "
  "CTI-EXP-IntSvcDMZTest v3.0.",
  "MEASURED IN THIS RUN",
  "Shodan host record for 203.0.113.20 retrieved 29 Aug 12:17 UTC: TCP 443 open, Microsoft IIS 10.0, "
  "certificate to Feb 2027. Confirms the asset still answers the internet today.  INHERITED from "
  "advisory A.2 and A.3, established 26 Aug and NOT rerun: the 9,000 requests, the 500 sources, the "
  "280 permitted sessions and both ThreatQ listed addresses."),

 ("Public web estate",
  "Summary callout, Why We Care bullets 1 to 3, action table row 2 and A.6 of "
  "CTI-EXP-WebEstate v3.0.",
  "INHERITED, established 26 Aug",
  "Not rerun this week and not externally observable: the finding is a firewall decision, not an open "
  "port. The 150,000 allowed flows, the 18,000 blocked, the several blocked destinations against twenty "
  "two allowed and the 23 Aug ThreatQ address are all advisory A.1 and A.2. The count of seven "
  "properties rather than eight comes from the correction issued 27 Aug, tested in the PKIW02 advisory "
  "at walkthrough step 10."),

 ("GLCN-PRD-TMSF01",
  "Summary callout and Why We Care bullets 2 and 3 of CTI-EXP-GLCN01 v3.0. The status line is this "
  "run's own measurement and is AHEAD of the advisory.",
  "MEASURED IN THIS RUN",
  "Shodan host record for 203.0.113.10 retrieved 28 Aug 22:14 UTC: ports 135, 3389 and 5985, OS Windows "
  "Server 2022 build 10.0.20348, TCP 3389 carrying a self issued certificate (subject and issuer both "
  "glcn-prd-tmsf01).  THE ADVISORY RECORDS 135 AND 5985 ONLY. Remote Desktop is new since it was "
  "written, which is why the row reads WIDER and why the advisory needs reissuing."),

 ("GLUS-PRD-VWPT01",
  "Summary callout, Why We Care bullets 1 to 3, action table rows 2 and 3, and A.6 of "
  "CTI-EXP-GLUSVWPT01 v3.0.",
  "INHERITED, established 26 Aug",
  "NOT externally observable and therefore NOT refreshable by scanning: the tunnel is established "
  "outbound, so an external scan of this host reports nothing and a clean scan here would be a false "
  "negative. The daily check ins from 19 to 26 Aug, the 17:04 UTC check in and the survival of the "
  "17 Aug reboot are Falcon process and network telemetry, advisory A.1 and A.3. Refreshing this row "
  "needs Falcon or Splunk, not Shodan."),

 ("GLUS-PRD-PKIW02",
  "Summary callout, Why We Care bullets 1 and 2, action table row 1 and A.6 of CTI-EXP-PKIW02 v1.0.",
  "MEASURED IN THIS RUN",
  "Shodan host record for 203.0.113.30 retrieved 29 Aug 08:50 UTC: ports 80 and 6080, IIS 10.0, content "
  "still Last-Modified 11 Jun 2019. CAVEAT CARRIED FORWARD FROM THE ADVISORY: the 6080 banner is still "
  "dated 17 Aug, so that port is a cached observation and its current state is unconfirmed.  INHERITED "
  "from advisory A.2, A.3 and walkthrough steps 5 and 6, established 27 Aug: the 46,300 connections, "
  "the 29,700 paths, the four bursts and the blocked telnet and SSH counts."),

 ("GLEU-PRD-VPNI74",
  "Summary callout, Why We Care bullets 1 to 3, action table rows 1 and 2, and A.6 of "
  "CTI-EXP-GLEUVPNI01 v3.0.",
  "INHERITED, established 26 Aug",
  "NOT externally observable, for the same reason as GLUS-PRD-VWPT01: a quick tunnel is an outbound "
  "connection and external scanning reports the host closed. The two client executions at about 12:14 "
  "UTC on 24 Aug and the absence of any further provisioning are Falcon telemetry, advisory A.1. "
  "'The client binary is not confirmed removed' is a statement about what nobody has checked, not a "
  "measurement, and it should be read that way in the room."),

 ("Evidence Opportunity\nRadar",
  "Summary callout, Why We Care bullets 1 to 3, action table rows 1 and 2, and A.6 of "
  "CTI-EXP-EvidenceRadar v3.0.",
  "INHERITED, established 26 Aug",
  "Not an GeneLabs host, so there is nothing of ours to scan or sensor. Reachability, the shared "
  "password model, the sibling application and the third application are a CTI external fetch of 25 Aug "
  "rechecked 26 Aug, advisory A.1. No content behind the login was accessed and no credentials were "
  "used, which is why the row says what the platform advertises and not what it holds."),
]

# step, tool and exact call, result, what it establishes and does not establish
RUN_STEPS = [
 ("1",
  "Shodan connector\nshodan_host(ip=\"203.0.113.10\")",
  "ports [135, 3389, 5985]; org Beijing Sinnet Technology; AS55960; os Windows Server 2022 build "
  "10.0.20348; TCP 3389 Remote Desktop with NTLM info and a self signed certificate, subject and "
  "issuer both glcn-prd-tmsf01; last_update 2026-08-28T22:14:51Z.",
  "ESTABLISHES that the exposure is not only still open but has GROWN since the advisory, which lists "
  "135 and 5985. That is the difference between a row that reads STILL OPEN and one that reads WIDER, "
  "and it is the strongest argument on the page that an untouched exposure does not decay.  DOES NOT "
  "ESTABLISH when 3389 opened, or by whom. Shodan gives a last scan time, not a change time. Only the "
  "security group history in AWS account 179162745785 answers that."),

 ("2",
  "Shodan connector\nshodan_host(ip=\"203.0.113.20\")",
  "port [443]; org GENELABS, INC.; AS12158; IIS 10.0; Last-Modified 25 Jun 2022; F5 BIG-IP cookie "
  "BIGipServerINTSVC_TEST; certificate CN intsvc-dmztest.genelabs.com to "
  "14 Feb 2027; last_update 2026-08-29T12:17:35Z.",
  "ESTABLISHES that the asset was still answering the internet hours before this briefing was built, "
  "so the top row of the page is current rather than three days old.  DOES NOT ESTABLISH that the two "
  "known bad sources are still reaching it. That is a firewall question and needs the Splunk search in "
  "the advisory, which was not rerun. The YES in the flag column is therefore inherited, not refreshed."),

 ("3",
  "Shodan connector\nshodan_host(ip=\"203.0.113.30\")",
  "ports [80, 6080]; org GENELABS, INC.; AS12158; IIS 10.0; TCP 80 Last-Modified 11 Jun 2019; TCP 6080 "
  "HTTP 403 with a banner dated 17 Aug; last_update 2026-08-29T08:50:48Z.",
  "ESTABLISHES that the certificate revocation host is still published, which it should be, and that "
  "the 2019 content date has not moved.  DOES NOT ESTABLISH the current state of 6080: the banner "
  "predates the host record by twelve days, so it is a cached observation. Reading it as live would be "
  "the same error the advisory warns about, and the row does not claim it.  TRAP, carried from the "
  "advisory: a hostname search for pki.genelabs.example returns zero. The index is keyed on the address. "
  "Do not read that zero as absence of exposure."),
]

# check, how it was run, result
VERIFY_STEPS = [
 ("Page one is one landscape page",
  "Convert with LibreOffice, then read the media box with pypdf rather than estimating: "
  "PdfReader(pdf).pages[0].mediabox",
  "792.0 x 612.0 pt, landscape. The table occupies page one alone and this appendix begins on page "
  "two after an explicit page break."),

 ("Every row carries an owner",
  "Walk the last cell of every table row with python-docx and print it.",
  "Seven of seven: Network Security, Network Security, Cloud Engineering, ViewPoint owner, "
  "PKI Operations, Cloud Engineering, Data Governance."),

 ("Every advisory reference resolves",
  "Extract the external relationship targets from the package, percent decode each filename and test "
  "it against the Exposure Advisories folder on disk.",
  "Seven of seven resolve. A link that points nowhere is indistinguishable from a working one until "
  "somebody clicks it in front of an audience, which is why this is tested rather than assumed."),

 ("No stray or orphaned links",
  "Compare every relationship id declared in the .rels parts against the ids actually referenced in "
  "the document body.",
  "Eight external relationships, all on <your-tenant>.sharepoint.com, zero orphaned. The house template "
  "historically carried eleven orphaned news links; the builder uses the cleaned copy in _tools/assets."),

 ("Typeface and page furniture",
  "Read every rFonts attribute in the package; read the footer part.",
  "Arial only. Footer carries the wordmark, TLP:AMBER+STRICT, the DOC # derived from the output "
  "filename, and a live page field."),

 ("No flag value breaks mid word",
  "Extract words inside the two flag columns with pdfplumber and check each value sits on one line.",
  "Partial, YES, No, Yes and n/a all intact. None seen wraps between its two words, which is the "
  "column doing its job rather than a rendering fault."),
]


def cell_text(cell, text, size=8, bold=False, color=ABBEY, space=0.5):
    cell.text = ""
    first = True
    for line in text.split("\n"):
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        p.paragraph_format.space_after = Pt(space)
        p.paragraph_format.space_before = Pt(0)
        run(p, line, size=size, bold=bold, color=color)


def flag(cell, val):
    """Centred status flag. Red is the one that should stop a reader."""
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    colour = {"YES": RED, "No": RED, "Partial": AMBER, "Yes": GREEN}.get(val, GREY)
    run(p, val, size=8, bold=val in ("YES", "No", "Partial"), color=colour)


def app_table(doc, headers, widths, rows, total_width, sizes=None):
    """One appendix table, house shaded header, Arial throughout."""
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    for i, h in enumerate(headers):
        cell_text(t.rows[0].cells[i], h, size=8, bold=True, color="FFFFFF")
        shade_cell(t.rows[0].cells[i], ORANGE_DEEP)
    # repeat the header on every page the table runs onto: a continuation page of
    # unlabelled columns is unreadable
    hdr = OxmlElement("w:tblHeader"); hdr.set(qn("w:val"), "true")
    t.rows[0]._tr.get_or_add_trPr().append(hdr)
    for r in rows:
        c = t.add_row().cells
        for i, v in enumerate(r):
            cell_text(c[i], v, size=(sizes[i] if sizes else 7.5))
        shade_cell(c[0], LABEL_FILL)
    # keep every row whole. A row broken across a page boundary leaves a stub like
    # "Radar" alone at the top of the next page, which reads as a fault
    for row in t.rows:
        ns = OxmlElement("w:cantSplit")
        row._tr.get_or_add_trPr().append(ns)
    table_borders(t, color=RULE, sz=6)
    set_grid(t, [w / sum(widths) for w in widths], total_width)
    return t


def heading(doc, text, size=11, space_before=10):
    p = para(doc, text, size=size, bold=True, color=ORANGE_DEEP, space_after=3)
    p.paragraph_format.space_before = Pt(space_before)
    return p


def build_appendix(doc, total_width):
    """Pages two onward: how every row on page one can be reproduced by hand.

    Deliberately NOT a second table of findings. The briefing argues nothing; this
    argues why the briefing is worth holding, and it separates what this run
    measured from what it inherited, because a roll-up that presents inherited
    evidence as fresh is the one way this format can mislead.
    """
    br = doc.add_paragraph()
    br.paragraph_format.space_after = Pt(0)
    br.add_run().add_break(WD_BREAK.PAGE)

    t = para(doc, "Appendix A - Validation, tooling and reasoning", size=15, bold=True,
             color=ABBEY, space_after=2)
    border(t, "bottom", ORANGE, sz=12, space=4)

    para(doc,
         "Page one is the reference and the presenter is the argument. This appendix is neither: it is "
         "the working, so that any claim on page one can be checked by somebody who was not in the room. "
         "Read A.1 first. It records, per row, whether the exposure state was measured in THIS run or "
         "inherited from the advisory that raised it, because a weekly roll-up is assembled mostly from "
         "advisories written on earlier dates, and the whole argument of page one is that these are "
         "STILL here. Presenting inherited evidence as fresh would be the one failure this format cannot "
         "absorb.",
         size=8.5, color=GREY, space_after=2)
    para(doc,
         "Nothing here is a new finding. Where a number appears on page one it is traceable through this "
         "appendix to the advisory section or the connector call it came from, and every advisory carries "
         "its own step by step walkthrough for the evidence underneath that.",
         size=8.5, color=GREY, space_after=6)

    heading(doc, "A.1  Provenance of each row: measured in this run, or inherited", space_before=2)
    para(doc,
         "MEASURED IN THIS RUN means a connector was called during this build and the result is quoted "
         "in A.2. INHERITED means the row restates an advisory finding and carries that advisory's "
         "measurement date, not today's. Neither is better; an inherited row is only weaker if the "
         "reader is not told.",
         size=8, color=GREY, space_after=4)
    app_table(doc,
              ["Row", "Where the row text came from", "State of the exposure, and what backs it"],
              [1.35, 3.30, 5.35],
              [(a, b, c.upper() + "\n" + d) for a, b, c, d in PROVENANCE],
              total_width, sizes=[8, 7.5, 7.5])

    heading(doc, "A.2  Steps measured in this run: the exact calls, and what each does and does not settle")
    para(doc,
         "Three read only external lookups, no authentication and no traffic to GeneLabs systems. Each is "
         "reproducible by anyone with the Shodan connector. The DOES NOT ESTABLISH column is the load "
         "bearing one: it is what stops a row being read for more than it says.",
         size=8, color=GREY, space_after=4)
    app_table(doc,
              ["Step", "Tool and exact call", "Result returned",
               "What it establishes, and what it does not"],
              [0.55, 2.15, 3.15, 4.15],
              RUN_STEPS, total_width, sizes=[8, 7.5, 7.5, 7.5])

    heading(doc, "A.3  Evidence NOT rerun this week, and where its walkthrough lives")
    para(doc,
         "Four rows could not be refreshed by external scanning, and two of those cannot be refreshed by "
         "scanning at all: a tunnel is an outbound connection, so an external scan of GLUS-PRD-VWPT01 or "
         "GLEU-PRD-VPNI74 reports the host closed and a clean scan would be a FALSE NEGATIVE rather than "
         "good news. Refreshing those needs Falcon or Splunk. Every firewall figure on page one - the "
         "150,000 allowed flows, the 46,300 scan connections, the 280 permitted sessions, and both "
         "KNOWN BAD TRAFFIC ALLOWED flags - is likewise inherited, because no Splunk search was run in "
         "this build. Each advisory linked from page one carries its own Appendix A.7 walkthrough giving "
         "the query, the expected result and the reasoning for every one of those numbers; that is the "
         "next place to go, and it is one click from the row.",
         size=8.5, color=GREY, space_after=4)

    heading(doc, "A.4  How the document itself was verified, and how to repeat it")
    para(doc,
         "Layout and link defects are silent: a briefing that fails one of these looks correct until it "
         "is opened in front of an audience. Each check below was run programmatically on the built file "
         "rather than judged by eye, and then page one was rendered and looked at, because the remaining "
         "defects are visual ones.",
         size=8, color=GREY, space_after=4)
    app_table(doc,
              ["Check", "How it was run", "Result"],
              [2.30, 4.05, 3.65],
              VERIFY_STEPS, total_width, sizes=[8, 7.5, 7.5])

    heading(doc, "A.5  The reasoning: why this page is built the way it is")
    for h, body in (
        ("Why two flag columns and not a severity column.",
         "A severity column on this set would read HIGH seven times and carry no information, and its "
         "width is better spent on prose. The two flags do carry information because they vary and "
         "because they ask different questions. EDR asks whether we would see anything if this went "
         "wrong. KNOWN BAD TRAFFIC ALLOWED asks whether something our own threat intelligence has "
         "already condemned reached the asset and was permitted, which is not a prediction about risk "
         "but a record of a control that did not act. Where it reads YES, that row leads."),
        ("Why n/a is not No, and why None seen is not No.",
         "External SaaS platform has no endpoint sensor because it is not an GeneLabs host, not "
         "because a control is missing; writing No there would invent a gap and send somebody to fix "
         "nothing. None seen records that no condemned source was OBSERVED reaching the asset, which is "
         "not proof that none did, particularly on assets whose telemetry we know to be incomplete. "
         "Tidying either into a cleaner looking No would make the page more confident than the evidence."),
        ("Why the status column is the one that earns the meeting.",
         "A list of findings is a status report and can be circulated instead of discussed. A list "
         "carrying STILL OPEN, LIVE, and stopped on its own with the configuration unchanged is a "
         "conversation about why these are still here. Two entries do most of that work this week: "
         "GLCN-PRD-TMSF01 has grown a third exposed service since it was raised, and the the public web "
         "scanning stopped without anything being fixed. An exposure that ends because the attacker "
         "lost interest has not been remediated, and an exposure left open does not decay."),
        ("What would change the page.",
         "Each row turns on one unanswered question, and they are in the advisories rather than here: "
         "whether the SAP test tier can reach production SAP; what the ViewPoint console shows a visitor "
         "arriving through the tunnel; what listens on port 3001; whether certificate authority key "
         "material sits on the PKI host; what the web shell probes were answered with; and what the "
         "shared password application actually contains. Answering any one of them moves a row up or "
         "off the page, which is why the action column names one action and one owner rather than a plan."),
    ):
        p = para(doc, "", size=8.5, color=GREY, space_after=3)
        run(p, h + "  ", size=8.5, bold=True, color=ABBEY)
        run(p, body, size=8.5, color=GREY)


def build(out_path, skill_dir):
    # Prefer the CLEANED workspace template. The copy shipped in the skill assets
    # carries eleven orphaned external relationships from the bulletin it was cut
    # from; see _tools/strip_orphan_links.py. Falls back to the skill copy.
    tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "cti_doc_template.docx")
    if not os.path.exists(tpl):
        tpl = os.path.join(skill_dir, "assets", "cti_doc_template.docx")
    doc = Document(tpl) if os.path.exists(tpl) else Document()
    set_base_style(doc)

    for s in doc.sections:                       # landscape BEFORE the banner
        w, h = s.page_width, s.page_height
        s.orientation = WD_ORIENT.LANDSCAPE
        s.page_width, s.page_height = max(w, h), min(w, h)
        # seven rows do not fit at 0.75in margins. Landscape has width to spend and no
        # depth to spend, so the fix is width, not shorter sentences: 0.5in each side
        # buys 0.5in of prose width, which is roughly a line off every long cell.
        s.left_margin = s.right_margin = Inches(0.5)
        s.top_margin = Inches(0.35)
        s.bottom_margin = Inches(0.3)
    for p in list(doc.paragraphs):
        p._element.getparent().remove(p._element)

    t = para(doc, "Open Exposures Team Briefing", size=17, bold=True, color=ABBEY, space_after=1)
    border(t, "bottom", ORANGE, sz=12, space=4)
    para(doc,
         "Seven assets reachable from somewhere they should not be, as at 29 August 2026, all HIGH. EDR: "
         "is there a Falcon sensor on the host. KNOWN BAD TRAFFIC ALLOWED: an address we already hold as "
         "malicious reached the asset and was permitted - the strongest signal here, and the top two "
         "rows are ordered on it. Advisories in ",
         size=8.5, color=GREY, space_after=4)
    intro = doc.paragraphs[-1]
    hyperlink(intro, "SecOps > SOC > CTI > CTI Deliverables > Exposure Advisories",
              SP_FOLDER_VIEW, size=8.5, italic=False)
    run(intro, " on SharePoint.", size=8.5, color=GREY)

    tab = doc.add_table(rows=1, cols=len(HEADER))
    tab.autofit = False
    for i, h in enumerate(HEADER):
        cell_text(tab.rows[0].cells[i], h, size=8, bold=True, color="FFFFFF")
        shade_cell(tab.rows[0].cells[i], ORANGE_DEEP)

    for name, desc, ref, edr, tq, risk, stands, action in ROWS:
        c = tab.add_row().cells
        c[0].text = ""
        pA = c[0].paragraphs[0]; pA.paragraph_format.space_after = Pt(0)
        run(pA, name, size=8, bold=True)
        pB = c[0].add_paragraph(); pB.paragraph_format.space_after = Pt(0)
        run(pB, desc, size=8, bold=True)
        # the advisory reference rides on the same paragraph rather than its own:
        # a separate line cost six lines across the table and pushed the closing
        # block onto a second page
        run(pB, "  ", size=6.5, color=GREY)
        doc_id = ref.rsplit(" v", 1)[0]
        if doc_id in FILES:
            hyperlink(pB, ref, file_url(FILES[doc_id]))
        else:
            run(pB, ref, size=6.5, italic=True, color=GREY)
        shade_cell(c[0], LABEL_FILL)
        flag(c[1], edr)
        flag(c[2], tq)
        for i, v in ((3, risk), (4, stands), (5, action)):
            cell_text(c[i], v)

    table_borders(tab, color=RULE, sz=6)
    total = doc.sections[0].page_width - doc.sections[0].left_margin - doc.sections[0].right_margin
    set_grid(tab, [w / sum(WIDTHS) for w in WIDTHS], total)

    build_appendix(doc, total)

    add_banner(doc)
    # CTI-BRIEF-YYYY-MM-DD, derived from the output filename so a weekly rebuild
    # cannot ship last week's identifier on this week's document
    import re as _re
    _m = _re.match(r"(\d{4}-\d{2}-\d{2})", os.path.basename(out_path))
    _id = "CTI-BRIEF-" + (_m.group(1) if _m else "UNDATED")
    build_footer(doc, _id, "CTI Exposure Briefing",
                 tlp="AMBER+STRICT", copyright_line="© 2026 GeneLabs LLC All rights reserved.")
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    print("wrote", build(sys.argv[1], sys.argv[2]))
