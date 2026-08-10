import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import nodes

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

settings.vault_path.mkdir(parents=True, exist_ok=True)
(settings.vault_path / "checks").mkdir(parents=True, exist_ok=True)
logger.info("Vault path: %s", settings.vault_path)

app = FastAPI(title="Thesis Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nodes.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
