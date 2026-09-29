import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks, Depends, status

from app.config import get_settings
from app.services.webhook_security import verify_github_signature, WebhookSecurityError
from app.services.automated_review_service import AutomatedReviewService

logger = logging.getLogger(__name__)
router = APIRouter()

SUPPORTED_PR_ACTIONS = {"opened", "synchronize", "reopened"}


def get_automated_review_service() -> AutomatedReviewService:
    """Dependency provider for AutomatedReviewService."""
    return AutomatedReviewService()


@router.post(
    "/github",
    status_code=status.HTTP_202_ACCEPTED,
    summary="GitHub Webhook Endpoint",
    description="Receives GitHub webhook events, verifies HMAC signatures, and triggers automated code reviews."
)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    review_service: AutomatedReviewService = Depends(get_automated_review_service)
) -> Dict[str, Any]:
    settings = get_settings()
    # 1. Read raw payload bytes for signature verification
    payload_bytes = await request.body()

    # 2. Verify HMAC SHA-256 signature
    try:
        verify_github_signature(payload_bytes, x_hub_signature_256)
    except WebhookSecurityError as exc:
        logger.warning("Rejected invalid GitHub webhook signature: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc)
        )

    # 3. Parse JSON payload
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {str(exc)}"
        )

    # 4. Filter event type
    event_type = x_github_event or payload.get("event")
    if event_type != "pull_request":
        return {
            "status": "ignored",
            "message": f"Event '{event_type}' ignored. Only 'pull_request' events trigger automated reviews."
        }

    action = payload.get("action")
    if action not in SUPPORTED_PR_ACTIONS:
        return {
            "status": "ignored",
            "message": f"Action '{action}' ignored. Supported actions: {sorted(list(SUPPORTED_PR_ACTIONS))}."
        }

    # 5. Extract PR parameters
    try:
        repo_data = payload["repository"]
        owner = repo_data["owner"]["login"]
        repo = repo_data["name"]
        pull_req = payload["pull_request"]
        pull_number = pull_req["number"]
        commit_sha = pull_req["head"]["sha"]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required GitHub PR payload field: {str(exc)}"
        )

    # 6. Queue review task (Celery or BackgroundTasks)
    repo_full_name = f"{owner}/{repo}"

    if settings.USE_CELERY:
        try:
            from app.worker import run_automated_review_task
            run_automated_review_task.delay(
                repo_full_name=repo_full_name,
                pull_number=pull_number,
                commit_sha=commit_sha
            )
            logger.info("Queued Celery review task for %s PR #%d", repo_full_name, pull_number)
        except Exception as exc:
            logger.error("Failed to queue Celery task, falling back to in-memory execution: %s", str(exc))
            background_tasks.add_task(
                review_service.execute_automated_review,
                owner=owner,
                repo=repo,
                pull_number=pull_number,
                commit_sha=commit_sha
            )
    else:
        background_tasks.add_task(
            review_service.execute_automated_review,
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            commit_sha=commit_sha
        )

    return {
        "status": "queued",
        "message": f"Automated AI Code Review queued for {owner}/{repo} PR #{pull_number} (commit {commit_sha[:7]}).",
        "owner": owner,
        "repo": repo,
        "pull_number": pull_number,
        "commit_sha": commit_sha
    }

