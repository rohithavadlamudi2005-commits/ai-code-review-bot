import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.automated_review_service import AutomatedReviewService, REVIEW_RUNS_STORE
from app.services.review_service import ReviewPRResponse, CombinedFinding


@pytest.mark.asyncio
async def test_automated_review_service_pipeline_and_idempotency():
    mock_github = MagicMock()
    mock_github.post_pull_request_review = AsyncMock(return_value={"id": 9999})

    mock_review_service = MagicMock()
    mock_review_resp = ReviewPRResponse(
        owner="octocat",
        repo="Hello-World",
        pull_number=1,
        static_findings_count=1,
        llm_findings_count=0,
        combined_findings_count=1,
        severity_counts={"CRITICAL": 0, "HIGH": 1, "MEDIUM": 0, "LOW": 0, "INFO": 0},
        analyzed_files_count=1,
        skipped_files_count=0,
        combined_findings=[
            CombinedFinding(
                id="1",
                category="security",
                severity="HIGH",
                confidence=0.9,
                file="main.py",
                line=10,
                message="Security issue",
                explanation="Expl",
                suggestion="Sugg",
                source="static",
                static_rule_id="PY-SEC-001"
            )
        ]
    )
    mock_review_service.review_pr = AsyncMock(return_value=mock_review_resp)

    service = AutomatedReviewService(
        github_service=mock_github,
        review_service=mock_review_service
    )

    commit_sha = "abc123456789"
    # 1. Execute initial run
    result1 = await service.execute_automated_review("octocat", "Hello-World", 1, commit_sha)
    assert result1["status"] == "completed"
    assert result1["findings_count"] == 1
    assert result1["github_review_id"] == 9999

    mock_review_service.review_pr.assert_called_once()
    mock_github.post_pull_request_review.assert_called_once()

    # 2. Re-run for the EXACT same commit SHA -> Idempotency check prevents duplicate review run
    mock_review_service.review_pr.reset_mock()
    mock_github.post_pull_request_review.reset_mock()

    result2 = await service.execute_automated_review("octocat", "Hello-World", 1, commit_sha)
    assert result2["status"] == "completed"
    mock_review_service.review_pr.assert_not_called()
    mock_github.post_pull_request_review.assert_not_called()


@pytest.mark.asyncio
async def test_automated_review_different_commit_sha_executes_new_run():
    mock_github = MagicMock()
    mock_github.post_pull_request_review = AsyncMock(return_value={"id": 10000})

    mock_review_service = MagicMock()
    mock_review_resp = ReviewPRResponse(
        owner="octocat", repo="Hello-World", pull_number=1,
        analyzed_files_count=1, combined_findings=[]
    )
    mock_review_service.review_pr = AsyncMock(return_value=mock_review_resp)

    service = AutomatedReviewService(github_service=mock_github, review_service=mock_review_service)

    result = await service.execute_automated_review("octocat", "Hello-World", 1, "sha_new_commit_999")
    assert result["status"] == "completed"
    mock_review_service.review_pr.assert_called_once()
