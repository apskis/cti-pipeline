"""The bulletin builder must never split a question into letters.

Builder passes wrote `questions` as plain strings. The builder read each string as a
[team, question] pair, so "Does GeneLabs ..." rendered as "D:" and "o". These tests feed
every shape a spec has used and check that no one character paragraph comes out.
"""

import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "core" / ".claude" / "skills" / "cti-bulletin" / "scripts" / "build_bulletin.py"

try:
    import docx
except ImportError:  # python-docx is in the image; skip where it is not installed
    docx = None


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_bulletin", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _paragraphs(doc) -> list[str]:
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def _lone(paras: list[str]) -> list[str]:
    return [p for p in paras if len(p.strip("▪•-– \t").rstrip(":").strip()) <= 1]


@unittest.skipIf(docx is None, "python-docx not installed")
class Questions(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bb = _load_builder()

    def _render(self, fn, value) -> tuple[list[str], str]:
        doc = docx.Document()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            fn(doc, value)
        return _paragraphs(doc), err.getvalue()

    def test_plain_strings_render_whole(self) -> None:
        # The exact shape of the CTI26-131 spec.
        qs = ["Are Ivanti Connect Secure appliances deployed?", "Are they internet-exposed?"]
        paras, err = self._render(self.bb.add_questions, qs)
        self.assertEqual(_lone(paras), [])
        self.assertTrue(any("Ivanti Connect Secure" in p for p in paras))
        self.assertIn("no team label", err)

    def test_one_bare_string_renders_whole(self) -> None:
        paras, _ = self._render(self.bb.add_questions, "Is Faspex deployed?")
        self.assertEqual(len(paras), 1)
        self.assertTrue(paras[0].endswith("Is Faspex deployed?"))

    def test_pairs_still_group_by_team(self) -> None:
        qs = [["SOC", "Any new admin accounts?"], ["SOC", "Any bulk downloads?"], ["Leadership", "Timeline?"]]
        paras, err = self._render(self.bb.add_questions, qs)
        self.assertEqual(paras.count("SOC:"), 1)
        self.assertEqual(_lone(paras), [])
        self.assertEqual(err, "")

    def test_grouped_dicts_with_string_items(self) -> None:
        qs = [{"audience": "SOC", "items": "Any new admin accounts?"}]
        paras, _ = self._render(self.bb.add_questions, qs)
        self.assertEqual(_lone(paras), [])
        self.assertTrue(any("Any new admin accounts?" in p for p in paras))

    def test_recommended_actions_plain_strings(self) -> None:
        paras, err = self._render(self.bb.add_recommended_actions, ["Patch Faspex.", "Rotate keys."])
        self.assertEqual(_lone(paras), [])
        self.assertIn("Patch Faspex.", " ".join(paras))
        self.assertIn("no team label", err)

    def test_recommended_actions_string_items(self) -> None:
        groups = [{"audience": "IT", "target": "7 days", "items": "Patch Faspex."}]
        paras, _ = self._render(self.bb.add_recommended_actions, groups)
        self.assertEqual(_lone(paras), [])
        self.assertTrue(any("Patch Faspex." in p for p in paras))


if __name__ == "__main__":
    unittest.main()
