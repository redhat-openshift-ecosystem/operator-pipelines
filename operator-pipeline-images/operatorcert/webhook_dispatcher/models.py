"""Module for database models used in the webhook dispatcher."""

import uuid
from datetime import datetime
from typing import Any, Optional

from flask import Request
from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):  # pylint: disable=too-few-public-methods
    """
    Base class for all database models.
    This class is used to define the base for SQLAlchemy ORM models.
    It can be extended by other models to inherit common properties.
    """


class WebhookEvent(Base):  # pylint: disable=too-few-public-methods
    """
    Database model for storing GitHub webhook events.
    """

    __tablename__ = "webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    delivery_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    repository_full_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    pull_request_number: Mapped[int] = mapped_column(Integer, index=True)
    processed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )
    request_headers: Mapped[Optional[dict[str, str]]] = mapped_column(
        JSON, nullable=True
    )


def convert_to_webhook_event(payload: dict[str, Any], request: Request) -> WebhookEvent:
    """
    Convert a JSON payload and request headers into a WebhookEvent object.

    Args:
        payload (dict[str, Any]): A request payload containing event data.
        request (Request): A Flask request object containing headers.

    Returns:
        WebhookEvent: A WebhookEvent object populated with the payload and
        request headers.
    """
    headers = {}
    for key, value in request.headers.items():
        if key.lower().startswith("x-hub-") or key.lower().startswith("x-github-"):
            headers[key] = value
    return WebhookEvent(
        id=uuid.uuid4(),
        delivery_id=request.headers.get("X-GitHub-Delivery"),
        action=payload["action"],
        payload=payload,
        repository_full_name=payload["repository"]["full_name"],
        pull_request_number=payload["pull_request"]["number"],
        received_at=datetime.utcnow(),
        processed=False,
        processing_error=None,
        processed_at=None,
        status="pending",
        request_headers=headers,
    )
