from pathlib import Path

from fastapi.testclient import TestClient


def _create(client: TestClient, **overrides: object) -> dict:
    payload = {"title": "Node", "body": ""}
    payload.update(overrides)
    response = client.post("/api/nodes", json=payload)
    assert response.status_code == 201
    return response.json()


def test_basic_edge_and_degree(client: TestClient) -> None:
    b = _create(client, title="B")
    a = _create(client, title="A", body="See [[B]].")

    response = client.get("/api/graph")
    assert response.status_code == 200
    data = response.json()

    assert len(data["edges"]) == 1
    edge = data["edges"][0]
    assert {edge["source"], edge["target"]} == {a["id"], b["id"]}

    degree_by_id = {n["id"]: n["degree"] for n in data["nodes"]}
    assert degree_by_id[a["id"]] == 1
    assert degree_by_id[b["id"]] == 1


def test_self_links_excluded(client: TestClient) -> None:
    node = _create(client, title="Self Referential", body="See [[Self Referential]] again.")

    response = client.get("/api/graph")
    data = response.json()

    assert data["edges"] == []
    degree_by_id = {n["id"]: n["degree"] for n in data["nodes"]}
    assert degree_by_id[node["id"]] == 0


def test_unresolved_links_surface(client: TestClient) -> None:
    _create(client, title="Has Dangling Link", body="See [[Nonexistent Note]].")

    response = client.get("/api/graph")
    data = response.json()

    assert "Nonexistent Note" in data["unresolved"]
    assert data["edges"] == []


def test_duplicate_links_collapse_to_one_edge(client: TestClient) -> None:
    d = _create(client, title="D")
    c = _create(client, title="C", body="See [[D]] and also [[D]] again.")

    response = client.get("/api/graph")
    data = response.json()

    edges = [e for e in data["edges"] if {e["source"], e["target"]} == {c["id"], d["id"]}]
    assert len(edges) == 1


def test_check_notes_never_appear_in_graph(client: TestClient, vault_root: Path) -> None:
    node = _create(client, title="Checked Node")

    check_text = f"""---
id: aaaaaaaaaaaa
type: check
node_id: {node["id"]}
verdict: on_track
checked: 2026-01-01T00:00:00Z
sources: []
---

Check of [[{node["title"]}]] - verdict: on_track
"""
    (vault_root / "checks" / "manual-check.md").write_text(check_text)

    response = client.get("/api/graph")
    data = response.json()

    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["id"] == node["id"]
    assert data["edges"] == []


def test_reindex_endpoint(client: TestClient, vault_root: Path) -> None:
    (vault_root / "external.md").write_text("---\ntitle: External\n---\n\nbody\n")

    response = client.post("/api/vault/reindex")
    assert response.status_code == 200
    body = response.json()
    assert body["added"] >= 1

    nodes_response = client.get("/api/nodes")
    titles = [n["title"] for n in nodes_response.json()]
    assert "External" in titles
