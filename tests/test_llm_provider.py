import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.llm.gemini_provider import GeminiProvider, LLMConfigurationError, LLMError
from app.llm.schemas import LLMFinding


@pytest.mark.asyncio
async def test_gemini_provider_missing_api_key():
    provider = GeminiProvider(api_key="")
    with pytest.raises(LLMConfigurationError) as exc:
        await provider.review_code("app.py", "eval('2+2')")
    assert "GEMINI_API_KEY is not configured" in str(exc.value)


@pytest.mark.asyncio
async def test_gemini_provider_success_response():
    mock_llm_json = """{
      "findings": [
        {
          "category": "security",
          "severity": "HIGH",
          "confidence": 0.95,
          "file": "app.py",
          "line": 10,
          "message": "Potential SQL injection",
          "explanation": "Dynamic SQL construction using raw input concatenation",
          "suggestion": "Use parameterized queries",
          "evidence": "query = 'SELECT * FROM users WHERE id=' + user_input"
        }
      ]
    }"""

    mock_response_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": mock_llm_json}]
                }
            }
        ]
    }

    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.status_code = 200
    mock_http_response.json.return_value = mock_response_payload

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response

        provider = GeminiProvider(api_key="test_gemini_key")
        findings = await provider.review_code("app.py", "query = 'SELECT * FROM users WHERE id=' + user_input")

        assert len(findings) == 1
        f = findings[0]
        assert f.category == "security"
        assert f.severity == "HIGH"
        assert f.confidence == 0.95
        assert f.line == 10
        assert f.evidence == "query = 'SELECT * FROM users WHERE id=' + user_input"


@pytest.mark.asyncio
async def test_gemini_provider_malformed_json_returns_empty_list():
    mock_response_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "INVALID NON-JSON RESPONSE TEXT"}]
                }
            }
        ]
    }

    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.status_code = 200
    mock_http_response.json.return_value = mock_response_payload

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response

        provider = GeminiProvider(api_key="test_key")
        findings = await provider.review_code("app.py", "code")

        assert findings == []


@pytest.mark.asyncio
async def test_gemini_provider_discards_finding_without_evidence():
    mock_llm_json = """{
      "findings": [
        {
          "category": "security",
          "severity": "HIGH",
          "confidence": 0.9,
          "file": "app.py",
          "line": 10,
          "message": "Hallucinated issue",
          "explanation": "No proof",
          "suggestion": "Fix it",
          "evidence": ""
        }
      ]
    }"""

    mock_response_payload = {
        "candidates": [{"content": {"parts": [{"text": mock_llm_json}]}}]
    }

    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.status_code = 200
    mock_http_response.json.return_value = mock_response_payload

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response

        provider = GeminiProvider(api_key="test_key")
        findings = await provider.review_code("app.py", "code")

        # Discarded because evidence was empty string
        assert findings == []


@pytest.mark.asyncio
async def test_gemini_provider_test_connection_success():
    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.status_code = 200
    mock_http_response.json.return_value = {}

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response

        provider = GeminiProvider(api_key="test_key_123")
        res = await provider.test_connection()

        assert res["connected"] is True
        assert res["model"] == "gemini-3.5-flash"
        assert res["error"] is None

        # Verify payload sent to Gemini API matches generateContent standard structure (no maxOutputTokens)
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"] == {"contents": [{"parts": [{"text": "Ping"}]}]}


@pytest.mark.asyncio
async def test_gemini_provider_test_connection_sanitizes_secret():
    mock_http_response = MagicMock(spec=httpx.Response)
    mock_http_response.status_code = 500
    mock_http_response.text = "Error occurred with key secret_key_abcxyz"

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_http_response

        provider = GeminiProvider(api_key="secret_key_abcxyz")
        res = await provider.test_connection()

        assert res["connected"] is False
        assert "secret_key_abcxyz" not in res["error"]
        assert "[REDACTED]" in res["error"]

