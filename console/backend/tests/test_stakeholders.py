"""The stakeholder list: the console's one write, and who each report is for."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from cti_console.api import create_app
from cti_console.audience import name_keys
from cti_console.config import Settings

LOCAL = "http://127.0.0.1"
WRITE = {"X-CTI-Console": "1", "Origin": "http://127.0.0.1:5173"}
PERSON = {
    "name": "Jordan Reyes",
    "role": "SOC lead",
    "team": "SOC",
    "also_known_as": ["Security Operations", "security operations", "  "],
    "email": "jordan@genelabs.example",
    "channel": "teams",
    "receives": ["bulletin", "hunt"],
    "interests": ["phishing"],
    "notes": "",
}


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings, pdf_ready=False), base_url=LOCAL)


def test_empty_until_first_save(client: TestClient, settings: Settings) -> None:
    body = client.get("/api/stakeholders").json()
    assert body == {"exists": False, "has_example": True, "stakeholders": []}
    assert not settings.stakeholders_file.exists()


def test_add_update_remove(client: TestClient, settings: Settings) -> None:
    created = client.post("/api/stakeholders", json=PERSON, headers=WRITE)
    assert created.status_code == 201
    person = created.json()
    assert person["id"].startswith("sh-")
    assert person["also_known_as"] == ["Security Operations"]  # tidied and de-duplicated

    changed = client.put(
        f"/api/stakeholders/{person['id']}", json={**PERSON, "role": "SOC manager"}, headers=WRITE
    )
    assert changed.json()["role"] == "SOC manager"
    saved = json.loads(settings.stakeholders_file.read_text(encoding="utf-8"))
    assert saved["stakeholders"][0]["role"] == "SOC manager"
    assert settings.stakeholders_file.with_suffix(".json.bak").is_file()

    assert client.delete(f"/api/stakeholders/{person['id']}", headers=WRITE).status_code == 204
    assert client.get("/api/stakeholders").json()["stakeholders"] == []
    assert client.delete(f"/api/stakeholders/{person['id']}", headers=WRITE).status_code == 404


@pytest.mark.parametrize(
    "headers",
    [
        {},  # a plain form post, or a script without the header
        {"X-CTI-Console": "1", "Origin": "https://evil.example"},
        {"X-CTI-Console": "yes"},
    ],
)
def test_writes_need_the_console(
    client: TestClient, settings: Settings, headers: dict[str, str]
) -> None:
    assert client.post("/api/stakeholders", json=PERSON, headers=headers).status_code == 403
    assert not settings.stakeholders_file.exists()


def test_other_hosts_are_refused(settings: Settings) -> None:
    rebound = TestClient(create_app(settings, pdf_ready=False), base_url="http://attacker.example")
    assert rebound.get("/api/stakeholders").status_code == 400
    assert rebound.post("/api/stakeholders", json=PERSON, headers=WRITE).status_code == 400


def test_cross_site_preflight_fails(client: TestClient) -> None:
    preflight = client.options(
        "/api/stakeholders",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-cti-console",
        },
    )
    assert "access-control-allow-origin" not in preflight.headers


@pytest.mark.parametrize(
    "change",
    [
        {"email": "not an email"},
        {"name": ""},
        {"channel": "fax"},
        {"receives": ["Bulletins!"]},
        {"interests": ["x" * 41]},
        {"admin": True},  # unknown fields are refused
        {"notes": "x" * 1001},
    ],
)
def test_bad_input_is_refused(client: TestClient, change: dict[str, object]) -> None:
    response = client.post("/api/stakeholders", json={**PERSON, **change}, headers=WRITE)
    assert response.status_code == 422


def test_bad_ids_are_refused(client: TestClient) -> None:
    assert client.put("/api/stakeholders/sh-zzzz", json=PERSON, headers=WRITE).status_code == 422
    assert client.delete("/api/stakeholders/sh-ZZZ", headers=WRITE).status_code == 422


def test_start_from_example_once(client: TestClient) -> None:
    first = client.post("/api/stakeholders/start-from-example", headers=WRITE)
    assert first.status_code == 201
    assert len(first.json()["stakeholders"]) >= 5
    again = client.post("/api/stakeholders/start-from-example", headers=WRITE)
    assert again.status_code == 409


def test_unreadable_file_is_never_overwritten(client: TestClient, settings: Settings) -> None:
    settings.stakeholders_file.parent.mkdir(parents=True)
    settings.stakeholders_file.write_text("{hand edited, broken", encoding="utf-8")
    assert client.post("/api/stakeholders", json=PERSON, headers=WRITE).status_code == 500
    assert settings.stakeholders_file.read_text(encoding="utf-8") == "{hand edited, broken"


def test_audience_matches_teams_and_names_gaps(client: TestClient) -> None:
    soc = client.post("/api/stakeholders", json=PERSON, headers=WRITE).json()
    view = client.get("/api/audience").json()

    report = view["reports"]["CTI26-01"]
    assert report["spec"] == "bulletin-scan/state/_work/CTI26-01-spec.json"  # newest wins
    teams = {t["name"]: t for t in report["teams"]}
    assert teams["SOC"]["stakeholders"] == [soc["id"]]
    assert teams["Security Operations"]["stakeholders"] == [soc["id"]]  # via also known as
    assert teams["SOC"]["questions"] == ["Would we see this in Falcon?"]
    assert "Lab Operations" in teams  # from the audience line, no questions
    assert "Old Team" not in teams
    assert view["reports"]["CTI26-02"]["teams"][0]["questions"] == ["Is the vendor affected?"]
    assert "TH26-01" not in view["reports"]  # a hunt spec names no teams

    gaps = {g["team"]: g["reports"] for g in view["unmatched"]}
    assert gaps["Product Security"] == ["CTI26-01"]
    assert "SOC" not in gaps


def test_team_names_are_compared_loosely() -> None:
    assert name_keys("Security Team") == {"security"}
    assert name_keys("DevOps / Platform Engineering") >= {"devops", "platform engineering"}
    assert name_keys("Privacy & Compliance") == {"privacy and compliance"}
