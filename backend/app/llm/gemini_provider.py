import json
import logging
from typing import List, Optional
import httpx

from app.config import get_settings
from app.llm.base import LLMProvider
from app.llm.schemas import LLMFinding, LLMReviewResponse
from app.llm.prompt_builder import PromptBuilder
from app.models.finding import Finding

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMConfigurationError(LLMError):
    """Raised when LLM API key or model configuration is missing."""
    pass


class GeminiProvider(LLMProvider):
    """
    LLM Code Review Provider implementing Google Gemini REST API.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self.api_key = (api_key if api_key is not None else settings.GEMINI_API_KEY).strip()
        self.model = (model if model is not None else settings.GEMINI_MODEL).strip() or "gemini-3.5-flash"
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def review_code(
        self,
        filename: str,
        source_code: str,
        diff_patch: Optional[str] = None,
        changed_lines: Optional[List[int]] = None,
        static_findings: Optional[List[Finding]] = None
    ) -> List[LLMFinding]:
        if not self.api_key:
            raise LLMConfigurationError(
                "GEMINI_API_KEY is not configured in backend environment variables."
            )

        system_prompt = PromptBuilder.build_system_prompt()
        user_prompt = PromptBuilder.build_user_prompt(
            filename, source_code, diff_patch, changed_lines, static_findings
        )

        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        url = f"{self.api_url}/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [{"text": full_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json",
            }
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.RequestError as exc:
                raise LLMError(f"Failed to connect to Gemini API: {str(exc)}")

            if response.status_code == 401 or response.status_code == 403:
                raise LLMConfigurationError("Invalid or unauthorized Gemini API key.")

            if response.status_code == 429:
                raise LLMError("Gemini API rate limit exceeded. Please try again later.")

            if response.status_code != 200:
                raise LLMError(f"Gemini API error (HTTP {response.status_code}): {response.text}")

            data = response.json()
            raw_text = ""
            try:
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_text = parts[0].get("text", "")
            except Exception as exc:
                logger.warning("Failed to extract content parts from Gemini response: %s", str(exc))

            if not raw_text or not raw_text.strip():
                return []

            return self._parse_and_validate_response(raw_text, filename)

    def _parse_and_validate_response(self, raw_text: str, filename: str) -> List[LLMFinding]:
        """
        Parses raw LLM text into validated LLMFinding objects, discarding invalid or un-evidenced findings.
        """
        try:
            parsed_json = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning("Gemini returned invalid JSON output: %s", str(exc))
            return []

        # Handle object format {"findings": [...]} or raw array [...]
        if isinstance(parsed_json, dict):
            findings_list = parsed_json.get("findings", [])
        elif isinstance(parsed_json, list):
            findings_list = parsed_json
        else:
            return []

        valid_findings: List[LLMFinding] = []
        for item in findings_list:
            if not isinstance(item, dict):
                continue
            # Ensure file is set correctly
            if "file" not in item or not item["file"]:
                item["file"] = filename

            try:
                finding_obj = LLMFinding(**item)
                # Ensure finding has evidence to prevent hallucinations
                if finding_obj.evidence and len(finding_obj.evidence.strip()) > 0:
                    valid_findings.append(finding_obj)
            except Exception as exc:
                logger.debug("Skipping malformed LLM finding item: %s", str(exc))

        return valid_findings

    async def test_connection(self) -> dict:
        """
        Diagnostic method to test Gemini API connection without exposing keys.
        """
        if not self.api_key:
            return {
                "connected": False,
                "model": self.model,
                "error": "GEMINI_API_KEY is not configured."
            }

        url = f"{self.api_url}/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [{"text": "Ping"}]
                }
            ]
        }

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    return {
                        "connected": True,
                        "model": self.model,
                        "error": None
                    }
                elif response.status_code in (401, 403):
                    logger.warning("Gemini health check authentication failed (HTTP %s)", response.status_code)
                    return {
                        "connected": False,
                        "model": self.model,
                        "error": "Invalid or unauthorized Gemini API key."
                    }
                else:
                    safe_text = self._sanitize_secret(response.text[:100])
                    logger.warning("Gemini health check error (HTTP %s): %s", response.status_code, safe_text)
                    return {
                        "connected": False,
                        "model": self.model,
                        "error": f"HTTP {response.status_code}: {safe_text}"
                    }
            except Exception as exc:
                safe_err = self._sanitize_secret(str(exc))
                logger.warning("Gemini health check exception: %s", safe_err)
                return {
                    "connected": False,
                    "model": self.model,
                    "error": f"Connection failed: {safe_err}"
                }

    def _sanitize_secret(self, text: str) -> str:
        """Removes API key from text or error messages if present."""
        if self.api_key and self.api_key in text:
            return text.replace(self.api_key, "[REDACTED]")
        return text

