from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import theses

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Thesis Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(theses.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
