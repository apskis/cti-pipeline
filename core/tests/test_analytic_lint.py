"""The analytic linter flags the phrasing that travels with thinking errors, and nothing else."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE / "tools"))

import analytic_lint  # noqa: E402
from analytic_lint import lint_text  # noqa: E402


def rules(text: str) -> set[str]:
    return {f.rule for f in lint_text([text])}


@pytest.mark.parametrize(
    "text",
    [
        "We assess with moderate confidence that the actor is likely to target sequencing firms.",
        "It is very likely, high confidence, that the flaw will be exploited.",
    ],
)
def test_likelihood_and_confidence_in_one_sentence_is_an_error(text: str) -> None:
    assert "mixed-confidence-likelihood" in rules(text)


def test_split_sentences_pass() -> None:
    text = (
        "We assess the actor is likely to target sequencing firms. "
        "We hold this with moderate confidence because only one vendor reports it."
    )
    assert rules(text) == set()


@pytest.mark.parametrize("text", ["Confidence: Medium-High.", "Low to moderate confidence."])
def test_blended_confidence_is_an_error(text: str) -> None:
    assert "blended-confidence" in rules(text)


def test_cve_relevance_scale_is_not_a_blend() -> None:
    # MEDIUM-HIGH is a defined level on the CVE brief's relevance scale, not a confidence blend.
    assert rules("MEDIUM-HIGH") == set()
    assert rules("Relevance: LOW-MEDIUM, product in the tech profile.") == set()


def test_json_rating_is_judged_with_its_key(tmp_path: Path) -> None:
    path = tmp_path / "summary.json"
    path.write_text(json.dumps({"hunts": [{"confidence": "Medium-High"}]}), encoding="utf-8")
    assert {f.rule for f in lint_text(analytic_lint.read_blocks(path))} == {"blended-confidence"}


def test_severity_range_outside_a_confidence_claim_is_not_a_blend() -> None:
    assert "blended-confidence" not in rules("Severity moved from low to high over the week.")


def test_certainty_words_warn_but_almost_certainly_does_not() -> None:
    assert "absolute-certainty" in rules("This definitely came from the same operator.")
    assert "absolute-certainty" not in rules("The operator will almost certainly return.")


def test_asserted_proof_warns_but_negated_proof_does_not() -> None:
    assert "absolute-certainty" in rules("The shared loader proves both campaigns are one actor.")
    assert rules("A hunt can fail to find something; it cannot prove absence.") == set()
    assert rules("The result does not prove the host is clean of the implant.") == set()


def test_listed_scale_is_not_a_blend() -> None:
    assert rules("State the confidence (High / Moderate / Low) and the reason.") == set()


def test_absent_section_is_not_a_safety_claim() -> None:
    assert rules("The hand-off carries no risk assessment and no exposure narrative.") == set()


def test_non_icd_likelihood_warns() -> None:
    assert "non-standard-likelihood" in rules("Exploitation is highly likely this quarter.")


def test_remote_code_execution_is_not_a_likelihood_term() -> None:
    text = "CVE-2026-1234 allows remote code execution with high confidence in the PoC."
    assert rules(text) == set()


def test_clean_result_without_coverage_warns() -> None:
    assert "absence-as-proof" in rules("The company was not compromised.")


def test_clean_result_with_coverage_passes() -> None:
    text = "No sensored host was affected in the 14 day Falcon window; the rest are TG-12."
    assert "absence-as-proof" not in rules(text)


def test_unsourced_attribution_warns_and_sourced_does_not() -> None:
    assert "attribution-without-confidence" in rules("The intrusion was carried out by APT41.")
    assert "attribution-without-confidence" not in rules(
        "Mandiant reported the intrusion was carried out by APT41 [3]."
    )
    assert "attribution-without-confidence" not in rules(
        "The intrusion was likely carried out by APT41."
    )


def test_quoted_source_text_is_skipped() -> None:
    text = 'The vendor wrote "we assess with high confidence this is highly likely to continue".'
    assert rules(text) == set()


def test_json_strings_are_walked(tmp_path: Path) -> None:
    path = tmp_path / "analysis_result.json"
    path.write_text(json.dumps({"summary": {"text": ["The estate is safe."]}}), encoding="utf-8")
    assert {f.rule for f in lint_text(analytic_lint.read_blocks(path))} == {"absence-as-proof"}


def test_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    clean = tmp_path / "clean.md"
    clean.write_text("It is likely.\n\nWe hold this with low confidence.", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text("It is likely, with high confidence, to recur.", encoding="utf-8")
    assert analytic_lint.main([str(clean)]) == 0
    assert analytic_lint.main([str(bad)]) == 1
    assert analytic_lint.main([str(tmp_path / "missing.md")]) == 2
    assert "mixed-confidence-likelihood" in capsys.readouterr().out
