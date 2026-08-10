from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.deps import synced_db
from app.models import Check, Node, NodeLink

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("", response_model=schemas.GraphData)
def get_graph(db: Session = Depends(synced_db)) -> schemas.GraphData:
    notes_list = list(db.scalars(select(Node).where(Node.kind == "note")))
    by_title_norm = {n.title_norm: n for n in notes_list}
    notes_by_id = {n.id: n for n in notes_list}

    edges: set[tuple[str, str]] = set()
    unresolved: set[str] = set()

    for link in db.scalars(select(NodeLink)):
        source_node = notes_by_id.get(link.source_id)
        if source_node is None:
            continue

        target = by_title_norm.get(link.target_norm)
        if target is None:
            unresolved.add(link.target_raw)
            continue
        if target.id == source_node.id:
            continue
        edges.add((min(source_node.id, target.id), max(source_node.id, target.id)))

    degree: dict[str, int] = {n.id: 0 for n in notes_list}
    for a, b in edges:
        degree[a] += 1
        degree[b] += 1

    all_checks = list(db.scalars(select(Check).order_by(Check.created_at.desc())))
    latest_verdict_by_node: dict[str, str] = {}
    for check in all_checks:
        latest_verdict_by_node.setdefault(check.node_id, check.verdict)

    return schemas.GraphData(
        nodes=[
            schemas.GraphNode(
                id=n.id,
                title=n.title,
                ticker=n.ticker,
                verdict=latest_verdict_by_node.get(n.id),  # type: ignore[arg-type]
                degree=degree[n.id],
            )
            for n in notes_list
        ],
        edges=[schemas.GraphEdge(source=a, target=b) for a, b in sorted(edges)],
        unresolved=sorted(unresolved),
    )
