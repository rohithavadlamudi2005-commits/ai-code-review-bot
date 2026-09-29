import datetime
import uuid
import logging
from typing import Dict, Any, Optional

from app.services.github_service import (
    GitHubService,
    GitHubAuthenticationError,
    GitHubResourceNotFoundError,
    GitHubRateLimitError,
    GitHubAPIError,
)

logger = logging.getLogger(__name__)

TEST_FILE_PATH = "ai_review_test.py"
TEST_FILE_CONTENT = """def process_user_input(user_input):
    result = eval(user_input)
    return result
"""


class TestPRService:
    """
    Service for creating test Pull Requests with intentionally vulnerable Python code
    to test the AI Code Review Bot end-to-end.
    """
    __test__ = False

    def __init__(self, github_service: Optional[GitHubService] = None):
        self.github_service = github_service if github_service is not None else GitHubService()

    async def create_test_pull_request(
        self,
        owner: str,
        repo: str,
        base_branch: str = "main"
    ) -> Dict[str, Any]:
        """
        End-to-end pipeline:
        1. Fetches base branch SHA
        2. Creates a unique Git branch
        3. Commits ai_review_test.py with vulnerable code
        4. Opens a Pull Request targeting base_branch
        """
        if not owner or not owner.strip() or not repo or not repo.strip():
            raise GitHubAPIError("Owner and repository name are required.", status_code=400)

        owner = owner.strip()
        repo = repo.strip()
        base_branch = (base_branch or "main").strip()

        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
        unique_suffix = str(uuid.uuid4())[:6]
        branch_name = f"test-ai-review-{timestamp}-{unique_suffix}"

        # 1. Get Base Branch SHA
        base_sha = await self.github_service.get_branch_sha(owner, repo, base_branch)

        # 2. Create new Git Branch
        await self.github_service.create_branch(owner, repo, branch_name, base_sha)

        # 3. Create ai_review_test.py on the new branch
        commit_message = "Add vulnerable test code for AI Code Review"
        await self.github_service.create_file_commit(
            owner=owner,
            repo=repo,
            path=TEST_FILE_PATH,
            content=TEST_FILE_CONTENT,
            message=commit_message,
            branch=branch_name
        )

        # 4. Create Pull Request targeting base_branch
        pr_title = f"Test PR: Vulnerable Code Review Sample ({timestamp})"
        pr_body = (
            "This is an automated test Pull Request created by the AI Code Review Bot.\n\n"
            "**File added:** `ai_review_test.py`\n"
            "**Note:** Do NOT merge this pull request."
        )

        pr_data = await self.github_service.create_pull_request(
            owner=owner,
            repo=repo,
            title=pr_title,
            head=branch_name,
            base=base_branch,
            body=pr_body
        )

        return {
            "status": "created",
            "owner": owner,
            "repo": repo,
            "branch_name": branch_name,
            "pull_number": pr_data.get("number"),
            "html_url": pr_data.get("html_url"),
            "title": pr_data.get("title", pr_title),
            "base_branch": base_branch,
            "created_at": pr_data.get("created_at")
        }
