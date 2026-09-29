from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.finding import Finding


class CodeAnalyzer(ABC):
    """
    Abstract base class for language-specific static code analyzers.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """
        List of file extensions supported by this analyzer (e.g., ['.py']).
        """
        pass

    @abstractmethod
    def analyze(self, file_path: str, source_code: str, changed_lines: Optional[List[int]] = None) -> List[Finding]:
        """
        Analyzes source code and returns structured Findings.
        If changed_lines is provided, only findings on those line numbers should be returned.

        :param file_path: Path or filename of the file.
        :param source_code: Complete raw source code string.
        :param changed_lines: Optional list of 1-indexed changed line numbers.
        :return: List of Finding models.
        """
        pass

    def filter_findings_by_lines(self, findings: List[Finding], changed_lines: Optional[List[int]]) -> List[Finding]:
        """
        Helper method to filter findings to only those occurring on changed line numbers.
        If changed_lines is None or empty, all findings are retained.
        """
        if not changed_lines:
            return findings
        changed_set = set(changed_lines)
        return [f for f in findings if f.line in changed_set]
