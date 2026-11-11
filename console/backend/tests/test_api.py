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
