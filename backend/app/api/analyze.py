from fastapi import APIRouter, HTTPException, Depends, status

from app.models.finding import (
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    PRAnalysisRequest,
    PRAnalysisResponse,
)
from app.analyzers.engine import AnalysisEngine
from app.services.github_service import (
    GitHubService,
    GitHubAuthenticationError,
    GitHubResourceNotFoundError,
    GitHubRateLimitError,
    GitHubAPIError,
)

router = APIRouter()


def get_analysis_engine() -> AnalysisEngine:
    """Dependency provider for AnalysisEngine."""
    return AnalysisEngine()


def get_github_service() -> GitHubService:
    """Dependency provider for GitHubService."""
    return GitHubService()


@router.post(
    "/code",
    response_model=CodeAnalysisResponse,
    summary="Analyze Single Code Snippet / File",
    description="Runs static analysis rules on provided source code and optional changed lines."
)
async def analyze_code(
    request: CodeAnalysisRequest,
    engine: AnalysisEngine = Depends(get_analysis_engine)
) -> CodeAnalysisResponse:
    if not request.filename or not request.filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must be provided."
        )

    try:
        return engine.analyze_file(
            filename=request.filename,
            source_code=request.source_code,
            changed_lines=request.changed_lines
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis engine error: {str(exc)}"
        )


@router.post(
    "/pr",
    response_model=PRAnalysisResponse,
    summary="Analyze GitHub Pull Request",
    description="Fetches PR changed files, parses unified diffs, and runs static code analysis."
)
async def analyze_pr(
    request: PRAnalysisRequest,
    engine: AnalysisEngine = Depends(get_analysis_engine),
    github_service: GitHubService = Depends(get_github_service)
) -> PRAnalysisResponse:
    if not request.owner or not request.repo or request.pull_number <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid repository owner, repo name, and positive pull_number are required."
        )

    try:
        return await engine.analyze_pr(
            owner=request.owner,
            repo=request.repo,
            pull_number=request.pull_number,
            github_service=github_service
        )
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
            detail=f"Unexpected error during PR static analysis: {str(exc)}"
        )
