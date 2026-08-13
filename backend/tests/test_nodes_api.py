import time
from pathlib import Path

from fastapi.testclient import TestClient


def _create(client: TestClient, **overrides: object) -> dict:
    payload = {"title": "Sample Note", "body": "Some notes about a topic."}
    payload.update(overrides)
    response = client.post("/api/nodes", json=payload)
    assert response.status_code == 201
    return response.json()


def test_create_writes_file_with_matching_id(client: TestClient, vault_root: Path) -> None:
    node = _create(client)

    files = list(vault_root.glob("*.md"))
    assert len(files) == 1
    text = files[0].read_text()
    assert f"id: {node['id']}" in text
    assert "title: Sample Note" in text


def test_create_sanitizes_traversal_title(client: TestClient, vault_root: Path) -> None:
    before = set(vault_root.parent.iterdir())

    response = client.post("/api/nodes", json={"title": "../../pwned"})
    assert response.status_code == 201

    after = set(vault_root.parent.iterdir())
    assert before == after
    assert list(vault_root.glob("*.md"))


def test_duplicate_titles_get_suffixed_slugs(client: TestClient, vault_root: Path) -> None:
    first = _create(client, title="Same Title")
    second = _create(client, title="Same Title")

    assert first["id"] != second["id"]
    names = sorted(p.name for p in vault_root.glob("*.md"))
    assert names == ["same-title-2.md", "same-title.md"]


def test_patch_updates_file_and_preserves_unknown_keys(
    client: TestClient, vault_root: Path
) -> None:
    node = _create(client)
    path = next(vault_root.glob("*.md"))
    text = path.read_text()
    path.write_text(text.replace("---\n\n", "custom_field: keep-me\n---\n\n", 1))
    time.sleep(0.35)  # clear synced_db's 300ms throttle so the edit is picked up

    detail = client.get(f"/api/nodes/{node['id']}").json()

    response = client.patch(
        f"/api/nodes/{node['id']}",
        json={"content_hash": detail["content_hash"], "title": "Renamed Title"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Renamed Title"
    assert "custom_field: keep-me" in path.read_text()


def test_patch_with_stale_hash_returns_409_and_leaves_file_untouched(
    client: TestClient, vault_root: Path
) -> None:
    node = _create(client)
    path = next(vault_root.glob("*.md"))
    before = path.read_text()

    response = client.patch(
        f"/api/nodes/{node['id']}",
        json={"content_hash": "0" * 64, "title": "Should Not Apply"},
    )

    assert response.status_code == 409
    assert path.read_text() == before
    body = response.json()["detail"]
    assert body["current"]["title"] == node["title"]


def test_patch_unknown_id_404(client: TestClient) -> None:
    response = client.patch(
        "/api/nodes/000000000000", json={"content_hash": "0" * 64, "title": "x"}
    )
    assert response.status_code == 404


def test_patch_with_no_fields_422(client: TestClient) -> None:
    node = _create(client)
    detail = client.get(f"/api/nodes/{node['id']}").json()

    response = client.patch(
        f"/api/nodes/{node['id']}", json={"content_hash": detail["content_hash"]}
    )

    assert response.status_code == 422


def test_list_filters_by_query_and_tag(client: TestClient) -> None:
    _create(client, title="Nvidia AI capex", tags=["ai", "semis"])
    _create(client, title="Fed rate outlook", body="macro stuff", tags=["macro"])

    by_query = client.get("/api/nodes?q=nvidia").json()
    assert [n["title"] for n in by_query] == ["Nvidia AI capex"]

    by_tag = client.get("/api/nodes?tag=macro").json()
    assert [n["title"] for n in by_tag] == ["Fed rate outlook"]


def test_get_unknown_node_404(client: TestClient) -> None:
    response = client.get("/api/nodes/000000000000")
    assert response.status_code == 404


def test_links_out_and_backlinks_resolve_across_nodes(client: TestClient) -> None:
    target = _create(client, title="Target Note")
    source = _create(client, title="Source Note", body="See [[Target Note]].")

    source_detail = client.get(f"/api/nodes/{source['id']}").json()
    assert source_detail["links_out"][0]["node_id"] == target["id"]

    target_detail = client.get(f"/api/nodes/{target['id']}").json()
    assert target_detail["backlinks"][0]["node_id"] == source["id"]
