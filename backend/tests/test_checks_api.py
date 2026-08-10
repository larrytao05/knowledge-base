from pathlib import Path

from fastapi.testclient import TestClient

from app.schemas import Source
from app.services.agent import AgentCheckError, CheckResult
from app.services.vault_io import parse_note


def _create_node(client: TestClient) -> dict:
    response = client.post(
        "/api/nodes", json={"title": "NVDA Thesis", "body": "AI capex continues.", "ticker": "NVDA"}
    )
    assert response.status_code == 201
    return response.json()


def test_run_check_success_writes_check_note(
    client: TestClient, vault_root: Path, monkeypatch
) -> None:
    node = _create_node(client)

    def fake_run_check(*, claim: str, context: str = "") -> CheckResult:
        return CheckResult(
            verdict="on_track",
            reasoning="Evidence supports it.",
            sources=[Source(title="Example", url="https://example.com")],
        )

    monkeypatch.setattr("app.routers.nodes.run_check", fake_run_check)

    response = client.post(f"/api/nodes/{node['id']}/checks")
    assert response.status_code == 201
    assert response.json()["verdict"] == "on_track"

    files = list((vault_root / "checks").glob("*.md"))
    assert len(files) == 1
    parsed = parse_note(files[0].read_text())
    assert parsed.frontmatter["type"] == "check"
    assert parsed.frontmatter["node_id"] == node["id"]

    detail = client.get(f"/api/nodes/{node['id']}").json()
    assert len(detail["checks"]) == 1
    assert detail["checks"][0]["verdict"] == "on_track"


def test_run_check_agent_failure_returns_502_and_leaves_no_file(
    client: TestClient, vault_root: Path, monkeypatch
) -> None:
    node = _create_node(client)

    def fake_run_check(*, claim: str, context: str = "") -> CheckResult:
        raise AgentCheckError("model did not submit a report")

    monkeypatch.setattr("app.routers.nodes.run_check", fake_run_check)

    response = client.post(f"/api/nodes/{node['id']}/checks")
    assert response.status_code == 502
    assert list((vault_root / "checks").glob("*.md")) == []


def test_run_check_unknown_node_404(client: TestClient) -> None:
    response = client.post("/api/nodes/000000000000/checks")
    assert response.status_code == 404


def test_check_note_wikilink_does_not_create_spurious_backlink(
    client: TestClient, vault_root: Path, monkeypatch
) -> None:
    node = _create_node(client)

    def fake_run_check(*, claim: str, context: str = "") -> CheckResult:
        return CheckResult(
            verdict="on_track",
            reasoning="Evidence supports it.",
            sources=[Source(title="Example", url="https://example.com")],
        )

    monkeypatch.setattr("app.routers.nodes.run_check", fake_run_check)

    response = client.post(f"/api/nodes/{node['id']}/checks")
    assert response.status_code == 201

    files = list((vault_root / "checks").glob("*.md"))
    assert len(files) == 1
    assert "[[NVDA Thesis]]" in files[0].read_text()

    detail = client.get(f"/api/nodes/{node['id']}").json()
    assert detail["backlinks"] == []
