from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Path as PathParam
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.deps import Vault, get_vault, synced_db
from app.models import Check, Node, NodeLink
from app.services import notes
from app.services.agent import AgentCheckError, run_check
from app.services.indexer import sync_vault

router = APIRouter(prefix="/api/nodes", tags=["nodes"])

NodeId = Annotated[str, PathParam(pattern=r"^[a-f0-9]{12}$")]

_EXCERPT_LEN = 200


def _excerpt(body: str) -> str:
    stripped = body.strip()
    if len(stripped) <= _EXCERPT_LEN:
        return stripped
    return stripped[:_EXCERPT_LEN].rstrip() + "…"


def _latest_verdict(db: Session, node_id: str) -> schemas.Verdict | None:
    check = db.scalars(
        select(Check).where(Check.node_id == node_id).order_by(Check.created_at.desc()).limit(1)
    ).first()
    return check.verdict if check else None  # type: ignore[return-value]


def _build_detail(db: Session, node: Node) -> schemas.NodeDetail:
    links_out: list[schemas.LinkRef] = []
    for link in db.scalars(select(NodeLink).where(NodeLink.source_id == node.id)):
        target = db.scalars(
            select(Node).where(Node.title_norm == link.target_norm, Node.kind == "note")
        ).first()
        links_out.append(
            schemas.LinkRef(
                target_raw=link.target_raw,
                alias=link.alias,
                node_id=target.id if target else None,
                title=target.title if target else None,
            )
        )

    backlinks: list[schemas.LinkRef] = []
    stmt = (
        select(NodeLink, Node)
        .join(Node, Node.id == NodeLink.source_id)
        .where(NodeLink.target_norm == node.title_norm, Node.kind == "note")
    )
    for link, source_node in db.execute(stmt).all():
        backlinks.append(
            schemas.LinkRef(
                target_raw=link.target_raw,
                alias=link.alias,
                node_id=source_node.id,
                title=source_node.title,
            )
        )

    checks = [
        schemas.CheckRead.model_validate(c)
        for c in db.scalars(
            select(Check).where(Check.node_id == node.id).order_by(Check.created_at.desc())
        )
    ]

    return schemas.NodeDetail(
        id=node.id,
        title=node.title,
        path=node.path,
        ticker=node.ticker,
        tags=node.tags,
        body=node.body,
        content_hash=node.content_hash,
        fm_error=node.fm_error,
        created_at=node.created_at,
        updated_at=node.updated_at,
        links_out=links_out,
        backlinks=backlinks,
        checks=checks,
    )


@router.get("", response_model=list[schemas.NodeSummary])
def list_nodes(
    q: str | None = None, tag: str | None = None, db: Session = Depends(synced_db)
) -> list[schemas.NodeSummary]:
    stmt = select(Node).where(Node.kind == "note").order_by(Node.updated_at.desc())
    nodes = list(db.scalars(stmt))

    if q:
        needle = q.lower()
        nodes = [n for n in nodes if needle in n.title.lower() or needle in n.body.lower()]
    if tag:
        needle_tag = tag.lower()
        nodes = [n for n in nodes if needle_tag in (n.tags or [])]

    return [
        schemas.NodeSummary(
            id=n.id,
            title=n.title,
            ticker=n.ticker,
            tags=n.tags,
            excerpt=_excerpt(n.body),
            updated_at=n.updated_at,
            latest_verdict=_latest_verdict(db, n.id),
        )
        for n in nodes
    ]


@router.post("", response_model=schemas.NodeDetail, status_code=201)
def create_node(
    payload: schemas.NodeCreate,
    db: Session = Depends(synced_db),
    vault: Vault = Depends(get_vault),
) -> schemas.NodeDetail:
    try:
        node = notes.create_node(
            db,
            vault,
            title=payload.title,
            body=payload.body,
            ticker=payload.ticker,
            tags=payload.tags,
        )
    except OSError as exc:
        raise HTTPException(503, f"failed to write vault file: {exc}") from exc
    return _build_detail(db, node)


@router.get("/{node_id}", response_model=schemas.NodeDetail)
def get_node(node_id: NodeId, db: Session = Depends(synced_db)) -> schemas.NodeDetail:
    node = db.get(Node, node_id)
    if node is None or node.kind != "note":
        raise HTTPException(404, "Node not found")
    return _build_detail(db, node)


@router.patch("/{node_id}", response_model=schemas.NodeDetail)
def update_node(
    node_id: NodeId,
    payload: schemas.NodeUpdate,
    db: Session = Depends(synced_db),
    vault: Vault = Depends(get_vault),
) -> schemas.NodeDetail:
    node = db.get(Node, node_id)
    if node is None or node.kind != "note":
        raise HTTPException(404, "Node not found")

    try:
        updated = notes.update_node(db, vault, node, payload)
    except notes.MalformedNoteError as exc:
        raise HTTPException(422, f"cannot edit a note with invalid frontmatter: {exc}") from exc
    except notes.StaleContentError:
        sync_vault(db, vault.root)
        current = db.get(Node, node_id)
        current_detail = _build_detail(db, current) if current else None
        raise HTTPException(
            409,
            detail={
                "message": "content changed on disk",
                "current": current_detail.model_dump(mode="json") if current_detail else None,
            },
        ) from None
    except OSError as exc:
        raise HTTPException(503, f"failed to write vault file: {exc}") from exc

    return _build_detail(db, updated)


@router.post("/{node_id}/checks", response_model=schemas.CheckRead, status_code=201)
def run_node_check(
    node_id: NodeId,
    db: Session = Depends(synced_db),
    vault: Vault = Depends(get_vault),
) -> schemas.CheckRead:
    node = db.get(Node, node_id)
    if node is None or node.kind != "note":
        raise HTTPException(404, "Node not found")

    try:
        result = run_check(claim=f"{node.title}\n\n{node.body}", context=node.ticker or "")
    except AgentCheckError as exc:
        raise HTTPException(502, f"Check failed: {exc}") from exc

    try:
        check = notes.write_check_note(db, vault, node, result)
    except OSError as exc:
        raise HTTPException(503, f"failed to write check file: {exc}") from exc

    return schemas.CheckRead.model_validate(check)
