import time
from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.indexer import sync_vault
from app.services.locks import sync_lock

_SYNC_THROTTLE_SECONDS = 0.3
_last_sync_at = 0.0


@dataclass(frozen=True)
class Vault:
    root: Path


def get_vault() -> Vault:
    return Vault(root=settings.vault_path)


def reset_sync_throttle() -> None:
    global _last_sync_at
    _last_sync_at = 0.0


def synced_db(db: Session = Depends(get_db), vault: Vault = Depends(get_vault)) -> Session:
    global _last_sync_at
    with sync_lock:
        now = time.monotonic()
        if now - _last_sync_at >= _SYNC_THROTTLE_SECONDS:
            sync_vault(db, vault.root)
            _last_sync_at = time.monotonic()
    return db
