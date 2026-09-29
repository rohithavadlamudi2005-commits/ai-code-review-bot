from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Category(str, Enum):
    SECURITY = "security"
    QUALITY = "quality"


class Finding(BaseModel):
    """
    Structured model representing a single static analysis finding/issue.
    """
    rule_id: str = Field(..., description="Unique rule identifier (e.g., PY-SEC-001)")
    category: str = Field(..., description="Finding category ('security' or 'quality')")
    severity: str = Field(..., description="Severity level: CRITICAL, HIGH, MEDIUM, LOW, INFO")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    file: str = Field(..., description="Relative or base filename being analyzed")
    line: int = Field(..., ge=1, description="Line number of the finding")
    message: str = Field(..., description="Short summary message")
    explanation: str = Field(..., description="Detailed explanation of the rule violation")
    suggestion: str = Field(..., description="Actionable recommendation or fix suggestion")


class CodeAnalysisRequest(BaseModel):
    """
    Request payload for single file static code analysis.
    """
    filename: str
    source_code: str
    changed_lines: Optional[List[int]] = None


class CodeAnalysisResponse(BaseModel):
    """
    Response payload for single file static code analysis.
    """
    filename: str
    findings: List[Finding] = Field(default_factory=list)
    total_findings: int = 0
    skipped: bool = False
    skip_reason: Optional[str] = None


class PRAnalysisRequest(BaseModel):
    """
    Request payload for analyzing an entire GitHub Pull Request.
    """
    owner: str
    repo: str
    pull_number: int


class SkippedFileSummary(BaseModel):
    filename: str
    reason: str


class PRAnalysisResponse(BaseModel):
    """
    Response payload aggregating findings across all changed files in a PR.
    """
    owner: str
    repo: str
    pull_number: int
    total_findings: int = 0
    severity_counts: Dict[str, int] = Field(
        default_factory=lambda: {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    )
    analyzed_files_count: int = 0
    skipped_files_count: int = 0
    findings: List[Finding] = Field(default_factory=list)
    skipped_files: List[SkippedFileSummary] = Field(default_factory=list)
