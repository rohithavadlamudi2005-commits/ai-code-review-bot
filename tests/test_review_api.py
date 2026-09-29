import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_review_code_endpoint_success():
    payload = {
        "filename": "app.py",
        "source_code": "eval('2+2')",
        "changed_lines": [1]
    }

    with patch("app.llm.gemini_provider.GeminiProvider.review_code", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = []

        response = client.post("/api/review/code", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "app.py"
        assert len(data["static_findings"]) >= 1
        assert len(data["combined_findings"]) >= 1


def test_review_pr_endpoint_success():
    mock_pr_info = {
        "repository": "octocat/Hello-World",
        "pull_number": 1,
        "title": "Add feature",
        "head_sha": "sha123",
    }
    mock_files = [
        {
            "filename": "main.py",
            "status": "modified",
            "patch": "@@ -1,1 +1,2 @@\n+eval('2+2')",
        }
    ]

    with patch("app.services.github_service.GitHubService.get_pull_request", new_callable=AsyncMock) as mock_pr, \
         patch("app.services.github_service.GitHubService.get_pull_request_files", new_callable=AsyncMock) as mock_files_fn, \
         patch("app.services.github_service.GitHubService.get_file_content", new_callable=AsyncMock) as mock_content, \
         patch("app.llm.gemini_provider.GeminiProvider.review_code", new_callable=AsyncMock) as mock_llm:

        mock_pr.return_value = mock_pr_info
        mock_files_fn.return_value = mock_files
        mock_content.return_value = "eval('2+2')"
        mock_llm.return_value = []

        payload = {
            "owner": "octocat",
            "repo": "Hello-World",
            "pull_number": 1
        }

        response = client.post("/api/review/pr", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["owner"] == "octocat"
        assert data["repo"] == "Hello-World"
        assert data["pull_number"] == 1
        assert data["analyzed_files_count"] == 1
        assert "combined_findings" in data


def test_get_pr_review_run_status_not_run():
    response = client.get("/api/review/runs/nonexistent_owner/nonexistent_repo/999")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NOT_RUN"
    assert "No review execution records found" in data["message"]


def test_get_pr_review_run_status_with_existing_run():
    from app.services.automated_review_service import REVIEW_RUNS_STORE
    test_key = "test_owner/test_repo#42@commit_sha_123"
    run_data = {
        "repo_full_name": "test_owner/test_repo",
        "pull_number": 42,
        "commit_sha": "commit_sha_123",
        "status": "completed",
        "started_at": "2026-09-29T10:00:00Z",
        "completed_at": "2026-09-29T10:00:05Z",
        "findings_count": 2,
        "github_review_id": 12345,
        "error_message": None,
        "created_at": "2026-09-29T10:00:00Z"
    }
    REVIEW_RUNS_STORE[test_key] = run_data

    try:
        response = client.get("/api/review/runs/test_owner/test_repo/42")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["pull_number"] == 42
        assert data["commit_sha"] == "commit_sha_123"
        assert data["findings_count"] == 2
    finally:
        REVIEW_RUNS_STORE.pop(test_key, None)

