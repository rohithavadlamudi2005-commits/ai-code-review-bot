import datetime
import logging
from typing import Dict, Any, Optional, List
from app.config import get_settings
from app.services.github_service import GitHubService, GitHubAPIError
from app.services.review_service import ReviewService, ReviewPRRequest, ReviewPRResponse
from app.services.github_review_formatter import GitHubReviewFormatter

logger = logging.getLogger(__name__)

# In-memory store for tracking review runs and enforcing idempotency
# Key: (repo_full_name, pull_number, commit_sha) -> Value: run_metadata dict
REVIEW_RUNS_STORE: Dict[str, Dict[str, Any]] = {}


class AutomatedReviewService:
    """
    Service for executing automated GitHub Pull Request reviews, tracking execution runs,
    enforcing idempotency per commit SHA, formatting reviews, and posting to GitHub.
    """

    def __init__(
        self,
        github_service: Optional[GitHubService] = None,
        review_service: Optional[ReviewService] = None
    ):
        self.github_service = github_service if github_service is not None else GitHubService()
        self.review_service = review_service if review_service is not None else ReviewService()
        self.settings = get_settings()

    def _get_run_key(self, repo_full_name: str, pull_number: int, commit_sha: str) -> str:
        return f"{repo_full_name.lower()}#{pull_number}@{commit_sha}"

    def get_review_run(self, owner: str, repo: str, pull_number: int, commit_sha: str) -> Optional[Dict[str, Any]]:
        repo_full_name = f"{owner}/{repo}"
        key = self._get_run_key(repo_full_name, pull_number, commit_sha)
        return REVIEW_RUNS_STORE.get(key)

    def get_latest_run_for_pr(self, owner: str, repo: str, pull_number: int) -> Optional[Dict[str, Any]]:
        prefix = f"{owner.lower()}/{repo.lower()}#{pull_number}@"
        matching_runs = [run for key, run in REVIEW_RUNS_STORE.items() if key.startswith(prefix)]
        if not matching_runs:
            return None
        return max(matching_runs, key=lambda r: r.get("created_at", ""))

    async def execute_automated_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        commit_sha: str
    ) -> Dict[str, Any]:
        """
        Executes end-to-end automated code review for a PR commit, enforcing idempotency.
        """
        repo_full_name = f"{owner}/{repo}"
        key = self._get_run_key(repo_full_name, pull_number, commit_sha)

        # 1. Idempotency check: verify if review already ran for this commit SHA
        existing_run = REVIEW_RUNS_STORE.get(key)
        if existing_run and existing_run.get("status") == "completed":
            logger.info("Idempotent check: Review already completed for %s", key)
            return existing_run

        if existing_run and existing_run.get("status") == "running":
            logger.info("Review currently in progress for %s", key)
            return existing_run

        # 2. Register/queue run
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        run_data = {
            "repo_full_name": repo_full_name,
            "pull_number": pull_number,
            "commit_sha": commit_sha,
            "status": "running",
            "started_at": now_iso,
            "completed_at": None,
            "findings_count": 0,
            "github_review_id": None,
            "error_message": None,
            "created_at": now_iso
        }
        REVIEW_RUNS_STORE[key] = run_data

        try:
            # 3. Execute Stage 3 + Stage 4 Combined Code Review
            review_resp: ReviewPRResponse = await self.review_service.review_pr(
                ReviewPRRequest(owner=owner, repo=repo, pull_number=pull_number)
            )

            # 4. Format Markdown summary body & inline comments
            summary_markdown = GitHubReviewFormatter.format_review_summary(
                findings=review_resp.combined_findings,
                severity_counts=review_resp.severity_counts,
                analyzed_files_count=review_resp.analyzed_files_count,
                skipped_files_count=review_resp.skipped_files_count
            )

            inline_comments, _ = GitHubReviewFormatter.prepare_inline_comments(review_resp.combined_findings)

            # 5. Post review to GitHub
            review_mode = self.settings.GITHUB_REVIEW_MODE or "COMMENT"
            posted_review = await self.github_service.post_pull_request_review(
                owner=owner,
                repo=repo,
                pull_number=pull_number,
                commit_sha=commit_sha,
                body=summary_markdown,
                event=review_mode,
                comments=inline_comments if inline_comments else None
            )

            review_id = posted_review.get("id") if isinstance(posted_review, dict) else None

            # 6. Update run metadata to completed
            completed_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            run_data.update({
                "status": "completed",
                "completed_at": completed_iso,
                "findings_count": len(review_resp.combined_findings),
                "github_review_id": review_id,
            })
            REVIEW_RUNS_STORE[key] = run_data
            return run_data

        except Exception as exc:
            error_msg = str(exc)
            logger.error("Automated review failed for %s: %s", key, error_msg)
            run_data.update({
                "status": "failed",
                "error_message": error_msg,
                "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
            REVIEW_RUNS_STORE[key] = run_data
            return run_data
