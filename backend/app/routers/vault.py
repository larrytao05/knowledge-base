from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.database import get_db
from app.deps import Vault, get_vault
from app.services.indexer import sync_vault

router = APIRouter(prefix="/api/vault", tags=["vault"])


@router.post("/reindex", response_model=schemas.SyncReport)
def reindex_vault(
    db: Session = Depends(get_db), vault: Vault = Depends(get_vault)
) -> schemas.SyncReport:
    stats = sync_vault(db, vault.root)
    return schemas.SyncReport(
        added=stats.added, updated=stats.updated, removed=stats.removed, errors=stats.errors
    )
