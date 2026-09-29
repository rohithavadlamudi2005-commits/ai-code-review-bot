import logging
from typing import Dict, Any, List, Optional
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class GitHubServiceError(Exception):
    """Base exception for GitHub Service errors."""
    pass


class GitHubAuthenticationError(GitHubServiceError):
    """Raised when authentication fails (401 Unauthorized)."""
    pass


class GitHubResourceNotFoundError(GitHubServiceError):
    """Raised when a repository or PR is not found (404 Not Found)."""
    pass


class GitHubRateLimitError(GitHubServiceError):
    """Raised when GitHub API rate limits are exceeded (403/429)."""
    pass


class GitHubAPIError(GitHubServiceError):
    """Raised for general GitHub API errors or unexpected status codes."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GitHubService:
    """
    Service for interacting with GitHub REST API v3.
    """

    def __init__(self, token: Optional[str] = None, api_url: Optional[str] = None):
        settings = get_settings()
        self.token = token if token is not None else settings.GITHUB_TOKEN
        self.api_url = (api_url if api_url is not None else settings.GITHUB_API_URL).rstrip("/")

    def _get_headers(self, accept: str = "application/vnd.github.v3+json") -> Dict[str, str]:
        """
        Constructs request headers, securely attaching authorization if token is configured.
        """
        headers = {
            "Accept": accept,
            "User-Agent": "AI-Code-Review-Bot/1.0",
        }
        if self.token and self.token.strip():
            headers["Authorization"] = f"Bearer {self.token.strip()}"
        return headers

    def _handle_error_response(self, response: httpx.Response, owner: str, repo: str, pull_number: Optional[int] = None):
        """
        Translates HTTP status codes into specific domain exceptions without exposing token details.
        """
        status = response.status_code
        try:
            error_data = response.json()
            message = error_data.get("message", response.text)
        except Exception:
            message = response.text or f"HTTP {status}"

        # 401 Unauthorized
        if status == 401:
            raise GitHubAuthenticationError(
                "Invalid or expired GitHub token. Please verify GITHUB_TOKEN environment variable."
            )

        # 403 Forbidden / 429 Rate Limit
        if status in (403, 429):
            remaining = response.headers.get("x-ratelimit-remaining")
            if remaining == "0" or "rate limit" in message.lower() or "secondary rate limit" in message.lower():
                raise GitHubRateLimitError(
                    "GitHub API rate limit exceeded. Please supply a valid GITHUB_TOKEN or wait before retrying."
                )
            raise GitHubAPIError(f"Access forbidden by GitHub API: {message}", status_code=status)

        # 404 Not Found
        if status == 404:
            resource = f"Pull Request #{pull_number} in '{owner}/{repo}'" if pull_number else f"Repository '{owner}/{repo}'"
            raise GitHubResourceNotFoundError(f"{resource} was not found on GitHub.")

        # Other HTTP errors
        raise GitHubAPIError(
            f"GitHub API error for '{owner}/{repo}' (HTTP {status}): {message}",
            status_code=status
        )

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Fetches repository metadata from GitHub.
        """
        url = f"{self.api_url}/repos/{owner}/{repo}"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers)
            except httpx.RequestError as exc:
                raise GitHubAPIError(f"Failed to connect to GitHub API: {str(exc)}")

            if response.status_code != 200:
                self._handle_error_response(response, owner, repo)

            data = response.json()
            return {
                "id": data["id"],
                "owner": data["owner"]["login"],
                "name": data["name"],
                "full_name": data["full_name"],
                "description": data.get("description"),
                "default_branch": data.get("default_branch", "main"),
                "is_private": data.get("private", False),
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues_count": data.get("open_issues_count", 0),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
            }

    async def get_pull_request(self, owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        """
        Fetches Pull Request information from GitHub.
        """
        if pull_number <= 0:
            raise GitHubResourceNotFoundError(f"Invalid PR number: {pull_number}")

        url = f"{self.api_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers)
            except httpx.RequestError as exc:
                raise GitHubAPIError(f"Failed to connect to GitHub API: {str(exc)}")

            if response.status_code != 200:
                self._handle_error_response(response, owner, repo, pull_number)

            data = response.json()
            return {
                "repository": f"{owner}/{repo}",
                "pull_number": data["number"],
                "title": data.get("title", ""),
                "description": data.get("body") or "",
                "author": data["user"]["login"] if data.get("user") else "unknown",
                "state": data.get("state", "open"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "head_branch": data["head"]["ref"],
                "head_sha": data["head"]["sha"],
                "base_branch": data["base"]["ref"],
                "base_sha": data["base"]["sha"],
                "changed_files_count": data.get("changed_files", 0),
                "additions": data.get("additions", 0),
                "deletions": data.get("deletions", 0),
                "draft": data.get("draft", False),
            }

    async def get_pull_request_files(self, owner: str, repo: str, pull_number: int) -> List[Dict[str, Any]]:
        """
        Fetches list of changed files for a Pull Request from GitHub.
        """
        if pull_number <= 0:
            raise GitHubResourceNotFoundError(f"Invalid PR number: {pull_number}")

        url = f"{self.api_url}/repos/{owner}/{repo}/pulls/{pull_number}/files"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers, params={"per_page": 100})
            except httpx.RequestError as exc:
                raise GitHubAPIError(f"Failed to connect to GitHub API: {str(exc)}")

            if response.status_code != 200:
                self._handle_error_response(response, owner, repo, pull_number)

            items = response.json()
            clean_files = []
            for item in items:
                clean_files.append({
                    "filename": item.get("filename", ""),
                    "status": item.get("status", "modified"),
                    "additions": item.get("additions", 0),
                    "deletions": item.get("deletions", 0),
                    "changes": item.get("changes", 0),
                    "patch": item.get("patch"),
                })
            return clean_files

    async def get_pull_request_diff(self, owner: str, repo: str, pull_number: int) -> str:
        """
        Fetches the unified diff / patch representation of a Pull Request.
        """
        if pull_number <= 0:
            raise GitHubResourceNotFoundError(f"Invalid PR number: {pull_number}")

        url = f"{self.api_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        headers = self._get_headers(accept="application/vnd.github.v3.diff")

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers)
            except httpx.RequestError as exc:
                raise GitHubAPIError(f"Failed to connect to GitHub API: {str(exc)}")

            if response.status_code != 200:
                self._handle_error_response(response, owner, repo, pull_number)

            return response.text

    async def get_file_content(self, owner: str, repo: str, path: str, ref: Optional[str] = None) -> str:
        """
        Fetches raw text content of a file from GitHub repository at a given git ref/sha.
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params["ref"] = ref
        headers = self._get_headers(accept="application/vnd.github.v3.raw")

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    return response.text
            except Exception as exc:
                logger.debug("Failed to fetch raw file content for %s: %s", path, str(exc))
            return ""

    async def post_pull_request_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        commit_sha: str,
        body: str,
        event: str = "COMMENT",
        comments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Posts a Pull Request Review to GitHub containing a summary body and optional inline line comments.
        If posting inline comments fails due to invalid diff line positions, falls back to summary body submission.
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
        headers = self._get_headers()

        payload: Dict[str, Any] = {
            "commit_id": commit_sha,
            "body": body,
            "event": event.upper() if event in ("COMMENT", "REQUEST_CHANGES", "APPROVE") else "COMMENT",
        }
        if comments:
            payload["comments"] = comments

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.RequestError as exc:
                raise GitHubAPIError(f"Failed to connect to GitHub API when posting review: {str(exc)}")

            # If inline comments caused 422 Unprocessable Entity, fallback to posting summary without inline comments
            if response.status_code == 422 and comments:
                logger.warning(
                    "GitHub rejected inline review comments for %s/%s PR #%s. Retrying summary-only review.",
                    owner, repo, pull_number
                )
                payload.pop("comments", None)
                response = await client.post(url, headers=headers, json=payload)

            if response.status_code not in (200, 201):
                self._handle_error_response(response, owner, repo, pull_number)

            return response.json()

    async def get_branch_sha(self, owner: str, repo: str, branch: str = "main") -> str:
        """
        Fetches the latest commit SHA for a given branch in GitHub repository.
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/git/ref/heads/{branch}"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers)
            except httpx.RequestError as exc:
                raise GitHubAPIError(f"Failed to connect to GitHub API: {str(exc)}")

            if response.status_code != 200:
                self._handle_error_response(response, owner, repo)

            data = response.json()
            return data["object"]["sha"]

    async def create_branch(self, owner: str, repo: str, new_branch: str, sha: str) -> Dict[str, Any]:
        """
        Creates a new Git branch (ref) from a given target commit SHA.
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/git/refs"
        headers = self._get_headers()
        payload = {
            "ref": f"refs/heads/{new_branch}",
            "sha": sha
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.RequestError as exc:
                raise GitHubAPIError(f"Failed to connect to GitHub API when creating branch: {str(exc)}")

            if response.status_code in (409, 422):
                raise GitHubAPIError(f"Branch '{new_branch}' already exists or invalid ref.", status_code=response.status_code)

            if response.status_code != 201:
                self._handle_error_response(response, owner, repo)

            return response.json()

    async def create_file_commit(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str
    ) -> Dict[str, Any]:
        """
        Creates or updates a file in GitHub repository branch by encoding content in base64.
        """
        import base64
        url = f"{self.api_url}/repos/{owner}/{repo}/contents/{path}"
        headers = self._get_headers()
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        payload = {
            "message": message,
            "content": encoded_content,
            "branch": branch
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.put(url, headers=headers, json=payload)
            except httpx.RequestError as exc:
                raise GitHubAPIError(f"Failed to connect to GitHub API when committing file: {str(exc)}")

            if response.status_code not in (200, 201):
                self._handle_error_response(response, owner, repo)

            return response.json()

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a Pull Request in GitHub repository from head branch to base branch.
        """
        url = f"{self.api_url}/repos/{owner}/{repo}/pulls"
        headers = self._get_headers()
        payload = {
            "title": title,
            "head": head,
            "base": base,
            "body": body or ""
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.RequestError as exc:
                raise GitHubAPIError(f"Failed to connect to GitHub API when creating PR: {str(exc)}")

            if response.status_code not in (200, 201):
                self._handle_error_response(response, owner, repo)

            return response.json()
