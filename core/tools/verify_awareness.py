#!/usr/bin/env python3
"""Sanitisation gate for the all-employee awareness post.

This runs BEFORE delivery. A Viva Engage post has no access control and is
trivially screenshotted, so anything internal that reaches it cannot be recalled.
The assertions below are deliberately blunt: they fail closed.
"""
import sys, os, re, datetime
from docx import Document

ABBEY = "444648"          # house black — the TLP value must render in this, not orange
ORANGE_ISH = ("EF6C00", "FF7109", "E05F00", "C62828", "B71C1C")

def all_text(doc):
    parts = [p.text for p in doc.paragraphs]
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                parts.append(c.text)
    for s in doc.sections:
        for hf in (s.header, s.footer):
            for p in hf.paragraphs:
                parts.append(p.text)
            for t in hf.tables:
                for row in t.rows:
                    for c in row.cells:
                        parts.append(c.text)
    return "\n".join(parts)


def footer_text(doc):
    """Footer only. The TLP marking must be asserted HERE, never against body
    text: an earlier version of this check passed because the word 'clearest'
    appeared in a red flag, which is exactly the kind of false pass this whole
    file exists to prevent."""
    out = []
    for s in doc.sections:
        for p in s.footer.paragraphs:
            out.append(p.text)
        for t in s.footer.tables:
            for row in t.rows:
                for c in row.cells:
                    out.append(c.text)
    return "\n".join(out)

