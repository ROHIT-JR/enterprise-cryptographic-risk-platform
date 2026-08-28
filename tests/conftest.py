import os

os.environ["ECDAT_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["ECDAT_NEO4J_ENABLED"] = "false"
os.environ["ECDAT_DOCKER_ENABLED"] = "false"
os.environ["ECDAT_SEED_DEMO"] = "false"
os.environ["ECDAT_SCAN_STORAGE_PATH"] = "/tmp/ecdatx-test-scans"

import pytest

from backend.app.database import engine
from backend.app.models.base import Base


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
