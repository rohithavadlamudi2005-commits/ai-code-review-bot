import pytest
from unittest.mock import patch, MagicMock
from app.worker import celery_app, run_automated_review_task


def test_celery_app_configuration():
    assert celery_app.main == "ai_code_review_worker"
    assert celery_app.conf.task_serializer == "json"


@patch("app.worker.AutomatedReviewService.execute_automated_review")
def test_run_automated_review_task_success(mock_execute):
    mock_execute.return_value = {
        "status": "completed",
        "findings_count": 3
    }

    res = run_automated_review_task(
        repo_full_name="owner/repo",
        pull_number=1,
        commit_sha="abc1234"
    )

    assert res["status"] == "completed"
    assert res["findings_count"] == 3


@patch("app.worker.AutomatedReviewService.execute_automated_review")
def test_run_automated_review_task_error(mock_execute):
    mock_execute.side_effect = Exception("Permanent error occurred")

    res = run_automated_review_task(
        repo_full_name="owner/repo",
        pull_number=1,
        commit_sha="abc1234"
    )

    assert res["status"] == "failed"
    assert "Permanent error occurred" in res["error"]

