from unittest.mock import MagicMock, patch

import pytest
from operatorcert.webhook_dispatcher.api import app
from operatorcert.webhook_dispatcher.config import SecurityConfig
from operatorcert.webhook_dispatcher.security import (
    GitHubWebhookVerifier,
    validate_github_webhook,
)


@pytest.fixture
def security_config() -> SecurityConfig:
    return SecurityConfig(
        verify_signatures=True,
        allowed_github_events=["push", "pull_request"],
        github_webhook_secret="test",
    )


@pytest.fixture
def webhook_verifier(security_config: SecurityConfig) -> GitHubWebhookVerifier:
    return GitHubWebhookVerifier(security_config)


def test_verify_signature(webhook_verifier: GitHubWebhookVerifier) -> None:
    payload = b"test"

    # This is the expected signature for the payload "test"
    signature_header = (
        "sha256=88cd2108b5347d973cf39cdf9053d7dd42704876d8c9a9bd8e2d168259d3ddf7"
    )
    assert webhook_verifier.verify_signature(payload, signature_header)

    # This is an invalid signature
    signature_header = "sha256=fake"
    assert not webhook_verifier.verify_signature(payload, signature_header)


@patch("operatorcert.webhook_dispatcher.security.hmac.new")
def test_verify_signature_exception(
    mock_hmac_new: MagicMock, webhook_verifier: GitHubWebhookVerifier
) -> None:
    payload = b"test"
    signature_header = "sha256=fake"
    mock_hmac_new.side_effect = Exception("test")
    assert not webhook_verifier.verify_signature(payload, signature_header)


def test_test_verify_signature_options() -> None:
    # No signature verification
    config = SecurityConfig(
        verify_signatures=False,
        allowed_github_events=["push", "pull_request"],
        github_webhook_secret="test",
    )
    verifier = GitHubWebhookVerifier(config)
    assert verifier.verify_signature(b"test", "sha256=fake")

    # No secret
    config = SecurityConfig(
        verify_signatures=True,
        allowed_github_events=["push", "pull_request"],
        github_webhook_secret="",
    )
    verifier = GitHubWebhookVerifier(config)
    assert not verifier.verify_signature(b"test", "sha256=fake")

    # No signature header
    config = SecurityConfig(
        verify_signatures=True,
        allowed_github_events=["push", "pull_request"],
        github_webhook_secret="test",
    )
    verifier = GitHubWebhookVerifier(config)
    assert not verifier.verify_signature(b"test", "")

    # Invalid signature header
    assert not verifier.verify_signature(b"test", "invalid")


def test_validate_event_type(webhook_verifier: GitHubWebhookVerifier) -> None:
    assert webhook_verifier.validate_event_type("push")
    assert webhook_verifier.validate_event_type("pull_request")
    assert not webhook_verifier.validate_event_type("unknown")
    assert not webhook_verifier.validate_event_type(None)


def test_validate_user_agent(webhook_verifier: GitHubWebhookVerifier) -> None:
    assert webhook_verifier.validate_user_agent("GitHub-Hookshot/1234567890")
    assert not webhook_verifier.validate_user_agent("unknown")
    assert not webhook_verifier.validate_user_agent(None)


@patch(
    "operatorcert.webhook_dispatcher.security.GitHubWebhookVerifier.validate_user_agent"
)
@patch(
    "operatorcert.webhook_dispatcher.security.GitHubWebhookVerifier.validate_event_type"
)
@patch(
    "operatorcert.webhook_dispatcher.security.GitHubWebhookVerifier.verify_signature"
)
def test_validate_github_webhook(
    mock_verify_signature: MagicMock,
    mock_validate_event_type: MagicMock,
    mock_validate_user_agent: MagicMock,
    webhook_verifier: GitHubWebhookVerifier,
) -> None:

    request = MagicMock()
    request.headers = {
        "X-Hub-Signature-256": "sha256=88cd2108b5347d973cf39cdf9053d7dd42704876d8c9a9bd8e2d168259d3ddf7",
        "X-GitHub-Event": "push",
        "X-GitHub-Delivery": "1234567890",
    }
    mock_validate_user_agent.return_value = False
    mock_validate_event_type.return_value = False
    mock_verify_signature.return_value = False
    resp = validate_github_webhook(request, webhook_verifier.config)
    assert resp[1] == 400
    assert resp[0]["status"] == "rejected"
    assert resp[0]["message"] == "Invalid User-Agent header"

    mock_validate_user_agent.return_value = True

    resp = validate_github_webhook(request, webhook_verifier.config)
    assert resp[1] == 400
    assert resp[0]["status"] == "rejected"
    assert resp[0]["message"] == "Event type 'push' not allowed"

    mock_validate_event_type.return_value = True
    resp = validate_github_webhook(request, webhook_verifier.config)
    assert resp[1] == 401
    assert resp[0]["status"] == "rejected"
    assert resp[0]["message"] == "Invalid webhook signature"

    mock_verify_signature.return_value = True
    resp = validate_github_webhook(request, webhook_verifier.config)
    assert resp is True
