"""The prompt renderer: every component fills in for every committed company."""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
RENDER = HERE / "render_task.py"
COMPONENTS = sorted(p.name for p in (REPO / "components").iterdir() if p.is_dir())
COMPANIES = {
    "genelabs": REPO / "config" / "companies" / "genelabs",
    "starter": REPO / "config" / "companies" / "_starter",
}
# A placeholder the renderer would fill; {{En}} style markers in the prompts are literal.
LEFT_OVER = re.compile(r"\{\{\s*[a-z_]+\s*\}\}")


def render(component: str, company_dir: Path, out: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "CTI_COMPANY_DIR": str(company_dir)}
    return subprocess.run(
        [sys.executable, str(RENDER), component, str(out)],
        env=env, capture_output=True, text=True, check=False,
    )


class RenderTaskTest(unittest.TestCase):
    def test_every_component_renders_for_every_company(self) -> None:
        for label, folder in COMPANIES.items():
            for component in COMPONENTS:
                with self.subTest(company=label, component=component), tempfile.TemporaryDirectory() as tmp:
                    result = render(component, folder, Path(tmp))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    task = (Path(tmp) / "task.md").read_text(encoding="utf-8")
                    self.assertTrue(task.startswith("> **Company for this run:"))
                    for page in Path(tmp).glob("*.md"):
                        text = page.read_text(encoding="utf-8")
                        self.assertIsNone(LEFT_OVER.search(text), page.name)
                        self.assertNotIn(f"components/{component}/", text)

    def test_genelabs_prompts_name_genelabs_and_a_new_company_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            render("bulletin-scan", COMPANIES["genelabs"], Path(tmp))
            task = (Path(tmp) / "task.md").read_text(encoding="utf-8")
            self.assertIn("at GeneLabs LLC.", task)
            self.assertIn("for each of the company's domains (genelabs.com)", task)
        with tempfile.TemporaryDirectory() as tmp:
            render("bulletin-scan", COMPANIES["starter"], Path(tmp))
            task = (Path(tmp) / "task.md").read_text(encoding="utf-8")
            self.assertIn("at New company.", task)
            self.assertNotIn("genelabs.com", task)
            self.assertIn("report this check as NOT SET UP", task)

    def test_an_unknown_placeholder_stops_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            component = REPO / "components" / "_render_test"
            component.mkdir()
            try:
                (component / "task.md").write_text("Hello {{no_such_field}}\n", encoding="utf-8")
                result = render("_render_test", COMPANIES["genelabs"], Path(tmp))
            finally:
                (component / "task.md").unlink()
                component.rmdir()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no_such_field", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
