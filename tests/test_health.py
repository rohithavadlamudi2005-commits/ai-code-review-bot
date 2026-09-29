import os
import sys
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """
    Test GET /api/health returns 200 OK and expected status payload.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-code-review-bot"
    }


def test_root_endpoint():
    """
    Test GET / returns 200 OK and valid welcome payload.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
