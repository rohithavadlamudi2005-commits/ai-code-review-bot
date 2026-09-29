import logging
import os
from typing import List, Optional, Dict, Set
from pydantic import BaseModel, Field

from app.analyzers.engine import AnalysisEngine
from app.services.github_service import GitHubService
from app.services.diff_parser import DiffParser
from app.services.llm_review_service import LLMReviewService
from app.models.finding import Finding
from app.llm.schemas import LLMFinding

logger = logging.getLogger(__name__)


class CombinedFinding(BaseModel):
    """
    Unified finding model combining deterministic static rule analysis and LLM code review insights.
    """
    id: str = Field(..., description="Unique finding identifier")
    category: str = Field(..., description="Category ('security' or 'quality')")
    severity: str = Field(..., description="Severity level: CRITICAL, HIGH, MEDIUM, LOW, INFO")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    file: str = Field(..., description="Filename")
    line: Optional[int] = Field(None, description="Line number of finding, or null if general")
    message: str = Field(..., description="Short finding summary title")
    explanation: str = Field(..., description="Detailed rationale")
    suggestion: str = Field(..., description="Recommended fix")
    evidence: Optional[str] = Field(None, description="Code snippet evidence")
    source: str = Field(..., description="Source of finding: 'static', 'llm', or 'combined'")
    static_rule_id: Optional[str] = Field(None, description="Static rule ID if applicable")


class ReviewCodeRequest(BaseModel):
    filename: str
    source_code: str
    changed_lines: Optional[List[int]] = None
    diff_patch: Optional[str] = None


class ReviewCodeResponse(BaseModel):
    filename: str
    static_findings: List[Finding] = Field(default_factory=list)
    llm_findings: List[LLMFinding] = Field(default_factory=list)
    combined_findings: List[CombinedFinding] = Field(default_factory=list)
    total_findings: int = 0


class ReviewPRRequest(BaseModel):
    owner: str
    repo: str
    pull_number: int