# Things that must never appear in an all-employee post.
BANNED_PATTERNS = [
    (r"\bTH-?\d{2}-?\d{2}\b",                  "internal hunt ID"),
    (r"\bCTI-?\d{2}-?\d{2}\b",                 "internal bulletin ID"),
    (r"\bCVE-\d{4}-\d{4,7}\b",                 "CVE identifier"),
    (r"\bPI-\d{4}-\d{2}\b",                    "peer incident register ID"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b",           "IP address"),
    (r"\bAMBER\b|\bTLP:AMBER\b",               "AMBER TLP marking on a public-facing post"),
    (r"\b(CrowdStrike|Falcon|Splunk|Claroty|Rapid7|InsightVM|ThreatQ|Intel\s*471|Shodan|Proofpoint|Okta|Entra)\b",
                                               "named internal security tool or platform"),
    (r"\b[a-z0-9-]+\.genelabs\.com\b",         "internal GeneLabs hostname"),
    (r"\b(?:linksvc|provideraccess|designstudio|dmapna|edicogenome|pki)\b",
                                               "named internal web property"),
    (r"\bNo EDR\b|\bunsensored\b|\bblocklist gap\b|\bcoverage gap\b|\bnot licensed\b|\bunlicensed\b",
                                               "statement about an GeneLabs control gap"),
    (r"\bhunt package\b|\btstats\b|\bCQL\b|\bdatamodel\b|\bMITRE\b|\bT1\d{3}\b",
                                               "internal hunt or detection tradecraft"),
]

# Things that MUST appear.
#
# FIXED 2026-08-26. This list previously hardcoded "hang up" and "call back" as
# UNIVERSAL requirements. They are not universal — they are the instructions for a
# PHONE-CHANNEL post, and they were baked in because the first document in the series
# (AWR-2026-08-25, vishing) happened to be a phone one. The second document in the
# series was about a malicious WEB PAGE and could not contain the phrase "hang up"
# without being nonsense, so the gate failed a correctly built post.
#
# This is the same defect class already recorded against verify_bulletin.py on
# 2026-08-25: a verification suite written against a single example document encodes
# that example as the rule, and only reveals itself when a document legitimately
# changes shape.
#
# UNIVERSAL — every post in the series, whatever the channel. These three come
# straight from the skill's Voice section: report, reporting is never a waste of
# time, and nobody is in trouble for reporting. Under-reporting is the real failure
# mode and these are the sentences that address it.
UNIVERSAL_REQUIRED = [
    # NOTE 2026-08-27: was \breport\b, which demanded the bare noun/verb and rejected
    # AWR-2026-08-27, a post whose reporting instructions read "Reporting is never a
    # waste of anyone's time" and "Nobody is in trouble for reporting". Those are the
    # sentences the requirement exists to enforce, and the check rejected them because
    # of an inflection. The requirement is that the post tells the reader to report,
    # not that it uses one particular form of the word.
    (r"\breport(?:s|ed|ing)?\b",                           "an instruction to report"),
    # NOTE: the inter-word class is [\w'’]+, not \w+. A plain \w+ does not match
    # "anyone's", so the phrasing "you are never wasting anyone's time" — which is the
    # natural way to write this sentence — failed a check it plainly satisfies.
    (r"wast\w*\s+(?:[\w'’]+\s+){0,3}time|never a waste",
                                                            "the 'never a waste of time' reassurance"),
    # NOTE: the second branch is \bno\s?(?:one|body)\b, not no\w*\s+(?:one|body).
    # The latter required whitespace INSIDE the word and so could never match the single
    # word "Nobody" — only the two-word "no one". It silently failed AWR-2026-08-25, which
    # contains the sentence verbatim. Caught by re-running the fixed gate against the
    # previous day's post; a gate change is not verified until it has been run against
    # every document it is supposed to accept.
    (r"(?:not|never)\s+(?:[\w'’]+\s+){0,4}in trouble|\bno\s?(?:one|body)\b\s+(?:[\w'’]+\s+){0,3}in trouble",
                                                            "the 'nobody is in trouble for reporting' reassurance"),
]

# CHANNEL-CONDITIONAL — required only when the post is actually about that channel.
#
# FIXED AGAIN 2026-08-27. The 26 Aug fix correctly moved these out of UNIVERSAL, but
# left the channel to be INFERRED from body text. Inference cannot tell a channel the
# post is ABOUT from a channel the post explicitly CONTRASTS ITSELF AGAINST, and the
# very next post proved it: AWR-2026-08-27 is about a drive-by web page and says so by
# ruling the other channels out — "You click a link, you answer a call" (describing
# what this attack is NOT) and "There is no attachment, no fake login screen and
# nothing to paste". The words "call" and "paste" fired both triggers, and the gate
# demanded "hang up", "call back", "close the tab" and "do not paste" on a post where
# all four would have been nonsense.
#
# This is the THIRD appearance of one defect class in this file: a check that encodes
# an example rather than the rule. The durable fix is to stop guessing. The author
# knows the channel; the prose does not reliably carry it. --channel now DECLARES it,
# and may be given more than once, or as "none".
#
# The heuristic is retained, but demoted. When a channel is declared, a trigger that
# fires for an UNDECLARED channel produces a WARNING, not a failure — so a genuinely
# missing instruction still surfaces for a human to judge, while a rhetorical mention
# no longer blocks a correct document. With no --channel at all the old inferring
# behaviour applies unchanged, so existing callers keep working.
CONDITIONAL_REQUIRED = [
    ("phone call",
     r"phone(?:s|d|ing)?\b|call(?:s|ed|er|ing)?\b|vishing|voicemail",
     [(r"hang up",          "the core instruction 'hang up'"),
      (r"call .{0,20}back", "the 'call back' instruction")]),
    ("pasted command",
     r"\bpaste\b|\bclipboard\b|Run box|Terminal|command window",
     [(r"clos\w*\s+the\s+tab|close the (?:tab|page|window)", "the 'close the tab' instruction"),
      (r"do not paste|don't paste|never .{0,30}paste",          "an explicit do-not-paste instruction")]),
]

# Kept for backward compatibility with any caller that imports REQUIRED.
REQUIRED = UNIVERSAL_REQUIRED

def check(path, topic_key=None, fingerprint=None, ledger_path=None, this_awr=None,
          channels=None):
    doc = Document(path)
    text = all_text(doc)
    fails, notes = [], []

    for pat, label in BANNED_PATTERNS:
        hits = sorted(set(m.group(0) for m in re.finditer(pat, text, re.I)))
        if hits:
            fails.append("LEAK — %s: %s" % (label, hits[:6]))
    if not fails:
        notes.append("no internal identifiers, hostnames, IPs, tooling or control gaps  OK")

    missing = []
    for pat, label in UNIVERSAL_REQUIRED:
        if not re.search(pat, text, re.I):
            missing.append(label)
    # channels is None  -> infer from body text (legacy behaviour, unchanged)
    # channels is a list -> those channels are AUTHORITATIVE. "none" declares that the
    #                       post is about no listed channel. A trigger firing for an
    #                       undeclared channel becomes a warning, never a failure.
    declared = None
    if channels is not None:
        declared = {c.strip().lower() for c in channels if c.strip()}
        if declared == {"none"}:
            declared = set()
        unknown = declared - {c for c, _, _ in CONDITIONAL_REQUIRED}
        if unknown:
            fails.append("unknown --channel value(s): %s (valid: %s, or none)"
                         % (sorted(unknown), [c for c, _, _ in CONDITIONAL_REQUIRED]))

    applied, warned = [], []
    for chan, trigger, reqs in CONDITIONAL_REQUIRED:
        fired = bool(re.search(trigger, text, re.I))
        active = (chan in declared) if declared is not None else fired
        if active:
            applied.append(chan)
            for pat, label in reqs:
                if not re.search(pat, text, re.I):
                    missing.append("%s (required because this post is about a %s)" % (label, chan))
        elif fired and declared is not None:
            warned.append(chan)
    for label in missing:
        fails.append("missing %s" % label)
    notes.append("required employee instructions present  OK  [universal + channel: %s]"
                 % (", ".join(applied) if applied else
                    ("none — declared" if declared is not None else "none detected"))
                 if not missing else
                 "required instructions INCOMPLETE")
    for chan in warned:
        notes.append("WARNING: '%s' wording appears but that channel was not declared. "
                     "Its instructions are NOT required. Confirm the mention is "
                     "rhetorical (ruling the channel out) and not the actual subject." % chan)

    # TLP must be CLEAR, never AMBER — asserted against the FOOTER only
    foot = footer_text(doc).upper()
    if not re.search(r"TLP:\s*CLEAR", foot):
        fails.append("footer TLP marking is not CLEAR (footer reads: %r)" % foot[:60])
    elif "AMBER" in foot:
        fails.append("footer still carries an AMBER marking")
    else:
        notes.append("footer marking is TLP: CLEAR  OK")

    # TLP value must render in house black, regular weight — never the orange
    # severity colour. April, 2026-08-26: orange read as an alert on a document
    # whose entire purpose is to be calm and routine.
    # FIXED 2026-08-27. This searched footer TABLES only, which is the EXACT MIRROR of
    # the bug already recorded at the top of this file — where the text extractor read
    # footer paragraphs but not footer tables. The analytical builder puts the footer in
    # a table; the blog builder puts it in paragraphs. Both are valid footers and both
    # must be checked, or the check silently stops applying the moment a new format
    # arrives. That is the third instance of this defect class in this file, and the
    # pattern is always the same: a check written against one document's structure,
    # which then treats a different structure as absence rather than as difference.
    def _footer_runs(section):
        for para in section.footer.paragraphs:
            for run in para.runs:
                yield run
        for table in section.footer.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        for run in para.runs:
                            yield run

    tlp_run = None
    for section in doc.sections:
        for run in _footer_runs(section):
            if run.text.strip() == "CLEAR":
                tlp_run = run
    if tlp_run is None:
        fails.append("could not locate the footer TLP value run to check its colour")
    else:
        col = tlp_run.font.color
        hexv = None
        try:
            hexv = str(col.rgb) if col and col.rgb is not None else None
        except Exception:
            hexv = None
        if hexv is None:
            fails.append("footer TLP value has no explicit colour set")
        elif hexv.upper() in ORANGE_ISH:
            fails.append("footer TLP value is still orange (%s) — must be house black %s"
                         % (hexv, ABBEY))
        elif hexv.upper() != ABBEY:
            notes.append("NOTE: footer TLP colour is %s, expected house black %s" % (hexv, ABBEY))
        else:
            notes.append("footer TLP value renders house black %s, regular weight  OK" % ABBEY)
        if tlp_run.font.bold:
            notes.append("NOTE: footer TLP value is still bold")
        if tlp_run.font.italic:
            notes.append("NOTE: footer TLP value is still italic")

    # REPETITION CONTROL — the topic must not repeat inside 90 days with an
    # unchanged tactic fingerprint. Nothing kills an awareness programme faster
    # than the same post every week.
    if topic_key and ledger_path and os.path.exists(ledger_path):
        rows = []
        for line in open(ledger_path, encoding="utf-8"):
            if line.startswith("|") and "`" in line:
                cols = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cols) >= 4 and re.match(r"^\d{4}-\d{2}-\d{2}$", cols[0]):
                    rows.append({"date": cols[0], "awr": cols[1],
                                 "topic": cols[2].strip("`"), "fp": cols[3]})
        today = datetime.date.today()
        prior = [r for r in rows if r["topic"] == topic_key and r["awr"] != this_awr]
        if prior:
            last = max(prior, key=lambda r: r["date"])
            age = (today - datetime.date.fromisoformat(last["date"])).days
            if age < 90:
                if fingerprint and fingerprint.strip() and fingerprint.strip() != last["fp"].strip():
                    notes.append("REPEAT ALLOWED: topic %r last used %s (%d days ago) but the "
                                 "tactic fingerprint CHANGED. The post must be framed as what "
                                 "changed, not as a re-explanation." % (topic_key, last["date"], age))
                else:
                    fails.append("REPETITION — topic %r was posted as %s on %s (%d days ago) with "
                                 "the SAME tactic fingerprint. Pick a different topic or state "
                                 "what materially changed."
                                 % (topic_key, last["awr"], last["date"], age))
            else:
                notes.append("topic %r last used %s (%d days ago, outside the 90-day window)  OK"
                             % (topic_key, last["date"], age))
        else:
            notes.append("topic %r is new to the ledger  OK" % topic_key)
    elif topic_key:
        notes.append("NOTE: ledger not found at %r — repetition could not be checked" % ledger_path)

    # readability: no sentence over ~45 words, no paragraph over ~120 words
    body = [p.text.strip() for p in doc.paragraphs if len(p.text.strip()) > 40]
    long_sent = []
    for para in body:
        for sent in re.split(r"(?<=[.!?])\s+", para):
            n = len(sent.split())
            if n > 45:
                long_sent.append((n, sent[:70]))
    if long_sent:
        notes.append("NOTE: %d sentence(s) over 45 words — longest %d words: %r"
                     % (len(long_sent), max(s[0] for s in long_sent),
                        max(long_sent)[1]))
    else:
        notes.append("all sentences under 45 words  OK")
    words = len(text.split())
    notes.append("total length %d words (2 pages is fine — April attaches the document)" % words)

    print("=" * 72)
    print(os.path.basename(path))
    for n in notes:
        print("  " + n)
    if fails:
        for f in fails:
            print("  FAIL: " + f)
        return False
    print("  PASS — safe to post to an all-employee channel")
    return True

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--topic-key")
    ap.add_argument("--fingerprint")
    ap.add_argument("--ledger")
    ap.add_argument("--awr")
    ap.add_argument("--channel", action="append", metavar="CHANNEL",
                    help="Declare the channel this post is ABOUT, so channel-specific "
                         "instructions are required only where they make sense. Repeatable. "
                         "Valid: 'phone call', 'pasted command', or 'none'. Omit entirely to "
                         "fall back to inferring the channel from the body text, which cannot "
                         "tell a channel the post is about from one it rules out.")
    a = ap.parse_args()
    sys.exit(0 if check(a.docx, a.topic_key, a.fingerprint, a.ledger, a.awr,
                        channels=a.channel) else 1)
