"""Branded PDFs: made once per report version, served inline or as a download."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cti_console.api import create_app
from cti_console.config import Settings
from cti_console.pdf import PdfCache, PdfError

FAKE_PDF = b"%PDF-1.7\n% made by the test converter\n"


class FakeWord:
    """Stands in for Word: writes a tiny PDF and counts the calls."""

    def __init__(self) -> None:
        self.calls: list[Path] = []

    def __call__(self, source: Path, target: Path) -> None:
        self.calls.append(source)
        target.write_bytes(FAKE_PDF)


@pytest.fixture()
def word() -> FakeWord:
    return FakeWord()


@pytest.fixture()
def client(settings: Settings, word: FakeWord) -> TestClient:
    return TestClient(
        create_app(settings, converter=word, pdf_ready=True), base_url="http://127.0.0.1"
    )


def test_html_says_a_pdf_can_be_made(client: TestClient) -> None:
    assert client.get("/api/deliverables/CTI26-01/html").json()["pdf"] is True


def test_pdf_inline_and_framable_by_the_console_only(client: TestClient) -> None:
    response = client.get("/api/deliverables/CTI26-01/pdf")
    assert response.status_code == 200
    assert response.content == FAKE_PDF
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")
    assert "CTI26-01-Good_Bulletin.pdf" in response.headers["content-disposition"]
    assert "frame-ancestors 'self'" in response.headers["content-security-policy"]
    # every other response still refuses to be framed
    other = client.get("/api/deliverables/CTI26-01/html")
    assert "frame-ancestors 'none'" in other.headers["content-security-policy"]


def test_pdf_download(client: TestClient) -> None:
    response = client.get("/api/deliverables/TH26-01/pdf", params={"download": True})
    assert response.headers["content-disposition"].startswith("attachment")
    assert "TH26-01-Sample_Hunt.pdf" in response.headers["content-disposition"]


def test_pdf_is_made_once_then_cached(client: TestClient, word: FakeWord) -> None:
    assert client.get("/api/deliverables/CTI26-01/pdf/ready").json()["bytes"] == len(FAKE_PDF)
    client.get("/api/deliverables/CTI26-01/pdf")
    client.get("/api/deliverables/CTI26-01/pdf", params={"download": True})
    assert len(word.calls) == 1


def test_rebuilt_report_gets_a_fresh_pdf(settings: Settings, word: FakeWord) -> None:
    source = settings.out_dir / "bulletin-scan/bulletins/2026/CTI26-01-Good_Bulletin.docx"
    cache = PdfCache(settings.cache_dir / "pdf", word)
    first = cache.get("CTI26-01", source)
    stat = source.stat()
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
    second = cache.get("CTI26-01", source)
    assert first != second
    assert len(word.calls) == 2
    assert not first.exists()  # the old version's PDF is dropped
    assert second.is_file()


def test_cache_cleanup_keeps_other_reports(settings: Settings, word: FakeWord) -> None:
    folder = settings.cache_dir / "pdf"
    folder.mkdir(parents=True)
    neighbour = folder / "CTI26-01-extra-0123456789abcdef.pdf"
    neighbour.write_bytes(FAKE_PDF)
    source = settings.out_dir / "bulletin-scan/bulletins/2026/CTI26-01-Good_Bulletin.docx"
    PdfCache(folder, word).get("CTI26-01", source)
    assert neighbour.is_file()


def test_failed_conversion_leaves_no_file(settings: Settings) -> None:
    def broken(source: Path, target: Path) -> None:
        target.write_bytes(b"half")
        raise PdfError("Word could not convert the report", 502)

    client = TestClient(
        create_app(settings, converter=broken, pdf_ready=True), base_url="http://127.0.0.1"
    )
    response = client.get("/api/deliverables/CTI26-01/pdf/ready")
    assert response.status_code == 502
    assert "Word could not convert" in response.json()["detail"]
    assert list((settings.cache_dir / "pdf").glob("*")) == []


def test_no_word_means_503(settings: Settings, word: FakeWord) -> None:
    client = TestClient(
        create_app(settings, converter=word, pdf_ready=False), base_url="http://127.0.0.1"
    )
    assert client.get("/api/deliverables/CTI26-01/html").json()["pdf"] is False
    assert client.get("/api/deliverables/CTI26-01/pdf").status_code == 503
    assert word.calls == []


@pytest.mark.parametrize(
    "path",
    [
        "/api/deliverables/CTI26-77/pdf",  # unknown ID
        "/api/deliverables/CTI26-99/pdf/ready",  # only exists under state/
    ],
)
def test_pdf_lookup_rejects(client: TestClient, word: FakeWord, path: str) -> None:
    assert client.get(path).status_code == 404
    assert word.calls == []
