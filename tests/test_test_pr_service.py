import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.github_service import (
    GitHubService,
    GitHubAuthenticationError,
    GitHubResourceNotFoundError,
    GitHubRateLimitError,
    GitHubAPIError,
)
from app.services.test_pr_service import TestPRService, TEST_FILE_PATH, TEST_FILE_CONTENT


@pytest.mark.asyncio
async def test_create_test_pull_request_success():
    mock_github = AsyncMock(spec=GitHubService)
    mock_github.get_branch_sha.return_value = "base_sha_123456"
    mock_github.create_branch.return_value = {"ref": "refs/heads/test-branch"}
    mock_github.create_file_commit.return_value = {"content": {"name": TEST_FILE_PATH}}
    mock_github.create_pull_request.return_value = {
        "number": 42,
        "html_url": "https://github.com/owner/repo/pull/42",
        "title": "Test PR Title",
        "created_at": "2026-09-29T12:00:00Z"
    }

    service = TestPRService(github_service=mock_github)
    result = await service.create_test_pull_request("owner", "repo", "main")

    assert result["status"] == "created"
    assert result["owner"] == "owner"
    assert result["repo"] == "repo"
    assert result["pull_number"] == 42
    assert result["html_url"] == "https://github.com/owner/repo/pull/42"
    assert "test-ai-review-" in result["branch_name"]

    mock_github.get_branch_sha.assert_called_once_with("owner", "repo", "main")
    mock_github.create_branch.assert_called_once()
    mock_github.create_file_commit.assert_called_once()
    mock_github.create_pull_request.assert_called_once()


@pytest.mark.asyncio
async def test_create_test_pull_request_empty_owner_raises():
    service = TestPRService()
    with pytest.raises(GitHubAPIError) as exc_info:
        await service.create_test_pull_request("", "repo")
    assert "Owner and repository name are required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_test_pull_request_401_error():
    mock_github = AsyncMock(spec=GitHubService)
    mock_github.get_branch_sha.side_effect = GitHubAuthenticationError("Invalid GitHub token")

    service = TestPRService(github_service=mock_github)
    with pytest.raises(GitHubAuthenticationError) as exc_info:
        await service.create_test_pull_request("owner", "repo", "main")
    assert "Invalid GitHub token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_test_pull_request_404_error():
    mock_github = AsyncMock(spec=GitHubService)
    mock_github.get_branch_sha.side_effect = GitHubResourceNotFoundError("Repository owner/repo was not found")

    service = TestPRService(github_service=mock_github)
    with pytest.raises(GitHubResourceNotFoundError) as exc_info:
        await service.create_test_pull_request("owner", "repo", "main")
    assert "not found" in str(exc_info.value)
