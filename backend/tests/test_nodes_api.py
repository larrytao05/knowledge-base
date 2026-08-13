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


def test_rename_rewrites_inbound_links_in_other_notes(
    client: TestClient, vault_root: Path
) -> None:
    target = _create(client, title="Old Title")
    source = _create(
        client,
        title="Source Note",
        body=(
            "See [[Old Title]], [[Old Title#Some Heading]] and [[Old Title|the alias]].\n\n"
            "```\n[[Old Title]]\n```\n\nInline `[[Old Title]]` stays too.\n"
        ),
    )

    response = client.patch(
        f"/api/nodes/{target['id']}",
        json={"content_hash": target["content_hash"], "title": "New Title"},
    )
    assert response.status_code == 200

    text = (vault_root / source["path"]).read_text()
    assert "See [[New Title]], [[New Title#Some Heading]] and [[New Title|the alias]]." in text
    assert "```\n[[Old Title]]\n```" in text
    assert "`[[Old Title]]`" in text

    source_detail = client.get(f"/api/nodes/{source['id']}").json()
    assert [link["node_id"] for link in source_detail["links_out"]] == [target["id"]] * 3


def test_rename_rewrites_self_links_in_the_renamed_note(
    client: TestClient, vault_root: Path
) -> None:
    node = _create(client, title="Old Title", body="This note is [[Old Title]].")

    response = client.patch(
        f"/api/nodes/{node['id']}",
        json={"content_hash": node["content_hash"], "title": "New Title"},
    )

    assert response.status_code == 200
    assert "This note is [[New Title]]." in (vault_root / node["path"]).read_text()


def test_rename_onto_an_existing_title_is_rejected(client: TestClient, vault_root: Path) -> None:
    target = _create(client, title="Old Title")
    _create(client, title="New Title")
    source = _create(client, title="Source Note", body="See [[Old Title]].")

    response = client.patch(
        f"/api/nodes/{target['id']}",
        json={"content_hash": target["content_hash"], "title": "New Title"},
    )

    # Rewriting the link text is not reversible, so the collision has to be
    # refused rather than silently pointing this note's backlinks at the other.
    assert response.status_code == 409
    assert "See [[Old Title]]." in (vault_root / source["path"]).read_text()
    assert client.get(f"/api/nodes/{target['id']}").json()["title"] == "Old Title"


def test_rename_away_from_a_shared_title_leaves_inbound_links_alone(
    client: TestClient, vault_root: Path
) -> None:
    kept = _create(client, title="Meeting Notes")
    renamed = _create(client, title="Meeting Notes")
    source = _create(client, title="Source Note", body="See [[Meeting Notes]].")
    assert client.get(f"/api/nodes/{source['id']}").json()["links_out"][0]["node_id"] == kept["id"]

    response = client.patch(
        f"/api/nodes/{renamed['id']}",
        json={"content_hash": renamed["content_hash"], "title": "Weekly Sync"},
    )

    # The link may well have meant the note that kept the title, so retargeting
    # it at the renamed one would repoint it at a note it never referenced.
    assert response.status_code == 200
    assert response.json()["link_rewrite_skipped"] == 1
    assert "See [[Meeting Notes]]." in (vault_root / source["path"]).read_text()
    source_detail = client.get(f"/api/nodes/{source['id']}").json()
    assert source_detail["links_out"][0]["node_id"] == kept["id"]


def test_rename_rewrites_a_target_holding_inline_code(
    client: TestClient, vault_root: Path
) -> None:
    target = _create(client, title="Using `git rebase`")
    source = _create(client, title="Source Note", body="See [[Using `git rebase`]].")
    before = client.get(f"/api/nodes/{source['id']}").json()
    assert before["links_out"][0]["node_id"] == target["id"]

    response = client.patch(
        f"/api/nodes/{target['id']}",
        json={"content_hash": target["content_hash"], "title": "Rebasing"},
    )

    assert response.status_code == 200
    assert response.json()["link_rewrite_skipped"] == 0
    assert "See [[Rebasing]]." in (vault_root / source["path"]).read_text()
    source_detail = client.get(f"/api/nodes/{source['id']}").json()
    assert source_detail["links_out"][0]["node_id"] == target["id"]


