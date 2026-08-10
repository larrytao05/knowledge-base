from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.database import get_db
from app.services.agent import AgentCheckError, run_thesis_check

router = APIRouter(prefix="/api/theses", tags=["theses"])


@router.post("", response_model=schemas.ThesisRead, status_code=201)
def create_thesis(payload: schemas.ThesisCreate, db: Session = Depends(get_db)) -> models.Thesis:
    thesis = models.Thesis(ticker=payload.ticker, thesis_text=payload.thesis_text)
    db.add(thesis)
    db.commit()
    db.refresh(thesis)
    return thesis


@router.get("", response_model=list[schemas.ThesisRead])
def list_theses(db: Session = Depends(get_db)) -> list[models.Thesis]:
    stmt = select(models.Thesis).order_by(models.Thesis.created_at.desc())
    return list(db.scalars(stmt))


@router.get("/{thesis_id}", response_model=schemas.ThesisDetail)
def get_thesis(thesis_id: int, db: Session = Depends(get_db)) -> models.Thesis:
    stmt = (
        select(models.Thesis)
        .where(models.Thesis.id == thesis_id)
        .options(selectinload(models.Thesis.checks))
    )
    thesis = db.scalars(stmt).first()
    if thesis is None:
        raise HTTPException(404, "Thesis not found")
    return thesis


@router.post("/{thesis_id}/checks", response_model=schemas.ThesisCheckRead, status_code=201)
def trigger_check(thesis_id: int, db: Session = Depends(get_db)) -> models.ThesisCheck:
    thesis = db.get(models.Thesis, thesis_id)
    if thesis is None:
        raise HTTPException(404, "Thesis not found")
    try:
        result = run_thesis_check(ticker=thesis.ticker, thesis_text=thesis.thesis_text)
    except AgentCheckError as exc:
        raise HTTPException(502, f"Check failed: {exc}") from exc

    check = models.ThesisCheck(
        thesis_id=thesis.id,
        verdict=result.verdict,
        reasoning=result.reasoning,
        sources=[s.model_dump() for s in result.sources],
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check
