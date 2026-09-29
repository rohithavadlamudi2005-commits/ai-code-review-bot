from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.finding import Finding
from app.llm.schemas import LLMFinding


class LLMProvider(ABC):
    """
    Abstract interface for LLM providers (e.g. Gemini, OpenAI, Claude).
    """

    @abstractmethod
    async def review_code(
        self,
        filename: str,
        source_code: str,
        diff_patch: Optional[str] = None,
        changed_lines: Optional[List[int]] = None,
        static_findings: Optional[List[Finding]] = None
    ) -> List[LLMFinding]:
        """
        Reviews supplied source code and diff using LLM and returns structured LLM findings.

        :param filename: Target file path.
        :param source_code: Complete or context source code string.
        :param diff_patch: Optional patch string from GitHub PR.
        :param changed_lines: Optional list of line numbers modified in PR.
        :param static_findings: Deterministic static findings from Stage 3.
        :return: List of validated LLMFinding objects.
        """
        pass
