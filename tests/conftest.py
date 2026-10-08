import os

os.environ["DATABASE_URL"] = "sqlite:///./test_certificate_generator.db"
os.environ["CERTIFICATE_OUTPUT_DIR"] = "test_generated_certificates"

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client
