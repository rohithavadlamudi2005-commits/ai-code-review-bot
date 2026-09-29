import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_code_endpoint_success():
    payload = {
        "filename": "test.py",
        "source_code": "eval('2+2')\nprint('hello')",
        "changed_lines": [1]
    }
    response = client.post("/api/analyze/code", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.py"
    assert data["total_findings"] == 1
    assert data["findings"][0]["rule_id"] == "PY-SEC-002"


def test_analyze_code_endpoint_unsupported_file():
    payload = {
        "filename": "document.pdf",
        "source_code": "pdf content",
        "changed_lines": None
    }
    response = client.post("/api/analyze/code", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["skipped"] is True
    assert data["total_findings"] == 0


def test_analyze_pr_endpoint_success():
    mock_pr_info = {
        "repository": "octocat/Hello-World",
        "pull_number": 1,
        "title": "Add eval feature",
        "head_sha": "abc1234",
    }
    mock_files = [
        {
            "filename": "main.py",
            "status": "modified",
            "patch": "@@ -1,1 +1,2 @@\n context\n+eval('dangerous')",
        },
        {
            "filename": "avatar.png",
            "status": "added",
            "patch": "Binary files differ",
        }
    ]

    with patch("app.api.analyze.GitHubService.get_pull_request", new_callable=AsyncMock) as mock_pr, \
         patch("app.api.analyze.GitHubService.get_pull_request_files", new_callable=AsyncMock) as mock_files_fn, \
         patch("app.api.analyze.GitHubService.get_file_content", new_callable=AsyncMock) as mock_content:

        mock_pr.return_value = mock_pr_info
        mock_files_fn.return_value = mock_files
        mock_content.return_value = "context\neval('dangerous')"

        payload = {
            "owner": "octocat",
            "repo": "Hello-World",
            "pull_number": 1
        }
        response = client.post("/api/analyze/pr", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["owner"] == "octocat"
        assert data["repo"] == "Hello-World"
        assert data["pull_number"] == 1
        assert data["analyzed_files_count"] == 1
        assert data["skipped_files_count"] == 1
        assert data["total_findings"] >= 1
