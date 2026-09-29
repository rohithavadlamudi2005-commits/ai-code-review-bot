import hashlib
import hmac
import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_webhook_unauthorized_missing_signature():
    with patch("app.services.webhook_security.get_settings") as mock_settings:
        mock_settings.return_value.GITHUB_WEBHOOK_SECRET = "secret_key"
        response = client.post("/api/webhooks/github", json={"action": "opened"})
        assert response.status_code == 401
        assert "Missing 'X-Hub-Signature-256' header" in response.json()["detail"]


def test_webhook_unauthorized_invalid_signature():
    with patch("app.services.webhook_security.get_settings") as mock_settings:
        mock_settings.return_value.GITHUB_WEBHOOK_SECRET = "secret_key"
        headers = {
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalid_hash"
        }
        response = client.post("/api/webhooks/github", json={"action": "opened"}, headers=headers)
        assert response.status_code == 401


def test_webhook_pr_opened_event_accepted_and_queued():
    secret = "test_webhook_secret"
    payload = {
        "action": "opened",
        "repository": {
            "name": "Hello-World",
            "owner": {"login": "octocat"}
        },
        "pull_request": {
            "number": 1,
            "head": {"sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e"}
        }
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    signature = "sha256=" + hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    headers = {
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": signature,
        "Content-Type": "application/json"
    }

    with patch("app.services.webhook_security.get_settings") as mock_settings, \
         patch("app.api.webhooks.AutomatedReviewService.execute_automated_review", new_callable=AsyncMock) as mock_exec:

        mock_settings.return_value.GITHUB_WEBHOOK_SECRET = secret

        response = client.post("/api/webhooks/github", content=payload_bytes, headers=headers)
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "queued"
        assert data["owner"] == "octocat"
        assert data["repo"] == "Hello-World"
        assert data["pull_number"] == 1


def test_webhook_unsupported_event_ignored():
    secret = "test_webhook_secret"
    payload = {"action": "created", "comment": {"body": "hello"}}
    payload_bytes = json.dumps(payload).encode("utf-8")
    signature = "sha256=" + hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    headers = {
        "X-GitHub-Event": "issue_comment",
        "X-Hub-Signature-256": signature,
        "Content-Type": "application/json"
    }

    with patch("app.services.webhook_security.get_settings") as mock_settings:
        mock_settings.return_value.GITHUB_WEBHOOK_SECRET = secret

        response = client.post("/api/webhooks/github", content=payload_bytes, headers=headers)
        assert response.status_code == 202
        assert response.json()["status"] == "ignored"