class ReviewPRResponse(BaseModel):
    owner: str
    repo: str
    pull_number: int
    static_findings_count: int = 0
    llm_findings_count: int = 0
    combined_findings_count: int = 0
    severity_counts: Dict[str, int] = Field(
        default_factory=lambda: {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    )
    analyzed_files_count: int = 0
    skipped_files_count: int = 0
    static_findings: List[Finding] = Field(default_factory=list)
    llm_findings: List[LLMFinding] = Field(default_factory=list)
    combined_findings: List[CombinedFinding] = Field(default_factory=list)


class ReviewService:
    """
    Main orchestration service for running combined Static + LLM Code Reviews.
    """

    def __init__(
        self,
        analysis_engine: Optional[AnalysisEngine] = None,
        llm_service: Optional[LLMReviewService] = None,
        github_service: Optional[GitHubService] = None
    ):
        self.engine = analysis_engine if analysis_engine is not None else AnalysisEngine()
        self.llm_service = llm_service if llm_service is not None else LLMReviewService()
        self.github_service = github_service if github_service is not None else GitHubService()

    def combine_findings(
        self,
        filename: str,
        static_findings: List[Finding],
        llm_findings: List[LLMFinding]
    ) -> List[CombinedFinding]:
        """
        Deduplicates and merges Stage 3 static findings and Stage 4 LLM findings.
        """
        combined: List[CombinedFinding] = []
        matched_llm_indices: Set[int] = set()

        for idx, sf in enumerate(static_findings):
            matched_llm: Optional[LLMFinding] = None
            matched_llm_idx: Optional[int] = None

            for l_idx, lf in enumerate(llm_findings):
                if l_idx in matched_llm_indices:
                    continue
                # Line matching check (within 2 lines)
                same_file = (sf.file == lf.file or lf.file == filename)
                line_match = (sf.line is not None and lf.line is not None and abs(sf.line - lf.line) <= 2)

                if same_file and line_match:
                    matched_llm = lf
                    matched_llm_idx = l_idx
                    break

            if matched_llm and matched_llm_idx is not None:
                matched_llm_indices.add(matched_llm_idx)
                combined.append(CombinedFinding(
                    id=f"COMBINED-{sf.rule_id}-{sf.line}",
                    category=sf.category,
                    severity=sf.severity,
                    confidence=max(sf.confidence, matched_llm.confidence),
                    file=sf.file,
                    line=sf.line,
                    message=sf.message,
                    explanation=f"{sf.explanation}\n\n[AI LLM Insight]: {matched_llm.explanation}",
                    suggestion=matched_llm.suggestion or sf.suggestion,
                    evidence=matched_llm.evidence,
                    source="combined",
                    static_rule_id=sf.rule_id
                ))
            else:
                combined.append(CombinedFinding(
                    id=f"STATIC-{sf.rule_id}-{sf.line}",
                    category=sf.category,
                    severity=sf.severity,
                    confidence=sf.confidence,
                    file=sf.file,
                    line=sf.line,
                    message=sf.message,
                    explanation=sf.explanation,
                    suggestion=sf.suggestion,
                    evidence=None,
                    source="static",
                    static_rule_id=sf.rule_id
                ))

        # Add remaining unmatched LLM findings
        for l_idx, lf in enumerate(llm_findings):
            if l_idx not in matched_llm_indices:
                combined.append(CombinedFinding(
                    id=f"LLM-{lf.category.upper()}-{lf.line or 0}-{l_idx}",
                    category=lf.category,
                    severity=lf.severity,
                    confidence=lf.confidence,
                    file=lf.file or filename,
                    line=lf.line,
                    message=lf.message,
                    explanation=lf.explanation,
                    suggestion=lf.suggestion,
                    evidence=lf.evidence,
                    source="llm",
                    static_rule_id=None
                ))

        return combined

    async def review_code(self, request: ReviewCodeRequest) -> ReviewCodeResponse:
        """
        Executes static analysis and LLM review for a single code snippet or file.
        """
        static_resp = self.engine.analyze_file(request.filename, request.source_code, request.changed_lines)
        static_findings = static_resp.findings

        llm_findings: List[LLMFinding] = []
        if not static_resp.skipped:
            llm_findings = await self.llm_service.review_file(
                filename=request.filename,
                source_code=request.source_code,
                diff_patch=request.diff_patch,
                changed_lines=request.changed_lines,
                static_findings=static_findings
            )

        combined = self.combine_findings(request.filename, static_findings, llm_findings)

        return ReviewCodeResponse(
            filename=request.filename,
            static_findings=static_findings,
            llm_findings=llm_findings,
            combined_findings=combined,
            total_findings=len(combined)
        )

    async def review_pr(self, request: ReviewPRRequest) -> ReviewPRResponse:
        """
        Executes static analysis and LLM review across all changed files in a GitHub PR.
        """
        pr_info = await self.github_service.get_pull_request(request.owner, request.repo, request.pull_number)
        files = await self.github_service.get_pull_request_files(request.owner, request.repo, request.pull_number)

        head_sha = pr_info.get("head_sha")

        all_static: List[Finding] = []
        all_llm: List[LLMFinding] = []
        all_combined: List[CombinedFinding] = []

        analyzed_count = 0
        skipped_count = 0
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}

        for file_item in files[:self.engine.analyzers[0].supported_extensions and 15]:
            filename = file_item.get("filename", "")
            patch = file_item.get("patch")
            status = file_item.get("status", "")

            if status == "removed" or not self.engine.is_supported_file(filename):
                skipped_count += 1
                continue

            parsed_diff = DiffParser.parse_patch(patch, filename)
            if parsed_diff.is_binary:
                skipped_count += 1
                continue

            changed_lines = parsed_diff.changed_line_numbers

            source_code = await self.github_service.get_file_content(
                request.owner, request.repo, filename, ref=head_sha
            )
            if not source_code and patch:
                source_code = "\n".join([
                    line[1:] if line.startswith(("+", "-", " ")) else line
                    for line in patch.splitlines()
                    if not line.startswith("@@") and not line.startswith("---") and not line.startswith("+++")
                ])

            if not source_code:
                skipped_count += 1
                continue

            # Run Code Review for file
            file_review = await self.review_code(ReviewCodeRequest(
                filename=filename,
                source_code=source_code,
                changed_lines=changed_lines,
                diff_patch=patch
            ))

            analyzed_count += 1
            all_static.extend(file_review.static_findings)
            all_llm.extend(file_review.llm_findings)
            all_combined.extend(file_review.combined_findings)

            for cf in file_review.combined_findings:
                if cf.severity in severity_counts:
                    severity_counts[cf.severity] += 1

        return ReviewPRResponse(
            owner=request.owner,
            repo=request.repo,
            pull_number=request.pull_number,
            static_findings_count=len(all_static),
            llm_findings_count=len(all_llm),
            combined_findings_count=len(all_combined),
            severity_counts=severity_counts,
            analyzed_files_count=analyzed_count,
            skipped_files_count=skipped_count,
            static_findings=all_static,
            llm_findings=all_llm,
            combined_findings=all_combined
        )
