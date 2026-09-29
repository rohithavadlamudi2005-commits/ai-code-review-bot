from fastapi import APIRouter, HTTPException, Depends, status

from app.services.review_service import (
    ReviewService,
    ReviewCodeRequest,
    ReviewCodeResponse,
    ReviewPRRequest,
    ReviewPRResponse,
)
from app.services.github_service import (
    GitHubAuthenticationError,
    GitHubResourceNotFoundError,
    GitHubRateLimitError,
    GitHubAPIError,
)
from app.services.automated_review_service import AutomatedReviewService

router = APIRouter()


def get_review_service() -> ReviewService:
    """Dependency provider for ReviewService."""
    return ReviewService()


@router.post(
    "/code",
    response_model=ReviewCodeResponse,
    summary="Run Combined Code Review on Snippet",
    description="Runs Stage 3 deterministic static analysis + Stage 4 LLM code review on a source snippet."
)
async def review_code(
    request: ReviewCodeRequest,
    service: ReviewService = Depends(get_review_service)
) -> ReviewCodeResponse:
    if not request.filename or not request.filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must be provided."
        )

    try:
        return await service.review_code(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Review engine error: {str(exc)}"
        )


@router.post(
    "/pr",
    response_model=ReviewPRResponse,
    summary="Run Combined AI Code Review on Pull Request",
    description="Fetches PR files, runs Stage 3 static analysis + Stage 4 LLM review, and returns combined findings."
)
async def review_pr(
    request: ReviewPRRequest,
    service: ReviewService = Depends(get_review_service)
) -> ReviewPRResponse:
    if not request.owner or not request.repo or request.pull_number <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid repository owner, repo name, and positive pull_number are required."
        )

    try:
        return await service.review_pr(request)
    except GitHubAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except GitHubResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except GitHubAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during PR review: {str(exc)}"
        )


@router.post(
    "/pr/{owner}/{repo}/{pull_number}/run",
    summary="Manually Trigger Automated Review Pipeline",
    description="Fetches PR head commit, executes static + LLM analysis, posts GitHub review, and records run metadata."
)
async def run_automated_review_manually(
    owner: str,
    repo: str,
    pull_number: int,
    service: ReviewService = Depends(get_review_service)
):
    if pull_number <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PR number.")

    try:
        pr_info = await service.github_service.get_pull_request(owner, repo, pull_number)
        commit_sha = pr_info.get("head_sha", "HEAD")

        auto_service = AutomatedReviewService(
            github_service=service.github_service,
            review_service=service
        )

        return await auto_service.execute_automated_review(owner, repo, pull_number, commit_sha)
    except GitHubAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except GitHubResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    except GitHubAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Automated review failed: {str(exc)}"
        )


@router.get(
    "/runs/{owner}/{repo}/{pull_number}",
    summary="Get PR Review Run Status",
    description="Returns the latest automated review execution status for a given PR."
)
async def get_pr_review_run_status(
    owner: str,
    repo: str,
    pull_number: int
):
    auto_service = AutomatedReviewService()
    run_info = auto_service.get_latest_run_for_pr(owner, repo, pull_number)
    if not run_info:
        return {
            "status": "NOT_RUN",
            "message": f"No review execution records found for {owner}/{repo} PR #{pull_number}."
        }
    return run_info
