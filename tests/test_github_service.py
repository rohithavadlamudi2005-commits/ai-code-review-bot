import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.github_service import (
    GitHubService,
    GitHubAuthenticationError,
    GitHubResourceNotFoundError,
    GitHubRateLimitError,
    GitHubAPIError,
)


@pytest.mark.asyncio
async def test_get_repository_success():
    mock_data = {
        "id": 12345,
        "owner": {"login": "octocat"},
        "name": "Hello-World",
        "full_name": "octocat/Hello-World",
        "description": "This your first repo!",
        "default_branch": "master",
        "private": False,
        "stargazers_count": 80,
        "forks_count": 20,
        "open_issues_count": 2,
        "created_at": "2011-01-26T19:01:12Z",
        "updated_at": "2026-09-28T00:00:00Z",
    }

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_data

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        service = GitHubService(token="test_token")
        result = await service.get_repository("octocat", "Hello-World")

        assert result["id"] == 12345
        assert result["owner"] == "octocat"
        assert result["name"] == "Hello-World"
        assert result["full_name"] == "octocat/Hello-World"
        assert result["stars"] == 80
        assert result["default_branch"] == "master"

        mock_get.assert_called_once()
        headers = mock_get.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test_token"


@pytest.mark.asyncio
async def test_get_pull_request_success():
    mock_pr_data = {
        "number": 1347,
        "title": "Amazing new feature",
        "body": "Please pull these changes into master.",
        "user": {"login": "octocat"},
        "state": "open",
        "created_at": "2011-01-26T19:01:12Z",
        "updated_at": "2011-01-26T19:01:12Z",
        "head": {"ref": "new-topic", "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e"},
        "base": {"ref": "master", "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e"},
        "changed_files": 3,
        "additions": 100,
        "deletions": 50,
        "draft": False,
    }

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_pr_data

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        service = GitHubService(token="test_token")
        result = await service.get_pull_request("octocat", "Hello-World", 1347)

        assert result["pull_number"] == 1347
        assert result["title"] == "Amazing new feature"
        assert result["author"] == "octocat"
        assert result["head_branch"] == "new-topic"
        assert result["base_branch"] == "master"
        assert result["changed_files_count"] == 3


@pytest.mark.asyncio
async def test_get_pull_request_files_success():
    mock_files = [
        {
            "filename": "file1.txt",
            "status": "added",
            "additions": 10,
            "deletions": 0,
            "changes": 10,
            "patch": "@@ -0,0 +1,10 @@\n+added content",
        }
    ]

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_files

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        service = GitHubService(token="test_token")
        result = await service.get_pull_request_files("octocat", "Hello-World", 1347)

        assert len(result) == 1
        assert result[0]["filename"] == "file1.txt"
        assert result[0]["status"] == "added"
        assert result[0]["patch"] == "@@ -0,0 +1,10 @@\n+added content"


@pytest.mark.asyncio
async def test_github_service_authentication_error():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = {"message": "Bad credentials"}

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        service = GitHubService(token="invalid_token")
        with pytest.raises(GitHubAuthenticationError) as exc:
            await service.get_repository("octocat", "Hello-World")
        assert "Invalid or expired GitHub token" in str(exc.value)


@pytest.mark.asyncio
async def test_github_service_resource_not_found():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.json.return_value = {"message": "Not Found"}

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        service = GitHubService()
        with pytest.raises(GitHubResourceNotFoundError) as exc:
            await service.get_pull_request("octocat", "nonexistent", 999)
        assert "not found on GitHub" in str(exc.value)


@pytest.mark.asyncio
async def test_github_service_rate_limit():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    mock_response.headers = {"x-ratelimit-remaining": "0"}
    mock_response.json.return_value = {"message": "API rate limit exceeded"}

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        service = GitHubService()
        with pytest.raises(GitHubRateLimitError) as exc:
            await service.get_repository("octocat", "Hello-World")
        assert "rate limit exceeded" in str(exc.value)


@pytest.mark.asyncio
async def test_get_branch_sha_success():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "ref": "refs/heads/main",
        "object": {"sha": "abc123def456"}
    }

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        service = GitHubService(token="test_token")
        sha = await service.get_branch_sha("octocat", "Hello-World", "main")
        assert sha == "abc123def456"


@pytest.mark.asyncio
async def test_create_branch_success():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "ref": "refs/heads/feature-branch",
        "object": {"sha": "abc123def456"}
    }

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        service = GitHubService(token="test_token")
        res = await service.create_branch("octocat", "Hello-World", "feature-branch", "abc123def456")
        assert res["ref"] == "refs/heads/feature-branch"


@pytest.mark.asyncio
async def test_create_file_commit_success():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "content": {"name": "ai_review_test.py", "path": "ai_review_test.py"}
    }

    with patch.object(httpx.AsyncClient, "put", new_callable=AsyncMock) as mock_put:
        mock_put.return_value = mock_response

        service = GitHubService(token="test_token")
        res = await service.create_file_commit("octocat", "Hello-World", "ai_review_test.py", "eval('2+2')", "Commit msg", "feature-branch")
        assert res["content"]["name"] == "ai_review_test.py"


@pytest.mark.asyncio
async def test_create_pull_request_success():
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "number": 10,
        "html_url": "https://github.com/octocat/Hello-World/pull/10",
        "title": "Test PR"
    }

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        service = GitHubService(token="test_token")
        res = await service.create_pull_request("octocat", "Hello-World", "Test PR", "feature-branch", "main", "PR body")
        assert res["number"] == 10
        assert res["html_url"] == "https://github.com/octocat/Hello-World/pull/10"

