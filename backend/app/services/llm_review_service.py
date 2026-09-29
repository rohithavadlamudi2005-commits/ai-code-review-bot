import logging
from typing import List, Optional
from app.config import get_settings
from app.llm.base import LLMProvider
from app.llm.gemini_provider import GeminiProvider, LLMError, LLMConfigurationError
from app.llm.schemas import LLMFinding
from app.models.finding import Finding

logger = logging.getLogger(__name__)


class LLMReviewService:
    """
    Service layer for executing LLM-based code reviews with fallback & size limit enforcement.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider if provider is not None else GeminiProvider()
        self.settings = get_settings()

    async def review_file(
        self,
        filename: str,
        source_code: str,
        diff_patch: Optional[str] = None,
        changed_lines: Optional[List[int]] = None,
        static_findings: Optional[List[Finding]] = None
    ) -> List[LLMFinding]:
        """
        Executes LLM code review for a single file within token and size limits.
        """
        if not source_code or not source_code.strip():
            return []

        # Check file size limit
        if len(source_code.encode("utf-8")) > self.settings.LLM_MAX_FILE_SIZE:
            logger.info("Skipping LLM review for '%s': File size exceeds limit.", filename)
            return []

        # Check diff size limit if present
        if diff_patch and len(diff_patch.encode("utf-8")) > self.settings.LLM_MAX_DIFF_SIZE:
            logger.info("Truncating diff for '%s': Patch size exceeds limit.", filename)
            diff_patch = diff_patch[:self.settings.LLM_MAX_DIFF_SIZE]

        try:
            return await self.provider.review_code(
                filename=filename,
                source_code=source_code,
                diff_patch=diff_patch,
                changed_lines=changed_lines,
                static_findings=static_findings
            )
        except (LLMConfigurationError, LLMError) as exc:
            logger.warning("LLM Review skipped for '%s': %s", filename, str(exc))
            return []
        except Exception as exc:
            logger.error("Unexpected error during LLM review for '%s': %s", filename, str(exc))
            return []
