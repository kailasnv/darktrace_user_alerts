from __future__ import annotations

import os
import tempfile

_TMP_DB_FD, _TMP_DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_TMP_DB_FD)

os.environ.setdefault("ALERT_ENGINE_DB_URL", f"sqlite:///{_TMP_DB_PATH}")
os.environ.setdefault("TAXII_API_ROOT", "https://taxii.example.test/api/v21")
os.environ.setdefault("TAXII_COLLECTION_ID", "00000000-0000-4000-8000-000000000001")

import pytest

from alert_engine.db import Base, SessionLocal, _engine


@pytest.fixture(autouse=True)
def _reset_schema():
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)
    yield


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()
