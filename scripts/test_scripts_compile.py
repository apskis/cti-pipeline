"""Every pipeline script must at least parse.

The entrypoint runs these scripts between Claude sessions. A syntax error there does not
fail the run: it silently skips the builder passes, so the scan's IDs are never built.
"""

import ast
import unittest
from pathlib import Path

ROOTS = [
    Path(__file__).resolve().parent,
    Path(__file__).resolve().parent.parent / "core" / ".claude" / "skills",
]


class ScriptsCompile(unittest.TestCase):
    def test_every_script_parses(self) -> None:
        scripts = [p for root in ROOTS if root.is_dir() for p in root.rglob("*.py")]
        self.assertTrue(scripts, "no scripts found")
        for path in scripts:
            with self.subTest(script=str(path)):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


if __name__ == "__main__":
    unittest.main()
