"""The Reviewer's queue: what this run built and nobody has reviewed yet."""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import review_queue as rq  # noqa: E402

try:
    import docx
except ImportError:  # python-docx is in the image; skip where it is not installed
    docx = None


@unittest.skipIf(docx is None, "python-docx not installed")
class Candidates(unittest.TestCase):
    def setUp(self) -> None:
        self.out = Path(tempfile.mkdtemp())
        rq.OUT = self.out
        rq.REVIEWS = self.out / "state" / "reviews"

    def _doc(self, rel: str, ident: str, paras: int = 20, mtime: float | None = None) -> Path:
        path = self.out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        d = docx.Document()
        for i in range(paras):
            d.add_paragraph(f"{ident} paragraph {i} of a complete document.")
        d.save(str(path))
        if mtime is not None:
            os.utime(path, (mtime, mtime))
        return path

    def _review(self, ident: str, mtime: float) -> None:
        path = rq.review_path(ident)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"id": ident, "verdict": "pass"}))
        os.utime(path, (mtime, mtime))

    def _ids(self, since: float | None = None) -> list[str]:
        return [i["id"] for i in rq.candidates(since)]

    def test_unreviewed_document_is_queued(self) -> None:
        self._doc("bulletins/2026/CTI26-01-A.docx", "CTI26-01")
        self.assertEqual(self._ids(), ["CTI26-01"])

    def test_review_newer_than_document_counts(self) -> None:
        now = time.time()
        self._doc("bulletins/2026/CTI26-01-A.docx", "CTI26-01", mtime=now - 100)
        self._review("CTI26-01", now)
        self.assertEqual(self._ids(), [])

    def test_rebuilt_document_is_reviewed_again(self) -> None:
        now = time.time()
        self._doc("bulletins/2026/CTI26-01-A.docx", "CTI26-01", mtime=now)
        self._review("CTI26-01", now - 100)
        self.assertEqual(self._ids(), ["CTI26-01"])

    def test_since_keeps_only_this_runs_documents(self) -> None:
        now = time.time()
        self._doc("bulletins/2026/CTI26-01-Old.docx", "CTI26-01", mtime=now - 86400)
        self._doc("bulletins/2026/CTI26-02-New.docx", "CTI26-02", mtime=now)
        self.assertEqual(self._ids(since=now - 60), ["CTI26-02"])

    def test_document_fixed_after_its_review_is_queued_whatever_its_date(self) -> None:
        now = time.time()
        self._doc("hunts/packages/TH26-08-H.docx", "TH26-08", paras=35, mtime=now - 3600)
        self._review("TH26-08", now - 7200)
        self.assertEqual(self._ids(since=now - 60), ["TH26-08"])

    def test_shells_and_scratch_and_briefs_are_skipped(self) -> None:
        self._doc("bulletins/2026/CTI26-03-Shell.docx", "CTI26-03", paras=3)
        self._doc("state/_work/CTI26-04-Draft.docx", "CTI26-04")
        self._doc("registers/CVE-VM-2026-11-12.docx", "CVE-VM-2026-11-12")
        self.assertEqual(self._ids(), [])

    def test_hunt_and_awareness_are_queued_with_their_kind(self) -> None:
        self._doc("hunts/packages/TH26-01-H.docx", "TH26-01", paras=35)
        self._doc("employee-posts/AWR-2026-11-12-Post.docx", "AWR-2026-11-12", paras=10)
        kinds = {i["id"]: i["kind"] for i in rq.candidates(None)}
        self.assertEqual(kinds, {"TH26-01": "hunt", "AWR-2026-11-12": "awareness"})


if __name__ == "__main__":
    unittest.main()