def test_rename_keeps_inline_code_inside_an_alias(client: TestClient, vault_root: Path) -> None:
    target = _create(client, title="Old Title")
    source = _create(client, title="Source Note", body="See [[Old Title|the `code` alias]].")

    client.patch(
        f"/api/nodes/{target['id']}",
        json={"content_hash": target["content_hash"], "title": "New Title"},
    )

    text = (vault_root / source["path"]).read_text()
    assert "[[New Title|the `code` alias]]" in text


def test_rename_to_an_unlinkable_title_is_rejected(client: TestClient, vault_root: Path) -> None:
    target = _create(client, title="Old Title")
    source = _create(client, title="Source Note", body="See [[Old Title]].")
    before = (vault_root / source["path"]).read_text()

    for unsafe in ("C# notes", "foo]] bar", "a|b", "   "):
        response = client.patch(
            f"/api/nodes/{target['id']}",
            json={"content_hash": target["content_hash"], "title": unsafe},
        )
        assert response.status_code == 422

    assert (vault_root / source["path"]).read_text() == before
    assert client.get(f"/api/nodes/{target['id']}").json()["title"] == "Old Title"


def test_create_with_an_unlinkable_title_is_rejected(client: TestClient) -> None:
    response = client.post("/api/nodes", json={"title": "C# notes"})
    assert response.status_code == 422


def _write_unlinkable_title_note(vault_root: Path) -> str:
    # Titles are free-form frontmatter and the vault is co-edited with Obsidian,
    # so notes like this arrive through the indexer, not through the API.
    node_id = "abcdef123456"
    path = vault_root / "csharp.md"
    path.write_text(f'---\nid: {node_id}\ntitle: "C# notes"\n---\n\nOld body.\n')
    return node_id


def test_body_edit_of_a_note_with_an_unlinkable_title_is_allowed(
    client: TestClient, vault_root: Path
) -> None:
    node_id = _write_unlinkable_title_note(vault_root)
    detail = client.get(f"/api/nodes/{node_id}").json()
    assert detail["title"] == "C# notes"

    response = client.patch(
        f"/api/nodes/{node_id}",
        json={
            "content_hash": detail["content_hash"],
            "title": detail["title"],
            "body": "New body.",
        },
    )

    assert response.status_code == 200
    assert "New body." in (vault_root / "csharp.md").read_text()
    assert client.get(f"/api/nodes/{node_id}").json()["title"] == "C# notes"


def test_rename_away_from_an_unlinkable_title_is_allowed(
    client: TestClient, vault_root: Path
) -> None:
    node_id = _write_unlinkable_title_note(vault_root)
    detail = client.get(f"/api/nodes/{node_id}").json()

    response = client.patch(
        f"/api/nodes/{node_id}",
        json={"content_hash": detail["content_hash"], "title": "Csharp notes"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Csharp notes"


def test_rename_leaves_unrelated_notes_alone(client: TestClient, vault_root: Path) -> None:
    target = _create(client, title="Old Title")
    other = _create(client, title="Other Note", body="Links to [[Something Else]].")
    before = (vault_root / other["path"]).read_text()

    client.patch(
        f"/api/nodes/{target['id']}",
        json={"content_hash": target["content_hash"], "title": "New Title"},
    )

    assert (vault_root / other["path"]).read_text() == before


def test_links_out_and_backlinks_resolve_across_nodes(client: TestClient) -> None:
    target = _create(client, title="Target Note")
    source = _create(client, title="Source Note", body="See [[Target Note]].")

    source_detail = client.get(f"/api/nodes/{source['id']}").json()
    assert source_detail["links_out"][0]["node_id"] == target["id"]

    target_detail = client.get(f"/api/nodes/{target['id']}").json()
    assert target_detail["backlinks"][0]["node_id"] == source["id"]
