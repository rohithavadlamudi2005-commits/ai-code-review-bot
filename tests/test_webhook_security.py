import hashlib
import hmac
import pytest
from app.services.webhook_security import verify_github_signature, WebhookSecurityError


def test_verify_github_signature_valid():
    secret = "my_super_secret"
    payload = b'{"action":"opened","number":1}'
    expected_hash = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    signature_header = f"sha256={expected_hash}"

    assert verify_github_signature(payload, signature_header, secret) is True


def test_verify_github_signature_invalid():
    secret = "my_super_secret"
    payload = b'{"action":"opened","number":1}'
    signature_header = "sha256=invalid_hash_value"

    with pytest.raises(WebhookSecurityError) as exc:
        verify_github_signature(payload, signature_header, secret)
    assert "Invalid webhook signature" in str(exc.value)


def test_verify_github_signature_missing_header():
    secret = "my_super_secret"
    payload = b'{"action":"opened"}'

    with pytest.raises(WebhookSecurityError) as exc:
        verify_github_signature(payload, None, secret)
    assert "Missing 'X-Hub-Signature-256' header" in str(exc.value)


def test_verify_github_signature_malformed_header():
    secret = "my_super_secret"
    payload = b'{"action":"opened"}'

    with pytest.raises(WebhookSecurityError) as exc:
        verify_github_signature(payload, "md5=123456", secret)
    assert "Must start with 'sha256='" in str(exc.value)
