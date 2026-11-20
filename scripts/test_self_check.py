"""The self check loop: lint, record each round, send failures back, and stop honestly."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import self_check as sc  # noqa: E402

CLEAN = "We assess the actor is likely to return. We hold this with moderate confidence [1]."
BAD = "It is likely, with high confidence, to return."
ALL_PASS = {g: "pass" for g in ("sources", "cve_facts", "house_rules", "consistency", "reasoning")}


class SelfCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.out = Path(tempfile.mkdtemp())
        sc.OUT = self.out
        self.list = self.out / "state" / "_work" / "review.json"
        self.fix = self.out / "state" / "_work" / "fix.json"
        self.list.parent.mkdir(parents=True)

    def _round(self, text: str, verdict: str, round_no: int, findings: list | None = None) -> int:
        doc = self.out / "bulletins" / "CTI26-01-Test.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(text, encoding="utf-8")
        review = {"id": "CTI26-01", "verdict": verdict, "summary": "checked",
                  "checks": ALL_PASS, "findings": findings or []}
        sc.write_json(self.out / "state" / "reviews" / "CTI26-01.json", review)
        batch = [{"id": "CTI26-01", "kind": "bulletin", "path": "bulletins/CTI26-01-Test.md"}]
        self.list.write_text(json.dumps({"batch": batch}), encoding="utf-8")
        return sc.cmd_record(self.list, round_no, 3, self.fix)

    def _record(self) -> dict:
        return json.loads((self.out / "state" / "guardrails" / "CTI26-01.json").read_text())

    def test_clean_first_round_is_verified_and_nothing_is_sent_back(self) -> None:
        self.assertEqual(self._round(CLEAN, "pass", 1), 3)
        record = self._record()
        self.assertEqual(record["status"], "verified")
        self.assertEqual(record["gates"]["wording"], "pass")
        self.assertFalse(self.fix.exists())

    def test_lint_error_fails_even_when_the_reviewer_passed(self) -> None:
        self.assertEqual(self._round(BAD, "pass", 1), 0)
        record = self._record()
        self.assertEqual(record["status"], "fixing")
        self.assertEqual(record["gates"]["wording"], "flag")
        sent = json.loads(self.fix.read_text())["batch"][0]
        self.assertEqual(sent["lint"][0]["rule"], "mixed-confidence-likelihood")

    def test_fixed_document_is_self_corrected(self) -> None:
        finding = [{"claim": "3 victims", "problem": "source says 2", "source": "x"}]
        self._round(CLEAN, "flag", 1, finding)
        self.assertEqual(self._round(CLEAN, "pass", 2), 3)
        record = self._record()
        self.assertEqual(record["status"], "self-corrected")
        self.assertEqual(len(record["rounds"]), 2)
        self.assertEqual(record["open_issues"], [])

    def test_still_failing_on_the_last_round_needs_a_human(self) -> None:
        finding = [{"claim": "3 victims", "problem": "source says 2", "source": "x"}]
        for round_no in (1, 2):
            self._round(CLEAN, "flag", round_no, finding)
        self.assertEqual(self._round(CLEAN, "flag", 3, finding), 3)
        record = self._record()
        self.assertEqual(record["status"], "needs-human")
        self.assertIn("source says 2", record["open_issues"][0])

    def test_a_new_run_starts_fresh(self) -> None:
        self._round(BAD, "pass", 1)
        self._round(CLEAN, "pass", 1)
        self.assertEqual(self._record()["status"], "verified")

    def test_a_flagged_gate_fails_even_with_a_pass_verdict(self) -> None:
        sc.write_json(self.out / "state" / "reviews" / "CTI26-01.json",
                      {"verdict": "pass", "checks": {**ALL_PASS, "reasoning": "flag"}})
        doc = self.out / "d.md"
        doc.write_text(CLEAN, encoding="utf-8")
        record = sc.record_item({"id": "CTI26-01", "path": "d.md"}, 1, 3)
        self.assertEqual(record["status"], "fixing")

    def test_missing_review_check_is_unchecked_not_pass(self) -> None:
        gates = sc.gate_results({"verdict": "pass", "checks": {"sources": "pass"}}, [])
        self.assertEqual(gates["sources"], "pass")
        self.assertEqual(gates["reasoning"], "unchecked")

    def test_finalize_routes_an_unfixed_document_with_the_fixers_reason(self) -> None:
        self._round(BAD, "pass", 1)
        note = self.out / "state" / "_work" / "fixes" / "CTI26-01.md"
        note.parent.mkdir(parents=True)
        note.write_text("The only source was taken down.", encoding="utf-8")
        sc.cmd_finalize()
        record = self._record()
        self.assertEqual(record["status"], "needs-human")
        self.assertEqual(record["fix_note"], "The only source was taken down.")


if __name__ == "__main__":
    unittest.main()
