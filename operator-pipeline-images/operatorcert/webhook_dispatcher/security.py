"""A GitHub webhook security module for verifying and validating requests."""

import hashlib
import hmac
import logging
from typing import Any, Optional

import flask

from .config import SecurityConfig

LOGGER = logging.getLogger("operator-cert")


class GitHubWebhookVerifier:
    """
    Verifies GitHub webhook signatures and validates requests.
    """

    def __init__(self, config: SecurityConfig):
        self.config = config

    def verify_signature(self, payload: bytes, signature_header: Optional[str]) -> bool:
        """
        Verify GitHub webhook signature.


        Args:
            payload: The raw webhook payload bytes
            signature_header: The X-Hub-Signature-256 header value

        Returns:
            bool: True if signature is valid, False otherwise
        """
        if not self.config.verify_signatures:
            LOGGER.warning("Webhook signature verification is disabled")
            return True

        if not self.config.github_webhook_secret:
            LOGGER.error("GitHub webhook secret not configured")
            return False

        if not signature_header:
            LOGGER.error("No signature header provided")
            return False

        LOGGER.debug("Verifying signature: %s", signature_header)

        try:
            # GitHub sends signature as "sha256=<signature>"
            if not signature_header.startswith("sha256="):
                LOGGER.error("Invalid signature format")
                return False

            hash_object = hmac.new(
                self.config.github_webhook_secret.encode("utf-8"),
                msg=payload,
                digestmod=hashlib.sha256,
            )
            expected_signature = "sha256=" + hash_object.hexdigest()

            is_valid = hmac.compare_digest(expected_signature, signature_header)

            return is_valid

        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Error verifying webhook signature")
            return False

    def validate_event_type(self, event_type: Optional[str]) -> bool:
        """
        Validate that the event type is allowed.

        Args:
            event_type: The GitHub event type from X-GitHub-Event header

        Returns:
            bool: True if event type is allowed, False otherwise
        """
        if not event_type:
            LOGGER.error("No event type provided")
            return False

        if event_type not in self.config.allowed_github_events:
            LOGGER.warning(
                "Event type '%s' not in allowed list: %s",
                event_type,
                self.config.allowed_github_events,
            )
            return False

        LOGGER.debug("Event type '%s' is allowed", event_type)
        return True

    def validate_user_agent(self, user_agent: Optional[str]) -> bool:
        """
        Validate that the request comes from GitHub.

        Args:
            user_agent: The User-Agent header value

        Returns:
            bool: True if user agent is valid GitHub webhook agent, False otherwise
        """
        if not user_agent:
            LOGGER.error("No User-Agent header provided")
            return False

        # GitHub webhook user agents start with "GitHub-Hookshot/"
        if not user_agent.startswith("GitHub-Hookshot/"):
            LOGGER.error("Invalid User-Agent: %s", user_agent)
            return False

        LOGGER.debug("Valid GitHub User-Agent: %s", user_agent)
        return True


def validate_github_webhook(
    request: flask.Request, security_config: SecurityConfig
) -> Any:
    """
    Validate GitHub webhook request.

    Args:
        request: The Flas request object
        security_config: Security configuration

    Returns:
        Any: Validation results and extracted data
    """
    verifier = GitHubWebhookVerifier(security_config)

    # Extract headers
    signature_header = request.headers.get("X-Hub-Signature-256")
    event_type = request.headers.get("X-GitHub-Event")
    delivery_id = request.headers.get("X-GitHub-Delivery")
    user_agent = request.headers.get("User-Agent")

    # Validate user agent
    if not verifier.validate_user_agent(user_agent):
        return (
            {"status": "rejected", "message": "Invalid User-Agent header"},
            400,
        )

    # Validate event type
    if not verifier.validate_event_type(event_type):
        return (
            {"status": "rejected", "message": f"Event type '{event_type}' not allowed"},
            400,
        )

    # Verify signature
    if not verifier.verify_signature(request.data, signature_header):
        return (
            {"status": "rejected", "message": "Invalid webhook signature"},
            401,
        )

    LOGGER.debug(
        "Validated GitHub webhook: %s event (delivery: %s)",
        event_type,
        delivery_id,
    )

    return True
