"""The shell check must catch a bulletin with one broken list section.

On 2026-11-10, 37 bulletins on disk had "Questions to Ask" rendered one character per
paragraph ("D:", "o", "r"). The old rule needed more than half the paragraphs broken, so
every one of them counted as built and was never rebuilt.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pending_deliverables as pd  # noqa: E402

try:
    import docx
except ImportError:  # python-docx is in the image; skip where it is not installed
    docx = None

BULLET = "▪  "
BODY = [f"CTI26-999 sentence {i} of a complete, readable bulletin." for i in range(25)]
# The real broken section from CTI26-145: an audience heading and its bullets, per letter.
BROKEN_SECTION = ["A:", BULLET + "r", "I:", BULLET + "s", BULLET + "s", "H:", BULLET + "a"]


class CountLoneChars(unittest.TestCase):
    def test_counts_broken_headings_and_bullets(self) -> None:
        self.assertEqual(pd.count_lone_chars(BROKEN_SECTION), 7)

    def test_ignores_real_text(self) -> None:
        real = ["SOC:", BULLET + "Have we seen new admin accounts?", "[1]  SecurityWeek"]
        self.assertEqual(pd.count_lone_chars(real), 0)


@unittest.skipIf(docx is None, "python-docx not installed")
class ShellReason(unittest.TestCase):
    def _write(self, paras: list[str]) -> Path:
        tmp = Path(tempfile.mkdtemp())
        d = docx.Document()
        for text in paras:
            d.add_paragraph(text)
        path = tmp / "CTI26-999-Test.docx"
        d.save(str(path))
        return path

    def test_one_broken_section_is_a_shell(self) -> None:
        why = pd.shell_reason(self._write(BODY + BROKEN_SECTION), "CTI26-999", "bulletin")
        self.assertIsNotNone(why)
        self.assertIn("single character", why)

    def test_smallest_real_break_is_a_shell(self) -> None:
        # CTI26-131 broke with one heading and two bullets: "A:", "r", "r".
        paras = BODY + ["A:", BULLET + "r", BULLET + "r"]
        self.assertIsNotNone(pd.shell_reason(self._write(paras), "CTI26-999", "bulletin"))

    def test_complete_bulletin_passes(self) -> None:
        self.assertIsNone(pd.shell_reason(self._write(BODY), "CTI26-999", "bulletin"))

    def test_two_stray_characters_pass(self) -> None:
        paras = BODY + [BULLET + "x", "y"]
        self.assertIsNone(pd.shell_reason(self._write(paras), "CTI26-999", "bulletin"))


if __name__ == "__main__":
    unittest.main()
