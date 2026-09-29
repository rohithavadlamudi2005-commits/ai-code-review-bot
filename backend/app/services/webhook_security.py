import hashlib
import hmac
import logging
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)


class WebhookSecurityError(Exception):
    """Raised when GitHub webhook signature verification fails."""
    pass


def verify_github_signature(
    payload_bytes: bytes,
    signature_header: Optional[str],
    secret: Optional[str] = None
) -> bool:
    """
    Verifies GitHub X-Hub-Signature-256 header using HMAC SHA-256 with constant-time comparison.

    :param payload_bytes: Raw HTTP request body bytes.
    :param signature_header: Value of 'X-Hub-Signature-256' header (e.g. 'sha256=abcdef...').
    :param secret: Webhook secret. If None, retrieves GITHUB_WEBHOOK_SECRET from app settings.
    :return: True if valid signature.
    :raises WebhookSecurityError: If signature is missing, malformed, or invalid when secret is set.
    """
    settings = get_settings()
    configured_secret = secret if secret is not None else settings.GITHUB_WEBHOOK_SECRET

    # If no webhook secret is configured in environment, log warning and bypass in dev mode if explicitly empty
    if not configured_secret or not configured_secret.strip():
        logger.warning("GITHUB_WEBHOOK_SECRET is empty. Skipping webhook signature verification.")
        return True

    if not signature_header or not signature_header.strip():
        raise WebhookSecurityError("Missing 'X-Hub-Signature-256' header in webhook request.")

    if not signature_header.startswith("sha256="):
        raise WebhookSecurityError("Malformed 'X-Hub-Signature-256' header format. Must start with 'sha256='.")

    secret_bytes = configured_secret.strip().encode("utf-8")
    expected_hash = hmac.new(secret_bytes, payload_bytes, hashlib.sha256).hexdigest()
    expected_signature = f"sha256={expected_hash}"

    if not hmac.compare_digest(expected_signature, signature_header.strip()):
        raise WebhookSecurityError("Invalid webhook signature. Request HMAC SHA-256 digest does not match secret.")

    return True
