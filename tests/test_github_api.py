import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.github_service import (
    GitHubResourceNotFoundError,
    GitHubRateLimitError,
)

client = TestClient(app)


def test_get_repository_endpoint_success():
    mock_repo_data = {
        "id": 101,
        "owner": "microsoft",
        "name": "vscode",
        "full_name": "microsoft/vscode",
        "description": "Visual Studio Code",
        "default_branch": "main",
        "is_private": False,
        "stars": 150000,
        "forks": 25000,
        "open_issues_count": 5000,
        "created_at": "2015-11-11T00:00:00Z",
        "updated_at": "2026-09-28T00:00:00Z",
    }

    with patch("app.api.github.GitHubService.get_repository", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_repo_data

        response = client.get("/api/github/repos/microsoft/vscode")

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "microsoft/vscode"
        assert data["stars"] == 150000


def test_get_repository_endpoint_not_found():
    with patch("app.api.github.GitHubService.get_repository", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = GitHubResourceNotFoundError("Repository 'invalid/repo' was not found on GitHub.")

        response = client.get("/api/github/repos/invalid/repo")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


def test_get_pull_request_endpoint_success():
    mock_pr_data = {
        "repository": "microsoft/vscode",
        "pull_number": 123,
        "title": "Fix bug in editor layout",
        "description": "Resolves alignment issue on high-DPI displays.",
        "author": "developer1",
        "state": "open",
        "created_at": "2026-09-25T10:00:00Z",
        "updated_at": "2026-09-26T12:00:00Z",
        "head_branch": "fix/layout",
        "head_sha": "abc1234",
        "base_branch": "main",
        "base_sha": "def5678",
        "changed_files_count": 2,
        "additions": 15,
        "deletions": 5,
        "draft": False,
    }

    with patch("app.api.github.GitHubService.get_pull_request", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_pr_data

        response = client.get("/api/github/repos/microsoft/vscode/pulls/123")

        assert response.status_code == 200
        data = response.json()
        assert data["pull_number"] == 123
        assert data["author"] == "developer1"
        assert data["head_branch"] == "fix/layout"


def test_get_pull_request_endpoint_invalid_pr_number():
    response = client.get("/api/github/repos/microsoft/vscode/pulls/-5")
    assert response.status_code == 400
    assert "Invalid PR number" in response.json()["detail"]


def test_get_pull_request_files_endpoint_success():
    mock_files = [
        {
            "filename": "src/vs/editor/editor.ts",
            "status": "modified",
            "additions": 10,
            "deletions": 2,
            "changes": 12,
            "patch": "@@ -10,3 +10,4 @@\n context line\n+added line",
        }
    ]

    with patch("app.api.github.GitHubService.get_pull_request_files", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_files

        response = client.get("/api/github/repos/microsoft/vscode/pulls/123/files")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["filename"] == "src/vs/editor/editor.ts"
        assert data[0]["additions"] == 10


def test_get_pull_request_files_endpoint_rate_limit():
    with patch("app.api.github.GitHubService.get_pull_request_files", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = GitHubRateLimitError("Rate limit exceeded")

        response = client.get("/api/github/repos/microsoft/vscode/pulls/123/files")

        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]


def test_create_test_pull_request_endpoint_success():
    mock_res = {
        "status": "created",
        "owner": "rohithavadlamudi2005-commits",
        "repo": "AI-Health-Assistant",
        "branch_name": "test-ai-review-20260929-120000-abc123",
        "pull_number": 1,
        "html_url": "https://github.com/rohithavadlamudi2005-commits/AI-Health-Assistant/pull/1",
        "title": "Test PR: Vulnerable Code Review Sample",
        "base_branch": "main",
        "created_at": "2026-09-29T12:00:00Z"
    }

    with patch("app.api.github.TestPRService.create_test_pull_request", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_res

        payload = {"base_branch": "main"}
        response = client.post("/api/github/repos/rohithavadlamudi2005-commits/AI-Health-Assistant/test-pr", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert data["owner"] == "rohithavadlamudi2005-commits"
        assert data["repo"] == "AI-Health-Assistant"
        assert data["pull_number"] == 1
        assert "html_url" in data
        assert "branch_name" in data

