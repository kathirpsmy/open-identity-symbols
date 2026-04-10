"""Shared pytest fixtures for the backend test suite.

IMPORTANT: Set DATABASE_URL before any backend module is imported,
so the SQLAlchemy engine is created pointing at SQLite, not Postgres.
"""

import os

# Override DB to SQLite before any backend import
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

# Now import backend modules (they will pick up the env override)
from backend.core.database import Base, get_db, engine as prod_engine  # noqa: E402
from backend.main import app  # noqa: E402

# Replace the global engine with a SQLite one (same URL as env override)
_TEST_URL = "sqlite:///./test.db"
engine = create_engine(_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import time
    for _ in range(5):
        try:
            if os.path.exists("test.db"):
                os.remove("test.db")
            break
        except PermissionError:
            time.sleep(0.2)


@pytest.fixture()
def client(setup_db):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
