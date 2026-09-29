from typing import List
from fastapi import APIRouter, HTTPException, Depends, status

from app.models.github import (
    RepositoryResponse,
    PullRequestResponse,
    PullRequestFileResponse,
    CreateTestPRRequest,
    CreateTestPRResponse,
)
from app.services.github_service import (
    GitHubService,
    GitHubAuthenticationError,
    GitHubResourceNotFoundError,
    GitHubRateLimitError,
    GitHubAPIError,
)
from app.services.test_pr_service import TestPRService

router = APIRouter()


def get_github_service() -> GitHubService:
    """Dependency provider for GitHubService."""
    return GitHubService()


def get_test_pr_service() -> TestPRService:
    """Dependency provider for TestPRService."""
    return TestPRService()


@router.get(
    "/repos/{owner}/{repo}",
    response_model=RepositoryResponse,
    summary="Get Repository Information",
    description="Fetch clean metadata for a GitHub repository by owner and repo name."
)
async def get_repository(
    owner: str,
    repo: str,
    service: GitHubService = Depends(get_github_service)
) -> RepositoryResponse:
    try:
        data = await service.get_repository(owner, repo)
        return RepositoryResponse(**data)
    except GitHubAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except GitHubResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except GitHubAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(exc)}")


@router.get(
    "/repos/{owner}/{repo}/pulls/{pull_number}",
    response_model=PullRequestResponse,
    summary="Get Pull Request Information",
    description="Fetch clean metadata for a Pull Request."
)
async def get_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
    service: GitHubService = Depends(get_github_service)
) -> PullRequestResponse:
    if pull_number <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid PR number: {pull_number}. Must be a positive integer."
        )

    try:
        data = await service.get_pull_request(owner, repo, pull_number)
        return PullRequestResponse(**data)
    except GitHubAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except GitHubResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except GitHubAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(exc)}")


@router.get(
    "/repos/{owner}/{repo}/pulls/{pull_number}/files",
    response_model=List[PullRequestFileResponse],
    summary="Get Pull Request Changed Files",
    description="Fetch list of changed files and unified patches for a Pull Request."
)
async def get_pull_request_files(
    owner: str,
    repo: str,
    pull_number: int,
    service: GitHubService = Depends(get_github_service)
) -> List[PullRequestFileResponse]:
    if pull_number <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid PR number: {pull_number}. Must be a positive integer."
        )

    try:
        files = await service.get_pull_request_files(owner, repo, pull_number)
        return [PullRequestFileResponse(**f) for f in files]
    except GitHubAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except GitHubResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except GitHubAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(exc)}")


@router.post(
    "/repos/{owner}/{repo}/test-pr",
    response_model=CreateTestPRResponse,
    summary="Create Test Pull Request",
    description="Creates a new branch, commits a test Python file with security issues, and opens a Pull Request."
)
async def create_test_pull_request(
    owner: str,
    repo: str,
    request: CreateTestPRRequest = CreateTestPRRequest(),
    service: TestPRService = Depends(get_test_pr_service)
) -> CreateTestPRResponse:
    try:
        data = await service.create_test_pull_request(owner, repo, request.base_branch)
        return CreateTestPRResponse(**data)
    except GitHubAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except GitHubResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except GitHubAPIError as exc:
        code = exc.status_code if exc.status_code else status.HTTP_502_BAD_GATEWAY
        if code == 409:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
        raise HTTPException(status_code=code, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(exc)}")

