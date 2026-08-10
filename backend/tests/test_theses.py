from fastapi.testclient import TestClient

from app.schemas import Source
from app.services.agent import AgentCheckError, ThesisCheckResult


def _create_thesis(client: TestClient) -> dict:
    response = client.post(
        "/api/theses",
        json={"ticker": "nvda", "thesis_text": "AI datacenter capex keeps growing through 2027."},
    )
    assert response.status_code == 201
    return response.json()


def test_create_and_list_thesis(client: TestClient) -> None:
    created = _create_thesis(client)
    assert created["ticker"] == "NVDA"

    listed = client.get("/api/theses")
    assert listed.status_code == 200
    assert any(t["id"] == created["id"] for t in listed.json())


def test_get_thesis_404(client: TestClient) -> None:
    response = client.get("/api/theses/999")
    assert response.status_code == 404


def test_trigger_check_success(client: TestClient, monkeypatch) -> None:
    thesis = _create_thesis(client)

    def fake_run_thesis_check(*, ticker: str, thesis_text: str) -> ThesisCheckResult:
        return ThesisCheckResult(
            verdict="on_track",
            reasoning="Evidence supports the thesis.",
            sources=[Source(title="Example", url="https://example.com")],
        )

    monkeypatch.setattr("app.routers.theses.run_thesis_check", fake_run_thesis_check)

    response = client.post(f"/api/theses/{thesis['id']}/checks")
    assert response.status_code == 201
    assert response.json()["verdict"] == "on_track"

    detail = client.get(f"/api/theses/{thesis['id']}")
    assert len(detail.json()["checks"]) == 1


def test_trigger_check_agent_failure(client: TestClient, monkeypatch) -> None:
    thesis = _create_thesis(client)

    def fake_run_thesis_check(*, ticker: str, thesis_text: str) -> ThesisCheckResult:
        raise AgentCheckError("model did not submit a report")

    monkeypatch.setattr("app.routers.theses.run_thesis_check", fake_run_thesis_check)

    response = client.post(f"/api/theses/{thesis['id']}/checks")
    assert response.status_code == 502
