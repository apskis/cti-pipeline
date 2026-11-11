from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cti_console.api import create_app
from cti_console.config import Settings


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_summary(client: TestClient) -> None:
    body = client.get("/api/summary").json()
    assert body["counts"]["bulletin"] == 2
    assert len(body["stages"]) == 6


def test_runs_newest_first_and_filtered(client: TestClient) -> None:
    runs = client.get("/api/runs", params={"component": "bulletin-scan"}).json()
    assert [r["kind"] for r in runs] == ["build only", "scan", "scan"]
    assert runs[1]["cost_usd"] == 9.0


def test_deliverables_filters(client: TestClient) -> None:
    assert len(client.get("/api/deliverables").json()) == 5
    broken = client.get("/api/deliverables", params={"status": "broken"}).json()
    assert [d["id"] for d in broken] == ["CTI26-02"]
    hits = client.get("/api/deliverables", params={"q": "sample"}).json()
    assert [d["id"] for d in hits] == ["TH26-01"]


def test_rejects_bad_limits(client: TestClient) -> None:
    assert client.get("/api/runs", params={"limit": 0}).status_code == 422
    assert client.get("/api/deliverables", params={"q": "x" * 101}).status_code == 422


def test_read_only(client: TestClient) -> None:
    for path in ("/api/summary", "/api/runs", "/api/deliverables"):
        assert client.post(path).status_code == 405
        assert client.delete(path).status_code == 405


def test_no_docs_and_cors_only_for_the_frontend(client: TestClient) -> None:
    assert client.get("/docs").status_code == 404
    ok = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers
    assert ok.headers["x-content-type-options"] == "nosniff"


def test_deliverable_html(client: TestClient) -> None:
    response = client.get("/api/deliverables/CTI26-01/html")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "CTI26-01"
    assert "CTI26-01 paragraph 3 of a complete bulletin." in body["html"]
    assert response.headers["content-security-policy"].startswith("default-src 'none'")


def test_deliverable_file_downloads(client: TestClient) -> None:
    response = client.get("/api/deliverables/TH26-01/file")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert "TH26-01-Sample_Hunt.docx" in response.headers["content-disposition"]
    assert response.content[:2] == b"PK"  # a .docx is a zip


@pytest.mark.parametrize(
    ("path", "status"),
    [
        ("/api/deliverables/CTI26-77/html", 404),  # unknown ID
        ("/api/deliverables/CTI26-99/file", 404),  # only exists under state/
        ("/api/deliverables/..%2F..%2Fsecrets/file", 404),  # never matches the route
        ("/api/deliverables/a b/html", 422),
    ],
)
def test_deliverable_lookup_rejects(client: TestClient, path: str, status: int) -> None:
    assert client.get(path).status_code == status


def test_run_detail(client: TestClient) -> None:
    runs = client.get("/api/runs", params={"component": "bulletin-scan"}).json()
    body = client.get(f"/api/runs/{runs[1]['id']}").json()
    assert [s["label"] for s in body["sessions"]] == ["scan", "build-1", "build-2"]
    assert len(body["stages"]) == 6
    assert [d["id"] for d in body["written"]] == ["CTI26-02"]
    assert body["report"]["name"] == "scan-2026-11-10.md"
    html = body["report"]["html"]
    assert "<table>" in html and "<h1>Scan</h1>" in html
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_run_without_report_or_stages(client: TestClient) -> None:
    runs = client.get("/api/runs").json()
    rebuild = next(r for r in runs if r["kind"] == "build only")
    body = client.get(f"/api/runs/{rebuild['id']}").json()
    assert body["stages"] == [] and body["report"] is None


def test_run_rejects(client: TestClient) -> None:
    assert client.get("/api/runs/bulletin-scan-20990101T000000").status_code == 404
    assert client.get("/api/runs/..%2Fstate").status_code in (404, 422)
    assert client.get("/api/runs/Bulletin-x").status_code == 422


def test_cves(client: TestClient) -> None:
    body = client.get("/api/cves").json()
    assert body["register"] == "bulletin-scan/registers/CVE_Register_2026.xlsx"
    first, second = body["cves"]
    assert first["id"] == "CVE-2026-0001" and first["exploited"] is True
    assert first["cvss_score"] == 9.8 and first["kev_added"] == "2026-11-09"
    assert first["hunt_id"] == "TH26-01" and first["bulletin_id"] == "CTI26-01"
    assert "validation_spl" not in first
    assert second["exploited"] is False and second["cvss_score"] is None
    assert second["kev_added"] is None and second["bulletin_id"] is None
    assert second["hunt_id"] is None  # a shifted row's text is not linked as an ID
