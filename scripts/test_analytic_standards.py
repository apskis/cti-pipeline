"""Every prompt that writes an intelligence judgement points at the analytic standards skill.

The bias guardrails only work if each component reads them. A prompt rewritten later without
the pointer would quietly drop them, so this test fails instead.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "core" / ".claude" / "skills" / "cti-analytic-standards" / "SKILL.md"
LINTER = REPO / "core" / "tools" / "analytic_lint.py"

# Prompts that rank, rate, rule on or attribute anything. documentation-sync and
# program-console only copy measured numbers, so they carry no judgement to guard.
JUDGEMENT_PROMPTS = [
    "components/bulletin-scan/task.md",
    "components/bulletin-scan/task-build.md",
    "components/bulletin-scan/task-review.md",
    "components/threat-hunting/task.md",
    "components/reporting/task.md",
    "components/perimeter-scan/task.md",
    "core/.claude/skills/cti-report/SKILL.md",
]
ICD_203_TERMS = [
    "almost no chance", "very unlikely", "unlikely", "roughly even chance",
    "likely", "very likely", "almost certain",
]


class AnalyticStandardsTest(unittest.TestCase):
    def test_skill_and_linter_exist(self) -> None:
        self.assertTrue(SKILL.is_file())
        self.assertTrue(LINTER.is_file())

    def test_skill_carries_the_fixed_scales(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: \"cti-analytic-standards\""))
        for term in ICD_203_TERMS:
            with self.subTest(term=term):
                self.assertRegex(text, rf"\|\s*{re.escape(term)}\s*\|")
        for level in ("High", "Moderate", "Low"):
            with self.subTest(level=level):
                self.assertIn(f"| **{level}** |", text)

    def test_every_judgement_prompt_points_at_the_skill(self) -> None:
        for rel in JUDGEMENT_PROMPTS:
            with self.subTest(prompt=rel):
                text = (REPO / rel).read_text(encoding="utf-8")
                self.assertIn("cti-analytic-standards", text)
                self.assertIn("analytic_lint.py", text)


if __name__ == "__main__":
    unittest.main()
