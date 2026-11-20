#!/usr/bin/env python3
"""Lint a finished CTI document for wording that signals a thinking error.

WHY A LINTER AND NOT JUST THE SKILL. The cti-analytic-standards skill tells every component
how to write a judgement. A rule in a document is checked by whoever remembers it; this is
checked every time. It cannot tell whether an analysis is right. It catches the phrasing that
usually travels with a wrong one: confidence and likelihood fused into one claim (ICD 203),
blended confidence levels, absolute certainty, invented likelihood words, a clean result
written as proof of safety, and attribution with no stated confidence.

Text inside double quotes is skipped. Quoting a source word for word is house policy, and the
hedging inside the quote is the source's, not ours.

EXIT CODES
  0  clean, or warnings only
  1  one or more ERRORS: fix the wording before the document is filed
  2  a file could not be read

Usage:
  python analytic_lint.py report.docx analysis_result.json notes.md
  python analytic_lint.py -          (read plain text from stdin)
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Level = Literal["ERROR", "WARN"]


@dataclass(frozen=True)
class Finding:
    level: Level
    rule: str
    message: str
    excerpt: str
    block: int


# ICD 203 likelihood terms and their alternatives. "remote" is left out on purpose: in this
# domain it almost always means "remote code execution", not a 1 to 5% probability.
LIKELIHOOD = re.compile(
    r"\b(almost no chance|very unlikely|highly improbable|unlikely|improbable|"
    r"roughly even (?:chance|odds)|likely|probable|probably|very likely|highly probable|"
    r"almost certain(?:ly)?|nearly certain(?:ly)?)\b",
    re.I,
)
_LEVEL = r"(?:high|moderate|medium|low)"
CONFIDENCE = re.compile(
    rf"\b{_LEVEL}[ -]confidence\b|\bconfidence(?: level)?(?: is| of|:)?\s+{_LEVEL}\b", re.I
)
# No "/": "High / Moderate / Low" is how a scale is listed, not a blend. A blend only counts
# when "confidence" is in the same sentence, because the CVE brief's RELEVANCE scale defines
# MEDIUM-HIGH and LOW-MEDIUM as real levels and must not be flagged.
BLENDED = re.compile(rf"\b{_LEVEL}\s*(?:-|–|—|\bto\b)\s*{_LEVEL}\b", re.I)
CERTAINTY = re.compile(
    r"(?<!almost )(?<!nearly )\b(certainly|definitely|undoubtedly|unquestionably|"
    r"without (?:a )?doubt|beyond (?:any )?doubt|irrefutabl\w*|guaranteed|100 ?%)\b",
    re.I,
)
# "Proves" is only a problem when asserted. "cannot prove absence" is exactly the right
# phrasing, so a negation just before the word clears it.
PROOF = re.compile(r"\b(proves|proven|proof that)\b", re.I)
NEGATION = re.compile(r"\b(not|cannot|can't|never|doesn't|isn't|no)\b[\w ]{0,20}$", re.I)
NON_ICD = re.compile(
    r"\b(highly likely|highly unlikely|extremely likely|extremely unlikely|fairly likely|"
    r"quite likely|somewhat likely|more than likely|in all likelihood|chances are|"
    r"very possibl\w*|quite possibl\w*)\b",
    re.I,
)
SAFE_CLAIM = re.compile(
    r"\b(?:(?:is|are|was|were|has|have)(?:n't| not)|never)(?: been)? "
    r"(?:compromised|affected|impacted|exposed|vulnerable)\b"
    r"|\b(?:is|are|was|were|remains?) (?:safe|clean)\b"
    # "no risk assessment" says a section is absent, not that the estate is safe.
    r"|\bno (?:risk|exposure|impact)\b(?! (?:narrative|assessment|rating|score|argument|section))",
    re.I,
)
# Words that show a negative result was stated with its coverage, which is what makes it honest.
COVERAGE = re.compile(
    r"\b(window|days?|telemetry|sensor\w*|scope|coverage|hosts?|retention|between|since|"
    r"data model|index|falcon|splunk|logs?|visibility|cannot confirm|inconclusive)\b|\bTG-\d+",
    re.I,
)
ATTRIBUTION = re.compile(
    r"\battributed to\b|\b(?:carried out|conducted|perpetrated|orchestrated) by\b"
    r"|\b(?:is|was|are|were) behind\b",
    re.I,
)
# Reporting someone else's attribution with a citation is fine; asserting our own is not.
SOURCED = re.compile(
    r"\baccording to\b|\breport(?:s|ed)?\b|\bsa(?:ys|id)\b|\bclaim(?:s|ed)?\b|\[\d+\]|\{\{E\d+\}\}",
    re.I,
)
QUOTED = re.compile(r"\"[^\"\n]*\"|“[^”\n]*”")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")


def strip_quotes(text: str) -> str:
    """Blank out quoted spans so a source's own hedging is never held against us."""
    return QUOTED.sub(" ", text)


