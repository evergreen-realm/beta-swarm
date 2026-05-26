import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    """Shared TestClient for all tests in the module."""
    with TestClient(app) as c:
        yield c
