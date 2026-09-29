from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.health import get_gemini_provider
from app.llm.gemini_provider import GeminiProvider

client = TestClient(app)


def test_full_health_check_endpoint():
    response = client.get("/api/health/full")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "ai-code-review-bot"
    assert "components" in data
    assert "gemini" in data["components"]
    assert "redis" in data["components"]
    assert "celery" in data["components"]


def test_full_health_check_endpoint_gemini_connected():
    mock_provider = AsyncMock(spec=GeminiProvider)
    mock_provider.test_connection.return_value = {
        "connected": True,
        "model": "gemini-3.5-flash",
        "error": None
    }

    app.dependency_overrides[get_gemini_provider] = lambda: mock_provider
    try:
        response = client.get("/api/health/full")
        assert response.status_code == 200
        data = response.json()
        assert data["components"]["gemini"]["connected"] is True
        assert data["components"]["gemini"]["model"] == "gemini-3.5-flash"
        assert "error" not in data["components"]["gemini"]
    finally:
        app.dependency_overrides.clear()


def test_full_health_check_endpoint_gemini_disconnected():
    mock_provider = AsyncMock(spec=GeminiProvider)
    mock_provider.test_connection.return_value = {
        "connected": False,
        "model": "gemini-3.5-flash",
        "error": "API key invalid"
    }

    app.dependency_overrides[get_gemini_provider] = lambda: mock_provider
    try:
        response = client.get("/api/health/full")
        assert response.status_code == 200
        data = response.json()
        assert data["components"]["gemini"]["connected"] is False
        assert data["components"]["gemini"]["model"] == "gemini-3.5-flash"
        assert data["components"]["gemini"]["error"] == "API key invalid"
    finally:
        app.dependency_overrides.clear()


def test_gemini_health_check_endpoint_success():
    mock_provider = AsyncMock(spec=GeminiProvider)
    mock_provider.test_connection.return_value = {
        "connected": True,
        "model": "gemini-3.5-flash",
        "error": None
    }

    app.dependency_overrides[get_gemini_provider] = lambda: mock_provider
    try:
        response = client.get("/api/health/gemini")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["model"] == "gemini-3.5-flash"
        assert data["error"] is None
    finally:
        app.dependency_overrides.clear()


def test_gemini_health_check_endpoint_failed():
    mock_provider = AsyncMock(spec=GeminiProvider)
    mock_provider.test_connection.return_value = {
        "connected": False,
        "model": "gemini-3.5-flash",
        "error": "GEMINI_API_KEY is not configured."
    }

    app.dependency_overrides[get_gemini_provider] = lambda: mock_provider
    try:
        response = client.get("/api/health/gemini")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False
        assert data["model"] == "gemini-3.5-flash"
        assert data["error"] == "GEMINI_API_KEY is not configured."
    finally:
        app.dependency_overrides.clear()


def test_gemini_health_check_endpoint_exception():
    mock_provider = AsyncMock(spec=GeminiProvider)
    mock_provider.test_connection.side_effect = Exception("Unexpected connection error")
    mock_provider.model = "gemini-3.5-flash"

    app.dependency_overrides[get_gemini_provider] = lambda: mock_provider
    try:
        response = client.get("/api/health/gemini")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False
        assert data["model"] == "gemini-3.5-flash"
        assert "Unexpected connection error" in data["error"]
    finally:
        app.dependency_overrides.clear()


