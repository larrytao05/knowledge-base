import os
import tempfile
from pathlib import Path

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("VAULT_PATH", str(Path(tempfile.mkdtemp()) / "vault"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import Vault, get_vault, reset_sync_throttle
from app.main import app

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def vault_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # A dedicated tmp dir, not tmp_path/"vault" - this fixture is pulled in by
    # the autouse _reset_db fixture below for every test, including ones in
    # test_vault_io.py that use their own `tmp_path` directly and assert its
    # exact contents; nesting under tmp_path would pollute those.
    root = tmp_path_factory.mktemp("vault")
    (root / "checks").mkdir()
    return root


@pytest.fixture(autouse=True)
def _reset_db(vault_root: Path):
    Base.metadata.create_all(bind=test_engine)
    reset_sync_throttle()
    app.dependency_overrides[get_vault] = lambda: Vault(root=vault_root)
    yield
    app.dependency_overrides.pop(get_vault, None)
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
