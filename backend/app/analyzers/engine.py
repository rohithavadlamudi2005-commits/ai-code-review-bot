import os
from typing import List, Dict, Optional, Type
from app.analyzers.base import CodeAnalyzer
from app.analyzers.python_analyzer import PythonAnalyzer
from app.analyzers.javascript_analyzer import JavaScriptAnalyzer
from app.services.diff_parser import DiffParser
from app.services.github_service import GitHubService
from app.models.finding import (
    Finding,
    CodeAnalysisResponse,
    PRAnalysisResponse,
    SkippedFileSummary,
)

# List of explicitly ignored file extensions or names
IGNORED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".zip", ".tar", ".gz",
    ".mp4", ".mp3", ".lock", ".bin", ".exe", ".dll", ".so", ".dylib", ".woff", ".ttf"
}

# Maximum supported file size (500 KB)
MAX_FILE_SIZE_BYTES = 500 * 1024


class AnalysisEngine:
    """
    Central manager for coordinating static code analyzers and PR review analysis pipelines.
    """

    def __init__(self):
        self.analyzers: List[CodeAnalyzer] = [
            PythonAnalyzer(),
            JavaScriptAnalyzer(),
        ]
        self._extension_map: Dict[str, CodeAnalyzer] = {}
        for analyzer in self.analyzers:
            for ext in analyzer.supported_extensions:
                self._extension_map[ext.lower()] = analyzer

    def get_analyzer(self, filename: str) -> Optional[CodeAnalyzer]:
        """
        Returns the appropriate analyzer for a given filename based on its extension.
        """
        _, ext = os.path.splitext(filename)
        return self._extension_map.get(ext.lower())

    def is_supported_file(self, filename: str) -> bool:
        """
        Checks if a file format is supported for static analysis.
        """
        return self.get_analyzer(filename) is not None

    def analyze_file(
        self,
        filename: str,
        source_code: str,
        changed_lines: Optional[List[int]] = None
    ) -> CodeAnalysisResponse:
        """
        Analyzes a single source file string and returns structured findings.
        """
        _, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        if ext_lower in IGNORED_EXTENSIONS:
            return CodeAnalysisResponse(
                filename=filename,
                skipped=True,
                skip_reason=f"Ignored file type ({ext_lower})"
            )

        analyzer = self.get_analyzer(filename)
        if not analyzer:
            return CodeAnalysisResponse(
                filename=filename,
                skipped=True,
                skip_reason=f"No static analyzer registered for extension '{ext}'"
            )

        if len(source_code.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
            return CodeAnalysisResponse(
                filename=filename,
                skipped=True,
                skip_reason="File exceeds maximum size limit (500 KB)"
            )

        findings = analyzer.analyze(filename, source_code, changed_lines)

        return CodeAnalysisResponse(
            filename=filename,
            findings=findings,
            total_findings=len(findings),
            skipped=False
        )

    async def analyze_pr(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        github_service: Optional[GitHubService] = None
    ) -> PRAnalysisResponse:
        """
        Fetches PR details and changed files, parses unified diffs, runs static analysis
        on changed lines, and aggregates findings.
        """
        if github_service is None:
            github_service = GitHubService()

        # Fetch PR metadata & changed files
        pr_info = await github_service.get_pull_request(owner, repo, pull_number)
        files = await github_service.get_pull_request_files(owner, repo, pull_number)

        all_findings: List[Finding] = []
        skipped_files: List[SkippedFileSummary] = []
        analyzed_count = 0
        skipped_count = 0

        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}

        head_sha = pr_info.get("head_sha")

        for file_item in files:
            filename = file_item.get("filename", "")
            patch = file_item.get("patch")
            status = file_item.get("status", "")

            if status == "removed":
                skipped_files.append(SkippedFileSummary(filename=filename, reason="File removed in PR"))
                skipped_count += 1
                continue

            if not self.is_supported_file(filename):
                _, ext = os.path.splitext(filename)
                reason = f"Unsupported file type ({ext or 'no extension'})"
                skipped_files.append(SkippedFileSummary(filename=filename, reason=reason))
                skipped_count += 1
                continue

            # Parse unified diff patch to get changed line numbers
            parsed_diff = DiffParser.parse_patch(patch, filename)
            if parsed_diff.is_binary:
                skipped_files.append(SkippedFileSummary(filename=filename, reason="Binary file patch"))
                skipped_count += 1
                continue

            changed_lines = parsed_diff.changed_line_numbers

            # Fetch full raw source code from GitHub, falling back to patch lines if unavailable
            source_code = await github_service.get_file_content(owner, repo, filename, ref=head_sha)
            if not source_code and patch:
                # Reconstruct readable snippet from patch lines if full source content unavailable
                source_code = "\n".join([
                    line[1:] if line.startswith(("+", "-", " ")) else line
                    for line in patch.splitlines()
                    if not line.startswith("@@") and not line.startswith("---") and not line.startswith("+++")
                ])

            analysis_resp = self.analyze_file(filename, source_code, changed_lines)

            if analysis_resp.skipped:
                skipped_files.append(SkippedFileSummary(filename=filename, reason=analysis_resp.skip_reason or "Skipped"))
                skipped_count += 1
            else:
                analyzed_count += 1
                for f in analysis_resp.findings:
                    all_findings.append(f)
                    if f.severity in severity_counts:
                        severity_counts[f.severity] += 1

        return PRAnalysisResponse(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            total_findings=len(all_findings),
            severity_counts=severity_counts,
            analyzed_files_count=analyzed_count,
            skipped_files_count=skipped_count,
            findings=all_findings,
            skipped_files=skipped_files
        )
