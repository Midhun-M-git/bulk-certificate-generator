import os
import sys
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import Base, get_db
import app.database as app_db
from app.config import settings
from app.main import app

# Create a temporary directory for test storage
TEST_STORAGE_DIR = Path(tempfile.mkdtemp(prefix="cert_test_storage_"))
settings.STORAGE_DIR = TEST_STORAGE_DIR

# Use a test SQLite database
TEST_DB_FILE = tempfile.mktemp(suffix=".db", prefix="cert_test_")
TEST_DB_URL = f"sqlite:///{TEST_DB_FILE}"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    # Setup test tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Teardown test tables & storage
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass
    if TEST_STORAGE_DIR.exists():
        shutil.rmtree(TEST_STORAGE_DIR, ignore_errors=True)


@pytest.fixture
def db_session():
    """Provides a transactional database session for tests."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(monkeypatch):
    """Provides a TestClient with dependency overrides and synchronous execution support."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Patch database SessionLocal so background tasks and services use the test database
    monkeypatch.setattr(app_db, "SessionLocal", TestingSessionLocal)
    import importlib
    job_service_module = sys.modules.get("app.services.job_service")
    if job_service_module:
        monkeypatch.setattr(job_service_module, "SessionLocal", TestingSessionLocal)

    monkeypatch.setattr(settings, "STORAGE_DIR", TEST_STORAGE_DIR)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