def sentences(text: str) -> Iterator[str]:
    for part in SENTENCE_END.split(text):
        if part.strip():
            yield part.strip()


def _excerpt(sentence: str, limit: int = 120) -> str:
    return sentence if len(sentence) <= limit else sentence[: limit - 3] + "..."


def check_sentence(sentence: str, block: int) -> list[Finding]:
    """Apply every rule to one sentence. Order matters only for readability of the output."""
    found: list[Finding] = []

    def add(level: Level, rule: str, message: str) -> None:
        found.append(Finding(level, rule, message, _excerpt(sentence), block))

    has_confidence = bool(CONFIDENCE.search(sentence))
    has_likelihood = bool(LIKELIHOOD.search(sentence))
    if has_confidence and has_likelihood:
        add("ERROR", "mixed-confidence-likelihood",
            "Likelihood and confidence in one sentence (ICD 203). Split them: say how probable "
            "in one sentence, how sure and why in the next.")
    if BLENDED.search(sentence) and "confidence" in sentence.lower():
        add("ERROR", "blended-confidence",
            "Blended rating. Pick one of High, Moderate or Low and give the reason.")
    if m := CERTAINTY.search(sentence):
        add("WARN", "absolute-certainty",
            f"'{m.group(0)}' claims certainty. Intelligence judgements top out at 'almost "
            "certain'; use a likelihood term or state it as a sourced fact.")
    if (m := PROOF.search(sentence)) and not NEGATION.search(sentence[: m.start()]):
        add("WARN", "absolute-certainty",
            f"'{m.group(0)}' claims proof. Say what the evidence supports and how strongly.")
    if m := NON_ICD.search(sentence):
        add("WARN", "non-standard-likelihood",
            f"'{m.group(0)}' is not on the ICD 203 scale. Use one of: almost no chance, very "
            "unlikely, unlikely, roughly even chance, likely, very likely, almost certain.")
    if (m := SAFE_CLAIM.search(sentence)) and not COVERAGE.search(sentence):
        add("WARN", "absence-as-proof",
            f"'{m.group(0)}' with no coverage stated. Say which telemetry, scope and window, "
            "or write CANNOT CONFIRM / INCONCLUSIVE.")
    hedged = has_confidence or has_likelihood or SOURCED.search(sentence)
    if ATTRIBUTION.search(sentence) and not hedged:
        add("WARN", "attribution-without-confidence",
            "Attribution with no confidence, likelihood or source. Cite who attributes it, or "
            "state our own assessment with a likelihood term and a confidence level.")
    return found


def lint_text(blocks: Iterable[str]) -> list[Finding]:
    """Lint a sequence of text blocks (paragraphs, table cells, JSON strings)."""
    findings: list[Finding] = []
    for index, block in enumerate(blocks, start=1):
        for sentence in sentences(strip_quotes(block)):
            findings.extend(check_sentence(sentence, index))
    return findings


def _json_strings(node: Any) -> Iterator[str]:
    """Yield every string. A string field carries its key ("confidence: Medium-High") so a
    rating is judged in context, the way a reader of the rendered table would see it."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str):
                yield f"{key}: {value}"
            else:
                yield from _json_strings(value)
    elif isinstance(node, list):
        for item in node:
            yield from _json_strings(item)


def _docx_blocks(path: Path) -> list[str]:
    import docx  # Imported here so plain text and JSON linting work without python-docx.

    document = docx.Document(str(path))

    def part_blocks(part: Any) -> Iterator[str]:
        yield from (p.text for p in part.paragraphs)
        for table in part.tables:
            for row in table.rows:
                yield from (cell.text for cell in row.cells)

    blocks = list(part_blocks(document))
    for section in document.sections:
        blocks.extend(part_blocks(section.header))
        blocks.extend(part_blocks(section.footer))
    return [b for b in blocks if b.strip()]


def read_blocks(path: Path) -> list[str]:
    match path.suffix.lower():
        case ".docx":
            return _docx_blocks(path)
        case ".json":
            return list(_json_strings(json.loads(path.read_text(encoding="utf-8"))))
        case _:
            return path.read_text(encoding="utf-8").split("\n\n")


def report(label: str, findings: list[Finding]) -> None:
    for f in findings:
        print(f"{label}:{f.block}: {f.level} {f.rule}: {f.message}\n    > {f.excerpt}")
    errors = sum(f.level == "ERROR" for f in findings)
    print(f"{label}: {errors} error(s), {len(findings) - errors} warning(s)")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    exit_code = 0
    for arg in argv:
        try:
            blocks = sys.stdin.read().split("\n\n") if arg == "-" else read_blocks(Path(arg))
        except (OSError, ValueError) as exc:  # ValueError covers bad JSON and bad docx zips.
            print(f"{arg}: cannot read: {exc}")
            exit_code = 2
            continue
        findings = lint_text(blocks)
        report(arg, findings)
        if exit_code == 0 and any(f.level == "ERROR" for f in findings):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
