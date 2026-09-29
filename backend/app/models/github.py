from typing import Optional, List
from pydantic import BaseModel


class RepositoryResponse(BaseModel):
    """
    Clean JSON response model for GitHub Repository.
    """
    id: int
    owner: str
    name: str
    full_name: str
    description: Optional[str] = None
    default_branch: str
    is_private: bool
    stars: int
    forks: int
    open_issues_count: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PullRequestResponse(BaseModel):
    """
    Clean JSON response model for GitHub Pull Request.
    """
    repository: str
    pull_number: int
    title: str
    description: Optional[str] = None
    author: str
    state: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    head_branch: str
    head_sha: str
    base_branch: str
    base_sha: str
    changed_files_count: int
    additions: int
    deletions: int
    draft: bool = False


class PullRequestFileResponse(BaseModel):
    """
    Clean JSON response model for a single changed file in a Pull Request.
    """
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None


class CreateTestPRRequest(BaseModel):
    """
    Request payload for creating a test Pull Request.
    """
    base_branch: str = "main"


class CreateTestPRResponse(BaseModel):
    """
    Response model after creating a test Pull Request.
    """
    status: str
    owner: str
    repo: str
    branch_name: str
    pull_number: int
    html_url: str
    title: str
    base_branch: str
    created_at: Optional[str] = None

