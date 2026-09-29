import asyncio
import logging
from typing import Optional
from app.config import get_settings
from app.services.automated_review_service import AutomatedReviewService, REVIEW_RUNS_STORE

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    Celery = None


if CELERY_AVAILABLE:
    celery_app = Celery(
        "ai_code_review_worker",
        broker=settings.redis_broker_url,
        backend=settings.redis_backend_url
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )

    @celery_app.task(
        bind=True,
        name="app.worker.run_automated_review_task",
        max_retries=3,
        default_retry_delay=30,
    )
    def run_automated_review_task(
        self,
        repo_full_name: str,
        pull_number: int,
        commit_sha: str,
        review_mode: Optional[str] = None
    ) -> dict:
        """
        Celery task to run automated PR review pipeline with retry capabilities.
        """
        logger.info(
            "Celery worker received review task for %s PR #%d (commit: %s, attempt: %d)",
            repo_full_name, pull_number, commit_sha, getattr(self.request, "retries", 0) + 1
        )

        try:
            owner, repo = repo_full_name.split("/", 1) if "/" in repo_full_name else ("owner", repo_full_name)
            service = AutomatedReviewService()
            result = asyncio.run(
                service.execute_automated_review(
                    owner=owner,
                    repo=repo,
                    pull_number=pull_number,
                    commit_sha=commit_sha
                )
            )
            logger.info(
                "Celery task finished for %s PR #%d: status=%s",
                repo_full_name, pull_number, result.get("status")
            )
            return result

        except Exception as exc:
            logger.error(
                "Celery task failed for %s PR #%d: %s",
                repo_full_name, pull_number, str(exc)
            )
            err_msg = str(exc).lower()
            is_transient = any(kw in err_msg for kw in ["429", "rate limit", "timeout", "connection", "temporary"])

            retries = getattr(self.request, "retries", 0)
            max_retries = getattr(self, "max_retries", 3)

            if is_transient and retries < max_retries:
                logger.warning("Retrying Celery task due to transient failure: %s", str(exc))
                raise self.retry(exc=exc, countdown=10 * (2 ** retries))

            # Permanent failure or max retries exceeded
            key = (repo_full_name, pull_number, commit_sha)
            if key in REVIEW_RUNS_STORE:
                run = REVIEW_RUNS_STORE[key]
                run.status = "failed"
                run.error_message = f"Task failed: {str(exc)}"

            return {
                "status": "failed",
                "repo_full_name": repo_full_name,
                "pull_number": pull_number,
                "commit_sha": commit_sha,
                "error": str(exc)
            }
else:
    celery_app = None

    def run_automated_review_task(*args, **kwargs):
        raise RuntimeError("Celery is not installed in the python environment.")

